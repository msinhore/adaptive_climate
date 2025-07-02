"""Adaptive Climate Coordinator."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import (
    ATTR_TEMPERATURE,
    SERVICE_SET_TEMPERATURE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_FAN_MODE,
    STATE_ON,
    STATE_OFF,
    STATE_UNKNOWN,
    STATE_UNAVAILABLE,
)
from homeassistant.components.climate.const import (
    DOMAIN as CLIMATE_DOMAIN,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    HVAC_MODE_AUTO,
    ATTR_HVAC_MODE,
    ATTR_FAN_MODE,
)

from .const import (
    DOMAIN,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
    DEFAULT_SETBACK_TEMPERATURE_OFFSET,
)
from .ashrae_calculator import ASHRAECalculator

_LOGGER = logging.getLogger(__name__)


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
            update_interval=timedelta(minutes=DEFAULT_UPDATE_INTERVAL),
        )
        
        self.config = config_entry_data
        self.calculator = ASHRAECalculator(config_entry_data)
        
        # State tracking
        self._manual_override = False
        self._override_expiry: datetime | None = None
        self._last_target_temp: float | None = None
        self._occupied = True
        self._natural_ventilation_active = False
        
        # Entity IDs from config
        self.climate_entity_id = config_entry_data["climate_entity"]
        self.indoor_temp_entity_id = config_entry_data["indoor_temp_sensor"]
        self.outdoor_temp_entity_id = config_entry_data["outdoor_temp_sensor"]
        self.occupancy_entity_id = config_entry_data.get("occupancy_sensor")
        
        # Set up state listeners
        self._setup_listeners()

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data."""
        try:
            # Get current states
            climate_state = self.hass.states.get(self.climate_entity_id)
            indoor_temp_state = self.hass.states.get(self.indoor_temp_entity_id)
            outdoor_temp_state = self.hass.states.get(self.outdoor_temp_entity_id)
            
            if not climate_state or not indoor_temp_state or not outdoor_temp_state:
                _LOGGER.warning("Required entities not available")
                return {}
            
            # Parse temperatures
            try:
                indoor_temp = float(indoor_temp_state.state)
                outdoor_temp = float(outdoor_temp_state.state)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid temperature values")
                return {}
            
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
                "occupancy": "occupied" if self._occupied else "unoccupied",
                "manual_override": self._manual_override,
                "natural_ventilation_active": self._natural_ventilation_active,
                "control_actions": control_actions,
                "last_updated": datetime.now(),
            }
            
            # Log control action
            self._log_control_action(data, control_actions)
            
            return data
            
        except Exception as err:
            _LOGGER.error("Error updating adaptive climate data: %s", err)
            raise

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
        # Trigger coordinator update
        self.async_set_updated_data(self.data or {})

    def _update_occupancy(self) -> None:
        """Update occupancy status."""
        if not self.occupancy_entity_id:
            return
        
        occupancy_state = self.hass.states.get(self.occupancy_entity_id)
        if occupancy_state and occupancy_state.state in (STATE_ON, STATE_OFF):
            self._occupied = occupancy_state.state == STATE_ON

    def _check_override_expiry(self) -> None:
        """Check if manual override has expired."""
        if self._manual_override and self._override_expiry:
            if datetime.now() >= self._override_expiry:
                self._manual_override = False
                self._override_expiry = None
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
            if current_hvac_mode != HVAC_MODE_COOL:
                actions["set_hvac_mode"] = HVAC_MODE_COOL
                actions["reason"] += f" (above comfort zone)" if actions["reason"] else "above comfort zone"
        elif indoor_temp < comfort_min:
            # Too cold - heating needed
            if current_hvac_mode != HVAC_MODE_HEAT:
                actions["set_hvac_mode"] = HVAC_MODE_HEAT
                actions["reason"] += f" (below comfort zone)" if actions["reason"] else "below comfort zone"
        else:
            # In comfort zone - could turn off or use auto
            if current_hvac_mode in [HVAC_MODE_COOL, HVAC_MODE_HEAT]:
                actions["set_hvac_mode"] = HVAC_MODE_AUTO
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
                
        except Exception as err:
            _LOGGER.error("Error executing control actions: %s", err)

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
        
        _LOGGER.info("Manual override set to %.1f°C%s", 
                    temperature, 
                    f" for {duration}s" if duration else "")

    async def clear_manual_override(self) -> None:
        """Clear manual override."""
        self._manual_override = False
        self._override_expiry = None
        _LOGGER.info("Manual override cleared, returning to adaptive control")
        
        # Trigger immediate update
        await self.async_request_refresh()

    async def update_comfort_category(self, category: str) -> None:
        """Update comfort category."""
        if category in ["I", "II", "III"]:
            self.config["comfort_category"] = category
            self.calculator.update_config(self.config)
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
