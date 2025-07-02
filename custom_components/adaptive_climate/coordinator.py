"""Adaptive Climate Coordinator."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store
from homeassistant.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_ON,
    STATE_OFF,
    STATE_UNKNOWN,
    STATE_UNAVAILABLE,
)
from homeassistant.components.climate.const import (
    DOMAIN as CLIMATE_DOMAIN,
    ATTR_HVAC_MODE,
    ATTR_FAN_MODE,
)
from homeassistant.components.climate import (
    HVACMode,
    HVACAction,
)

# Service constants - define as strings since they may not be in const anymore
SERVICE_SET_TEMPERATURE = "set_temperature"
SERVICE_SET_HVAC_MODE = "set_hvac_mode"
SERVICE_SET_FAN_MODE = "set_fan_mode"

from .const import (
    DOMAIN,
    UPDATE_INTERVAL_MEDIUM,
    DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
    DEFAULT_SETBACK_TEMPERATURE_OFFSET,
)
from .ashrae_calculator import AdaptiveComfortCalculator

_LOGGER = logging.getLogger(__name__)

# Storage constants
STORAGE_VERSION = 1
STORAGE_KEY = "adaptive_climate_data"


class AdaptiveClimateCoordinator(DataUpdateCoordinator):
    """Coordinate adaptive climate control."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_data: dict[str, Any],
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MEDIUM),
        )
        
        self.config = config_entry_data
        self.calculator = AdaptiveComfortCalculator(config_entry_data)
        
        # State tracking
        self._manual_override = False
        self._override_expiry: datetime | None = None
        self._last_target_temp: float | None = None
        self._occupied = True
        self._natural_ventilation_active = False
        
        # Temperature history for running mean (last 7 days)
        self._outdoor_temp_history: list[tuple[datetime, float]] = []
        self._running_mean_outdoor_temp: float | None = None
        
        # Storage for persistence
        self._store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{config_entry_data.get('name', 'default')}")
        self._last_valid_data: dict[str, Any] | None = None
        
        # Entity IDs from config
        self.climate_entity_id = config_entry_data["climate_entity"]
        self.indoor_temp_entity_id = config_entry_data["indoor_temp_sensor"]
        self.outdoor_temp_entity_id = config_entry_data["outdoor_temp_sensor"]
        self.occupancy_entity_id = config_entry_data.get("occupancy_sensor")
        
        # Set up state listeners
        self._setup_listeners()
        
        # Load persisted data
        self.hass.async_create_task(self._load_persisted_data())

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data."""
        try:
            # Get current states
            climate_state = self.hass.states.get(self.climate_entity_id)
            indoor_temp_state = self.hass.states.get(self.indoor_temp_entity_id)
            outdoor_temp_state = self.hass.states.get(self.outdoor_temp_entity_id)
            
            # Check if any required entity is unavailable or unknown
            missing_entities = []
            if not climate_state or climate_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                missing_entities.append(f"climate entity: {self.climate_entity_id}")
            if not indoor_temp_state or indoor_temp_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                missing_entities.append(f"indoor temperature sensor: {self.indoor_temp_entity_id}")
            if not outdoor_temp_state or outdoor_temp_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                missing_entities.append(f"outdoor temperature sensor: {self.outdoor_temp_entity_id}")
            
            if missing_entities:
                # Only log warning if this is the first time or if it's been a while
                now = datetime.now()
                if not hasattr(self, '_last_warning_time') or (now - self._last_warning_time).total_seconds() > 300:  # 5 minutes
                    _LOGGER.warning("Required entities not available or unknown: %s", ", ".join(missing_entities))
                    self._last_warning_time = now
                
                # Return previous data if available, or minimal default data
                if self.data:
                    return self.data
                elif self._last_valid_data:
                    _LOGGER.info("Using last valid persisted data while entities are unavailable")
                    return self._last_valid_data
                return self._get_default_data()
            
            # Parse temperatures
            try:
                indoor_temp = float(indoor_temp_state.state)
                outdoor_temp = float(outdoor_temp_state.state)
            except (ValueError, TypeError) as exc:
                _LOGGER.warning("Invalid temperature values: indoor=%s, outdoor=%s, error=%s", 
                              indoor_temp_state.state, outdoor_temp_state.state, exc)
                # Return previous data if available, or minimal default data
                if self.data:
                    return self.data
                elif self._last_valid_data:
                    _LOGGER.info("Using last valid persisted data due to invalid temperature values")
                    return self._last_valid_data
                return self._get_default_data()
            
            # Update outdoor temperature history and running mean
            self._update_outdoor_temp_history(outdoor_temp)
            
            # Update occupancy
            self._update_occupancy()
            
            # Check manual override expiry
            self._check_override_expiry()
            
            # Calculate adaptive parameters
            comfort_data = self.calculator.calculate_comfort_parameters(
                outdoor_temp=outdoor_temp,
                indoor_temp=indoor_temp,
                indoor_humidity=self._get_humidity(),
                air_velocity=self.config.get("air_velocity", 0.1),
                mean_radiant_temp=self._get_mean_radiant_temp(),
            )
            
            # Update natural ventilation status
            self._update_natural_ventilation_status(outdoor_temp, indoor_temp, comfort_data)

            # Determine control actions
            control_actions = self._determine_control_actions(
                climate_state, indoor_temp, comfort_data
            )
            
            # Execute control actions if not in manual override
            if not self._manual_override:
                await self._execute_control_actions(control_actions)
            
            # Prepare data for sensors
            data = {
                **comfort_data,
                "climate_state": climate_state.state,
                "indoor_temperature": indoor_temp,
                "outdoor_temperature": outdoor_temp,
                "outdoor_running_mean": self._running_mean_outdoor_temp,
                "occupancy": "occupied" if self._occupied else "unoccupied",
                "manual_override": self._manual_override,
                "natural_ventilation_active": self._natural_ventilation_active,
                "control_actions": control_actions,
                "last_updated": datetime.now(),
            }
            
            # Log control action
            self._log_control_action(data, control_actions)
            
            # Save valid data for persistence
            self._last_valid_data = data.copy()
            await self._save_persisted_data(data)
            
            return data
            
        except Exception as err:
            _LOGGER.error("Error updating adaptive climate data: %s", err)
            # Return previous data if available, or minimal default data
            if self.data:
                return self.data
            elif self._last_valid_data:
                _LOGGER.info("Using last valid persisted data due to update error")
                return self._last_valid_data
            return self._get_default_data()

    def _get_default_data(self) -> dict[str, Any]:
        """Get default data when entities are unavailable."""
        return {
            "adaptive_comfort_temp": 22.0,
            "comfort_temp_min": 20.0,
            "comfort_temp_max": 24.0,
            "indoor_temperature": None,
            "outdoor_temperature": None,
            "outdoor_running_mean": None,
            "climate_state": "unknown",
            "occupancy": "unknown",
            "manual_override": self._manual_override,
            "natural_ventilation_active": False,
            "ashrae_compliant": False,
            "control_actions": {},
            "last_updated": datetime.now(),
            "status": "entities_unavailable",
        }

    async def _load_persisted_data(self) -> None:
        """Load persisted data from storage."""
        try:
            data = await self._store.async_load()
            if data:
                # Restore outdoor temperature history
                if "outdoor_temp_history" in data:
                    self._outdoor_temp_history = [
                        (datetime.fromisoformat(timestamp), temp)
                        for timestamp, temp in data["outdoor_temp_history"]
                    ]
                
                # Restore running mean
                if "running_mean_outdoor_temp" in data:
                    self._running_mean_outdoor_temp = data["running_mean_outdoor_temp"]
                
                # Restore last valid sensor data
                if "last_sensor_data" in data:
                    self._last_valid_data = data["last_sensor_data"]
                
                self._create_logbook_entry("Adaptive climate data restored from storage after restart")
                _LOGGER.info("Loaded persisted adaptive climate data")
        except Exception as err:
            _LOGGER.warning("Failed to load persisted data: %s", err)

    async def _save_persisted_data(self, current_data: dict[str, Any]) -> None:
        """Save current data to storage."""
        try:
            # Prepare data for storage (make JSON serializable)
            storage_data = {
                "outdoor_temp_history": [
                    (timestamp.isoformat(), temp)
                    for timestamp, temp in self._outdoor_temp_history
                ],
                "running_mean_outdoor_temp": self._running_mean_outdoor_temp,
                "last_sensor_data": {
                    key: value for key, value in current_data.items()
                    if key not in ["last_updated"]  # Exclude non-serializable items
                },
                "last_updated": datetime.now().isoformat(),
            }
            
            # Save to storage
            await self._store.async_save(storage_data)
        except Exception as err:
            _LOGGER.warning("Failed to save persisted data: %s", err)

    def _create_logbook_entry(self, message: str, entity_id: str | None = None) -> None:
        """Create a logbook entry for important events."""
        try:
            self.hass.bus.async_fire(
                "logbook_entry",
                {
                    LOGBOOK_ENTRY_NAME: "Adaptive Climate",
                    LOGBOOK_ENTRY_MESSAGE: message,
                    "domain": DOMAIN,
                    "entity_id": entity_id or f"{DOMAIN}.{self.config.get('name', 'adaptive_climate')}",
                }
            )
        except Exception as err:
            _LOGGER.debug("Failed to create logbook entry: %s", err)

    def _setup_listeners(self) -> None:
        """Set up state change listeners."""
        entities_to_track = [
            self.climate_entity_id,
            self.indoor_temp_entity_id,
            self.outdoor_temp_entity_id,
        ]
        
        if self.occupancy_entity_id:
            entities_to_track.append(self.occupancy_entity_id)
        
        async_track_state_change_event(
            self.hass,
            entities_to_track,
            self._handle_state_change,
        )

    @callback
    def _handle_state_change(self, event) -> None:
        """Handle state changes."""
        # Schedule a fresh data update when tracked entities change
        self.async_set_updated_data(self.data or {})
        # Also trigger a full refresh to recalculate data
        self.hass.async_create_task(self.async_request_refresh())

    def _update_occupancy(self) -> None:
        """Update occupancy status."""
        if not self.occupancy_entity_id:
            return
        
        occupancy_state = self.hass.states.get(self.occupancy_entity_id)
        if occupancy_state and occupancy_state.state in (STATE_ON, STATE_OFF):
            new_occupied = occupancy_state.state == STATE_ON
            
            # Check if occupancy changed
            if new_occupied != self._occupied:
                self._occupied = new_occupied
                status = "occupied" if new_occupied else "unoccupied"
                self._create_logbook_entry(f"Occupancy changed to {status}", self.occupancy_entity_id)
                _LOGGER.info("Occupancy changed to %s", status)
            else:
                self._occupied = new_occupied

    def _check_override_expiry(self) -> None:
        """Check if manual override has expired."""
        if self._manual_override and self._override_expiry:
            if datetime.now() >= self._override_expiry:
                self._manual_override = False
                self._override_expiry = None
                
                # Create logbook entry
                self._create_logbook_entry("Manual override expired - returning to adaptive control", self.climate_entity_id)
                
                _LOGGER.info("Manual override expired, returning to adaptive control")

    def _get_humidity(self) -> float | None:
        """Get indoor humidity if available."""
        humidity_entity_id = self.config.get("indoor_humidity_sensor")
        if not humidity_entity_id:
            return None
        
        humidity_state = self.hass.states.get(humidity_entity_id)
        if humidity_state and humidity_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                return float(humidity_state.state)
            except (ValueError, TypeError):
                pass
        return None

    def _get_mean_radiant_temp(self) -> float | None:
        """Get mean radiant temperature if available."""
        mrt_entity_id = self.config.get("mean_radiant_temp_sensor")
        if not mrt_entity_id:
            return None
        
        mrt_state = self.hass.states.get(mrt_entity_id)
        if mrt_state and mrt_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                return float(mrt_state.state)
            except (ValueError, TypeError):
                pass
        return None

    def _determine_control_actions(
        self, 
        climate_state: State, 
        indoor_temp: float, 
        comfort_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Determine what control actions to take."""
        actions = {
            "set_temperature": None,
            "set_hvac_mode": None,
            "set_fan_mode": None,
            "reason": "",
        }
        
        comfort_temp = comfort_data.get("adaptive_comfort_temp")
        comfort_min = comfort_data.get("comfort_temp_min")
        comfort_max = comfort_data.get("comfort_temp_max")
        
        if not all([comfort_temp, comfort_min, comfort_max]):
            return actions
        
        # Determine target temperature
        target_temp = comfort_temp
        
        # Apply occupancy setback if unoccupied
        if not self._occupied:
            setback_offset = self.config.get("setback_temperature_offset", DEFAULT_SETBACK_TEMPERATURE_OFFSET)
            if indoor_temp > comfort_temp:
                target_temp = comfort_temp + setback_offset
            else:
                target_temp = comfort_temp - setback_offset
            actions["reason"] = f"Setback (unoccupied): {setback_offset}°C offset"
        
        # Check if temperature change is significant enough
        current_target = float(climate_state.attributes.get(ATTR_TEMPERATURE, 0))
        temp_threshold = self.config.get("temperature_change_threshold", DEFAULT_TEMPERATURE_CHANGE_THRESHOLD)
        
        if abs(target_temp - current_target) >= temp_threshold:
            actions["set_temperature"] = target_temp
        
        # Determine HVAC mode
        current_hvac_mode = climate_state.state
        
        if indoor_temp > comfort_max:
            # Too hot - cooling needed
            if current_hvac_mode != HVACMode.COOL:
                actions["set_hvac_mode"] = HVACMode.COOL
                actions["reason"] += f" (above comfort zone)" if actions["reason"] else "above comfort zone"
        elif indoor_temp < comfort_min:
            # Too cold - heating needed
            if current_hvac_mode != HVACMode.HEAT:
                actions["set_hvac_mode"] = HVACMode.HEAT
                actions["reason"] += f" (below comfort zone)" if actions["reason"] else "below comfort zone"
        else:
            # In comfort zone - could turn off or use auto
            if current_hvac_mode in [HVACMode.COOL, HVACMode.HEAT]:
                actions["set_hvac_mode"] = HVACMode.AUTO
                actions["reason"] += f" (in comfort zone)" if actions["reason"] else "in comfort zone"
        
        # Determine fan mode if adaptive air velocity is enabled
        if self.config.get("adaptive_air_velocity", False):
            fan_mode = self._calculate_optimal_fan_mode(indoor_temp, comfort_data)
            current_fan_mode = climate_state.attributes.get(ATTR_FAN_MODE)
            if fan_mode and fan_mode != current_fan_mode:
                actions["set_fan_mode"] = fan_mode
        
        return actions

    def _calculate_optimal_fan_mode(self, indoor_temp: float, comfort_data: dict[str, Any]) -> str | None:
        """Calculate optimal fan mode based on temperature deviation."""
        comfort_temp = comfort_data.get("adaptive_comfort_temp")
        if not comfort_temp:
            return None
        
        temp_deviation = abs(indoor_temp - comfort_temp)
        
        if temp_deviation <= 1.0:
            return "auto"
        elif temp_deviation <= 2.0:
            return "medium"
        else:
            return "high"

    async def _execute_control_actions(self, actions: dict[str, Any]) -> None:
        """Execute control actions on the climate entity."""
        try:
            action_messages = []
            
            # Set temperature
            if actions["set_temperature"] is not None:
                await self.hass.services.async_call(
                    CLIMATE_DOMAIN,
                    SERVICE_SET_TEMPERATURE,
                    {
                        "entity_id": self.climate_entity_id,
                        ATTR_TEMPERATURE: actions["set_temperature"],
                    },
                )
                self._last_target_temp = actions["set_temperature"]
                action_messages.append(f"Temperature set to {actions['set_temperature']:.1f}°C")
            
            # Set HVAC mode
            if actions["set_hvac_mode"] is not None:
                await self.hass.services.async_call(
                    CLIMATE_DOMAIN,
                    SERVICE_SET_HVAC_MODE,
                    {
                        "entity_id": self.climate_entity_id,
                        ATTR_HVAC_MODE: actions["set_hvac_mode"],
                    },
                )
                action_messages.append(f"HVAC mode set to {actions['set_hvac_mode']}")
            
            # Set fan mode
            if actions["set_fan_mode"] is not None:
                await self.hass.services.async_call(
                    CLIMATE_DOMAIN,
                    SERVICE_SET_FAN_MODE,
                    {
                        "entity_id": self.climate_entity_id,
                        ATTR_FAN_MODE: actions["set_fan_mode"],
                    },
                )
                action_messages.append(f"Fan mode set to {actions['set_fan_mode']}")
            
            # Create logbook entry if any actions were taken
            if action_messages:
                reason = actions.get("reason", "adaptive control")
                message = f"Climate adjusted: {', '.join(action_messages)} ({reason})"
                self._create_logbook_entry(message, self.climate_entity_id)
                
        except Exception as err:
            _LOGGER.error("Error executing control actions: %s", err)
            self._create_logbook_entry(f"Failed to execute climate control: {err}", self.climate_entity_id)

    def _log_control_action(self, data: dict[str, Any], actions: dict[str, Any]) -> None:
        """Log control action for debugging."""
        if any(actions[key] is not None for key in ["set_temperature", "set_hvac_mode", "set_fan_mode"]):
            comfort_temp = data.get("adaptive_comfort_temp", 0)
            comfort_min = data.get("comfort_temp_min", 0)
            comfort_max = data.get("comfort_temp_max", 0)
            indoor_temp = data.get("indoor_temperature", 0)
            outdoor_temp = data.get("outdoor_temperature", 0)
            
            _LOGGER.info(
                "ASHRAE 55 compliant climate control applied. "
                "Target: %.1f°C (Current: %.1f°C), Indoor: %.1f°C, Outdoor: %.2f°C, "
                "Comfort zone: %.1f-%.1f°C (adaptive temp: %.0f°C), "
                "HVAC Mode: %s %s, Occupancy: %s, Category: %s (±%.1f°C), "
                "Air velocity offset: %.0f°C, Humidity offset: %.0f°C, "
                "Fan: %s, Compliance: \"%s\"",
                actions.get("set_temperature", self._last_target_temp or 0),
                self._last_target_temp or 0,
                indoor_temp,
                outdoor_temp,
                comfort_min,
                comfort_max,
                comfort_temp,
                actions.get("set_hvac_mode", "unchanged"),
                actions.get("reason", ""),
                data.get("occupancy", "unknown"),
                self.config.get("comfort_category", "II"),
                self.calculator.get_comfort_tolerance(),
                0,  # Air velocity offset (placeholder)
                0,  # Humidity offset (placeholder)
                actions.get("set_fan_mode", "unchanged"),
                "Compliant" if data.get("ashrae_compliant", False) else "Non-compliant"
            )

    async def set_manual_override(self, temperature: float, duration: int | None = None) -> None:
        """Set manual override."""
        self._manual_override = True
        self._last_target_temp = temperature
        
        if duration:
            self._override_expiry = datetime.now() + timedelta(seconds=duration)
        else:
            self._override_expiry = None
        
        # Set temperature immediately
        await self.hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                "entity_id": self.climate_entity_id,
                ATTR_TEMPERATURE: temperature,
            },
        )
        
        # Create logbook entry
        duration_text = f" for {duration//3600}h {(duration%3600)//60}m" if duration else ""
        message = f"Manual override activated: {temperature:.1f}°C{duration_text}"
        self._create_logbook_entry(message, self.climate_entity_id)
        
        _LOGGER.info("Manual override set to %.1f°C%s", 
                    temperature, 
                    f" for {duration}s" if duration else "")

    async def clear_manual_override(self) -> None:
        """Clear manual override."""
        self._manual_override = False
        self._override_expiry = None
        
        # Create logbook entry
        self._create_logbook_entry("Manual override cleared - returning to adaptive control", self.climate_entity_id)
        
        _LOGGER.info("Manual override cleared, returning to adaptive control")
        
        # Trigger immediate update
        await self.async_request_refresh()

    async def update_comfort_category(self, category: str) -> None:
        """Update comfort category."""
        if category in ["I", "II", "III"]:
            old_category = self.config.get("comfort_category", "II")
            self.config["comfort_category"] = category
            self.calculator.update_config(self.config)
            
            # Create logbook entry
            self._create_logbook_entry(f"Comfort category changed from {old_category} to {category}")
            
            _LOGGER.info("Comfort category updated to %s", category)
            
            # Trigger immediate update
            await self.async_request_refresh()

    async def set_comfort_category(self, category: str) -> None:
        """Set comfort category (alias for update_comfort_category)."""
        await self.update_comfort_category(category)

    async def set_temporary_override(
        self, 
        temperature: float | None = None, 
        hvac_mode: str | None = None, 
        duration_hours: int = 1
    ) -> None:
        """Set temporary override with duration in hours."""
        duration_seconds = duration_hours * 3600
        if temperature is not None:
            await self.set_manual_override(temperature, duration_seconds)
        
        # If HVAC mode is specified, apply it immediately
        if hvac_mode is not None:
            actions = {"hvac_mode": hvac_mode}
            await self._execute_control_actions(actions)
        
        _LOGGER.info(
            "Temporary override set: temp=%s, mode=%s, duration=%dh",
            temperature, hvac_mode, duration_hours
        )

    def _update_outdoor_temp_history(self, outdoor_temp: float) -> None:
        """Update outdoor temperature history and calculate running mean."""
        now = datetime.now()
        
        # Add current temperature
        self._outdoor_temp_history.append((now, outdoor_temp))
        
        # Remove entries older than 7 days
        seven_days_ago = now - timedelta(days=7)
        self._outdoor_temp_history = [
            (timestamp, temp) for timestamp, temp in self._outdoor_temp_history
            if timestamp > seven_days_ago
        ]
        
        # Calculate running mean (ASHRAE 55 uses 7-day running mean)
        if len(self._outdoor_temp_history) >= 7:  # Need at least 7 data points
            total_temp = sum(temp for _, temp in self._outdoor_temp_history)
            self._running_mean_outdoor_temp = total_temp / len(self._outdoor_temp_history)
        else:
            # If we don't have enough history, use current temperature
            self._running_mean_outdoor_temp = outdoor_temp

    def _update_natural_ventilation_status(self, outdoor_temp: float, indoor_temp: float, comfort_data: dict[str, Any]) -> None:
        """Update natural ventilation status based on conditions."""
        # Natural ventilation is beneficial if:
        # 1. Indoor temp is above comfort zone
        # 2. Outdoor temp is lower than indoor temp
        # 3. The difference is significant (threshold)
        
        comfort_max = comfort_data.get("comfort_temp_max", 28.0)
        natural_vent_threshold = self.config.get("natural_ventilation_threshold", 2.0)
        
        new_status = (indoor_temp > comfort_max and 
                     outdoor_temp < indoor_temp and 
                     (indoor_temp - outdoor_temp) >= natural_vent_threshold)
        
        # Check if natural ventilation status changed
        if new_status != self._natural_ventilation_active:
            self._natural_ventilation_active = new_status
            status_text = "optimal" if new_status else "not recommended"
            temp_diff = indoor_temp - outdoor_temp
            message = f"Natural ventilation is now {status_text} (indoor: {indoor_temp:.1f}°C, outdoor: {outdoor_temp:.1f}°C, diff: {temp_diff:.1f}°C)"
            self._create_logbook_entry(message)
            _LOGGER.info("Natural ventilation status changed: %s", status_text)
        else:
            self._natural_ventilation_active = new_status

    async def update_config(self, config_updates: dict[str, Any]) -> None:
        """Update configuration dynamically."""
        # Update local config
        self.config.update(config_updates)
        
        # Update calculator config
        self.calculator.update_config(self.config)
        
        _LOGGER.info("Configuration updated: %s", config_updates)
        
        # Trigger immediate update
        await self.async_request_refresh()

    async def reset_outdoor_history(self) -> None:
        """Reset outdoor temperature history."""
        self._outdoor_temp_history.clear()
        self._running_mean_outdoor_temp = None
        
        # Create logbook entry
        self._create_logbook_entry("Outdoor temperature history reset")
        
        _LOGGER.info("Outdoor temperature history reset")
        
        # Trigger immediate update
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        """Shutdown coordinator and save final state."""
        try:
            if self.data:
                await self._save_persisted_data(self.data)
                _LOGGER.info("Final state saved to storage during shutdown")
        except Exception as err:
            _LOGGER.warning("Failed to save final state during shutdown: %s", err)
