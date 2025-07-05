"""Adaptive Climate Coordinator."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any
import pytz

from homeassistant.core import HomeAssistant, State, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.storage import Store
from homeassistant.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from homeassistant.const import (
    ATTR_TEMPERATURE,
    ATTR_NAME,
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
    EVENT_ADAPTIVE_CLIMATE_MODE_CHANGE,
    EVENT_ADAPTIVE_CLIMATE_TARGET_TEMP,
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
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MEDIUM),
        )
        
        self.config_entry = config_entry  # Store config entry for accessing options
        
        # Always create a mutable dictionary from the config entry data
        if hasattr(config_entry_data, "mapping"):
            # Handle MappingProxy objects
            self.config = dict(config_entry_data.mapping)
        else:
            # Handle regular dictionaries and other mappings
            self.config = dict(config_entry_data)
            
        # Merge options into config if config_entry is available
        # Note: Options flow removed - all config managed via services
            
        self.calculator = AdaptiveComfortCalculator(self.config)
        
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
            # Start with fresh calculation
            self._error_count = getattr(self, '_error_count', 0)
            
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
                now = dt_util.now()
                if not hasattr(self, '_last_warning_time') or (now - self._last_warning_time).total_seconds() > 300:  # 5 minutes
                    _LOGGER.info("Waiting for required temperature sensors to become available: %s", ", ".join(missing_entities))
                    self._last_warning_time = now
                
                status_message = f"entities_unavailable: {', '.join(missing_entities)}"
                
                # Return previous data if available, or minimal default data
                if self.data:
                    return {**self.data, "status": status_message}
                elif self._last_valid_data:
                    _LOGGER.info("Using last valid persisted data while entities are unavailable")
                    return {**self._last_valid_data, "status": status_message}
                return self._get_default_data(status=status_message)
            
            # Parse temperatures
            try:
                indoor_temp = float(indoor_temp_state.state)
                outdoor_temp = float(outdoor_temp_state.state)
            except (ValueError, TypeError) as exc:
                _LOGGER.warning("Invalid temperature values: indoor=%s, outdoor=%s, error=%s", 
                              indoor_temp_state.state, outdoor_temp_state.state, exc)
                # Return previous data if available, or minimal default data
                if self.data:
                    return {**self.data, "status": "invalid_temperature_values"}
                elif self._last_valid_data:
                    _LOGGER.info("Using last valid persisted data due to invalid temperature values")
                    return {**self._last_valid_data, "status": "invalid_temperature_values"}
                return self._get_default_data(status="invalid_temperature_values")
            
            # Update outdoor temperature history and running mean
            self._update_outdoor_temp_history(outdoor_temp)
            
            # Update occupancy
            self._update_occupancy()
            
            # Check manual override expiry
            self._check_override_expiry()
            
            # Sync options to config before calculations
            self._sync_options_to_config()
            
            # Calculate adaptive parameters using pythermalcomfort
            try:
                # Use pythermalcomfort wrapper for scientific accuracy
                adaptive_result = self.calculator._calculate_pythermalcomfort_adaptive()
                
                if adaptive_result:
                    self._last_pythermalcomfort_result = adaptive_result
                    _LOGGER.debug("pythermalcomfort calculation successful: %s", adaptive_result)
                else:
                    _LOGGER.debug("pythermalcomfort calculation returned None, using fallback")
                    
            except Exception as err:
                _LOGGER.warning("pythermalcomfort calculation failed: %s", err)
                adaptive_result = None
                
                # Extract values from pythermalcomfort result
                adaptive_comfort_temp = adaptive_result["adaptive_comfort_temp"]
                ashrae_compliant = adaptive_result["ashrae_compliant"]
                
                _LOGGER.info(
                    "STAGE2_PYTHERMALCOMFORT: adaptive_comfort_temp=%.1f°C, ashrae_compliant=%s (tdb=%.1f, tr=%.1f, t_rm=%.1f, v=%.2f)",
                    adaptive_comfort_temp,
                    ashrae_compliant,
                    indoor_temp,
                    self._get_mean_radiant_temp() or indoor_temp,
                    self._running_mean_outdoor_temp or outdoor_temp,
                    self.config.get("air_velocity", 0.1)
                )
                
                # Build comfort_data structure compatible with existing code
                comfort_data = {
                    "adaptive_comfort_temp": adaptive_comfort_temp,
                    "ashrae_compliant": ashrae_compliant,
                    "comfort_temp_min": adaptive_comfort_temp - 2.5,  # Default tolerance
                    "comfort_temp_max": adaptive_comfort_temp + 2.5,
                    "outdoor_running_mean": self._running_mean_outdoor_temp or outdoor_temp,
                }
                
            except Exception as err:
                _LOGGER.warning(
                    "STAGE2_PYTHERMALCOMFORT_FALLBACK: Error using pythermalcomfort, falling back to legacy calculator: %s",
                    err
                )
                # Fallback to legacy calculator for backward compatibility
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
                "last_updated": dt_util.now(),
            }
            
            # Log control action
            self._log_control_action(data, control_actions)
            
            # Save valid data for persistence
            self._last_valid_data = data.copy()
            await self._save_persisted_data(data)
            
            return data
            
        except Exception as err:
            self._error_count += 1
            error_type = type(err).__name__
            
            # Special handling for datetime errors - reset the history if we're having timezone issues
            if "offset-naive and offset-aware datetime" in str(err):
                _LOGGER.warning("Timezone mismatch detected - resetting temperature history")
                self._outdoor_temp_history = []  # Reset history
                self._running_mean_outdoor_temp = None
                
                # If this is happening repeatedly, try to recover
                if self._error_count > 3:
                    _LOGGER.warning("Persistent datetime errors - forcing timezone aware timestamps")
                    # Force the coordinator to update with correct timezone info
                    self.hass.async_create_task(self._force_timezone_update())
            
            # Only log full error periodically to avoid log spam
            if self._error_count <= 3 or self._error_count % 10 == 0:  # Log first 3 errors and then every 10th
                _LOGGER.error("Error updating adaptive climate data: %s", err)
            
            # Return previous data if available, or minimal default data
            if self.data:
                return self.data
            elif self._last_valid_data:
                _LOGGER.info("Using last valid persisted data due to update error")
                return self._last_valid_data
            return self._get_default_data()

    def _get_default_data(self, status: str = "entities_unavailable") -> dict[str, Any]:
        """Get default data when entities are unavailable.
        
        Args:
            status: The status to report for diagnostic purposes.
        """
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
            "last_updated": dt_util.now(),
            "status": status,
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
                "last_updated": dt_util.now().isoformat(),
            }
            
            # Save to storage
            await self._store.async_save(storage_data)
        except Exception as err:
            _LOGGER.warning("Failed to save persisted data: %s", err)

    def _create_logbook_entry(self, message: str, entity_id: str | None = None) -> None:
        """Create a logbook entry for important events."""
        try:
            # Se não foi fornecido um entity_id específico, use o ID da entidade de climate
            if entity_id is None:
                entity_id = self.climate_entity_id
                
            # Obter o device_id associado à entidade
            device_info = None
            if hasattr(self, "device_info") and self.device_info:
                device_info = self.device_info
            else:
                # Tenta determinar o device_info a partir da configuração
                device_info = {
                    "identifiers": {(DOMAIN, self.config_entry.entry_id)},
                    "name": self.config.get("name", "Adaptive Climate"),
                }
                
            # Nome do componente para visualização no logbook
            name = f"Adaptive Climate ({self.config.get('name', 'Controller')})"
                
            # Criar a entrada no logbook
            self.hass.bus.async_fire(
                "logbook_entry",
                {
                    LOGBOOK_ENTRY_NAME: name,
                    LOGBOOK_ENTRY_MESSAGE: message,
                    "domain": DOMAIN,
                    "entity_id": entity_id,
                    # Incluir identificadores de dispositivo se disponíveis
                    "device_id": next(iter(device_info["identifiers"]))[1] if device_info and "identifiers" in device_info else None,
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
            if dt_util.now() >= self._override_expiry:
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
        
        # Check if auto shutdown is enabled and environment is unoccupied
        auto_shutdown_enable = self.config.get("auto_shutdown_enable", False)
        prolonged_absence_minutes = self.config.get("prolonged_absence_minutes", 60)

        _LOGGER.debug(
            "Auto shutdown check: occupied=%s, auto_shutdown_enable=%s, prolonged_absence_minutes=%d",
            self._occupied, auto_shutdown_enable, prolonged_absence_minutes
        )

        if not self._occupied and auto_shutdown_enable:
            # Check how long the environment has been unoccupied
            occupancy_state = self.hass.states.get(self.occupancy_entity_id) if self.occupancy_entity_id else None

            _LOGGER.debug(
                "Occupancy entity: %s, state: %s", 
                self.occupancy_entity_id, 
                occupancy_state.state if occupancy_state else "None"
            )

            if occupancy_state and occupancy_state.last_changed:
                time_since_last_presence = dt_util.now() - occupancy_state.last_changed
                minutes_absent = time_since_last_presence.total_seconds() / 60

                _LOGGER.debug(
                    "Absence calculation: last_changed=%s, time_since=%s, minutes_absent=%.1f, threshold=%d",
                    occupancy_state.last_changed, time_since_last_presence, minutes_absent, prolonged_absence_minutes
                )

                # If absent for longer than configured threshold, turn off AC
                if minutes_absent >= prolonged_absence_minutes:
                    current_hvac_mode = climate_state.state
                    
                    _LOGGER.info(
                        "Auto shutdown condition met: absent for %.1f minutes (threshold: %d), current HVAC mode: %s",
                        minutes_absent, prolonged_absence_minutes, current_hvac_mode
                    )

                    if current_hvac_mode != HVACMode.OFF:
                        actions["set_hvac_mode"] = HVACMode.OFF
                        actions["reason"] = f"Auto shutdown after {minutes_absent:.1f} min absence (threshold: {prolonged_absence_minutes} min)"
                        
                        _LOGGER.warning(
                            "AUTO SHUTDOWN TRIGGERED: Setting HVAC to OFF after %.1f minutes absence. "
                            "Current mode: %s, Manual override: %s",
                            minutes_absent, current_hvac_mode, self._manual_override
                        )
                        
                        # Log the exact action that will be executed
                        _LOGGER.info(
                            "Auto shutdown action: %s", 
                            {k: v for k, v in actions.items() if v is not None}
                        )
                        # Return immediately with shutdown action
                        return actions
                    else:
                        actions["reason"] = f"Already off - absent for {minutes_absent:.1f} min"
                        _LOGGER.debug("HVAC already off due to auto shutdown")
                        
                        # Continue with normal logic since already off
                else:
                    remaining_minutes = prolonged_absence_minutes - minutes_absent
                    _LOGGER.debug(
                        "Auto shutdown countdown: %.1f min absent, %.1f min remaining until shutdown",
                        minutes_absent, remaining_minutes
                    )
            else:
                _LOGGER.warning(
                    "Cannot determine absence duration - occupancy_entity_id: %s, occupancy_state: %s, last_changed: %s",
                    self.occupancy_entity_id,
                    occupancy_state.state if occupancy_state else "None",
                    occupancy_state.last_changed if occupancy_state else "None"
                )
        else:
            if self._occupied:
                _LOGGER.debug("Auto shutdown skipped: environment is occupied")
            if not auto_shutdown_enable:
                _LOGGER.debug("Auto shutdown skipped: feature is disabled")

        # Apply occupancy setback if unoccupied (but prioritize cooling/heating when needed)
        if not self._occupied:
            setback_offset = self.config.get("setback_temperature_offset", DEFAULT_SETBACK_TEMPERATURE_OFFSET)
            
            # Get user-configured absolute comfort limits (the real absolute limits)
            min_comfort_limit = self.config.get("min_comfort_temp", 18.0)
            max_comfort_limit = self.config.get("max_comfort_temp", 30.0)
            
            # CRITICAL FIX: When temperature is outside comfort zone, prioritize cooling/heating
            if indoor_temp > comfort_max:
                # Force cooling: indoor is above comfort zone, must cool down
                # Allow minimal setback but ensure cooling happens
                target_temp = max(comfort_max - 0.5, min(comfort_temp + (setback_offset * 0.3), indoor_temp - 0.5))
                actions["reason"] = f"Setback cooling: indoor {indoor_temp:.1f}°C > comfort_max {comfort_max:.1f}°C"
                
            elif indoor_temp < comfort_min:
                # Force heating: indoor is below comfort zone, must heat up  
                # Allow minimal setback but ensure heating happens
                target_temp = min(comfort_min + 0.5, max(comfort_temp - (setback_offset * 0.3), indoor_temp + 0.5))
                actions["reason"] = f"Setback heating: indoor {indoor_temp:.1f}°C < comfort_min {comfort_min:.1f}°C"
                
            elif indoor_temp > comfort_temp:
                # Slightly above comfort temp but within comfort zone
                # Apply setback but don't exceed comfort_max
                target_temp = min(comfort_temp + setback_offset, comfort_max)
                actions["reason"] = f"Setback (unoccupied): {setback_offset}°C offset, within comfort zone"
                
            else:
                # Below or at comfort temp, apply heating setback
                # Apply setback but don't go below comfort_min
                target_temp = max(comfort_temp - setback_offset, comfort_min)
                actions["reason"] = f"Setback (unoccupied): {setback_offset}°C offset, within comfort zone"
            
            # Ensure target stays within user-configured absolute comfort limits
            target_temp = max(min_comfort_limit, min(target_temp, max_comfort_limit))
            
            _LOGGER.debug(
                "Setback logic: indoor=%.1f°C, comfort=%.1f°C, comfort_zone=[%.1f-%.1f]°C, target=%.1f°C",
                indoor_temp, comfort_temp, comfort_min, comfort_max, target_temp
            )
        else:
            # When occupied, use the comfort temperature directly
            target_temp = comfort_temp
            actions["reason"] = "Occupied - using comfort temperature"
            
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
            action_details = {}
            climate_state = self.hass.states.get(self.climate_entity_id)
            
            # Collect current state information for comparison
            current_state = {
                "hvac_mode": climate_state.state if climate_state else "unknown",
                "temperature": climate_state.attributes.get(ATTR_TEMPERATURE) if climate_state else None,
                "fan_mode": climate_state.attributes.get(ATTR_FAN_MODE) if climate_state else None,
            }
            
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
                # Safe format the temperature
                temp_value = actions['set_temperature']
                action_messages.append(f"Temperature set to {float(temp_value):.1f}°C" if temp_value is not None else "Temperature set")
                action_details["temperature"] = {
                    "new": actions["set_temperature"],
                    "old": current_state["temperature"],
                }
                
                # Fire event for logbook
                climate_entity = self.hass.states.get(self.climate_entity_id)
                climate_name = climate_entity.attributes.get("friendly_name", self.climate_entity_id) if climate_entity else self.climate_entity_id
                
                self.hass.bus.async_fire(
                    EVENT_ADAPTIVE_CLIMATE_TARGET_TEMP,
                    {
                        "entity_id": self.climate_entity_id,
                        ATTR_NAME: climate_name,
                        "old_temp": current_state["temperature"],
                        "new_temp": actions["set_temperature"],
                        "reason": actions.get("reason", "adaptive control")
                    },
                )
            
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
                action_details["hvac_mode"] = {
                    "new": actions["set_hvac_mode"],
                    "old": current_state["hvac_mode"],
                }
                
                # Fire event for logbook
                climate_entity = self.hass.states.get(self.climate_entity_id)
                climate_name = climate_entity.attributes.get("friendly_name", self.climate_entity_id) if climate_entity else self.climate_entity_id
                
                self.hass.bus.async_fire(
                    EVENT_ADAPTIVE_CLIMATE_MODE_CHANGE,
                    {
                        "entity_id": self.climate_entity_id,
                        ATTR_NAME: climate_name,
                        "old_mode": current_state["hvac_mode"],
                        "new_mode": actions["set_hvac_mode"],
                        "reason": actions.get("reason", "adaptive control")
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
                action_messages.append(f"Fan mode set to {actions['set_fan_mode']}")
                action_details["fan_mode"] = {
                    "new": actions["set_fan_mode"],
                    "old": current_state["fan_mode"],
                }
            
            # Create logbook entry if any actions were taken
            if action_messages:
                reason = actions.get("reason", "adaptive control")
                
                # Criar uma mensagem mais detalhada para o logbook
                if not self._occupied and "auto_shutdown" in reason:
                    # Caso especial: desligamento automático devido a ausência prolongada
                    last_presence = "unknown"
                    if self.occupancy_entity_id:
                        occupancy_state = self.hass.states.get(self.occupancy_entity_id)
                        if occupancy_state and occupancy_state.last_changed:
                            try:
                                last_presence = occupancy_state.last_changed.strftime('%H:%M:%S')
                            except (AttributeError, TypeError):
                                last_presence = "format error"
                    
                    minutes = self.config.get("prolonged_absence_minutes", 60)
                    message = (
                        f"Adaptive Climate Auto shutdown activated due to prolonged absence ({minutes} min). "
                        f"HVAC turned off for energy saving. Last presence: {last_presence} "
                        f"triggered by action Climate: {', '.join(action_messages)}"
                    )
                else:
                    # Mensagem padrão para outras ações
                    changes = []
                    if "temperature" in action_details:
                        old_temp = action_details["temperature"]["old"]
                        new_temp = action_details["temperature"]["new"]
                        # Safe format temperature values
                        old_temp_str = f"{float(old_temp):.1f}" if old_temp is not None else "unknown"
                        new_temp_str = f"{float(new_temp):.1f}" if new_temp is not None else "unknown"
                        changes.append(f"temperature from {old_temp_str}°C to {new_temp_str}°C")
                    
                    if "hvac_mode" in action_details:
                        old_mode = action_details["hvac_mode"]["old"]
                        new_mode = action_details["hvac_mode"]["new"]
                        changes.append(f"mode from {old_mode} to {new_mode}")
                    
                    if "fan_mode" in action_details:
                        old_fan = action_details["fan_mode"]["old"]
                        new_fan = action_details["fan_mode"]["new"]
                        changes.append(f"fan from {old_fan} to {new_fan}")
                    
                    changes_text = ", ".join(changes)
                    message = f"Climate adjusted: {changes_text} ({reason})"
                
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
            
            # Obtenha o estado atual do clima para comparações
            climate_state = self.hass.states.get(self.climate_entity_id)
            current_hvac_mode = climate_state.state if climate_state else "unknown"
            current_temp = climate_state.attributes.get(ATTR_TEMPERATURE, 0) if climate_state else 0
            current_fan = climate_state.attributes.get(ATTR_FAN_MODE, "unknown") if climate_state else "unknown"
            
            # Determinar alteração do modo HVAC
            hvac_change = ""
            if actions.get("set_hvac_mode") is not None:
                hvac_change = f" (was {current_hvac_mode})"
            
            # Determinar alteração do modo do ventilador
            fan_change = ""
            if actions.get("set_fan_mode") is not None:
                fan_change = f" (was {current_fan})"
            
            # Obter offsets para detalhamento - obtenha dos dados ou use valores padrão de 0
            air_velocity_offset = data.get("air_velocity_offset", 0)
            humidity_offset = data.get("humidity_offset", 0)
            
            # Obter hora da última presença, se disponível
            last_presence_time = ""
            if not self._occupied and self.occupancy_entity_id:
                occupancy_state = self.hass.states.get(self.occupancy_entity_id)
                if occupancy_state and occupancy_state.last_changed:
                    try:
                        last_presence_time = f", Last presence: {occupancy_state.last_changed.strftime('%H:%M:%S')}"
                    except (AttributeError, TypeError):
                        last_presence_time = ", Last presence: unknown (format error)"
            
            # Determine which action is being triggered
            trigger_action = "Climate:"
            if actions.get("set_temperature") is not None:
                trigger_action += " Set temperature"
            if actions.get("set_hvac_mode") is not None:
                trigger_action += " Set HVAC mode"
            if actions.get("set_fan_mode") is not None:
                trigger_action += " Set fan mode"
            
            # Safe format all values before building the log message
            target_temp = actions.get('set_temperature', current_temp)
            target_temp_str = f"{float(target_temp):.1f}" if target_temp is not None else "N/A"
            current_temp_str = f"{float(current_temp):.1f}" if current_temp is not None else "N/A"
            indoor_temp_str = f"{float(indoor_temp):.1f}" if indoor_temp is not None else "N/A"
            outdoor_temp_str = f"{float(outdoor_temp):.1f}" if outdoor_temp is not None else "N/A"
            comfort_min_str = f"{float(comfort_min):.1f}" if comfort_min is not None else "N/A"
            comfort_max_str = f"{float(comfort_max):.1f}" if comfort_max is not None else "N/A"
            comfort_temp_str = f"{float(comfort_temp):.1f}" if comfort_temp is not None else "N/A"
            comfort_tolerance = self.calculator.get_comfort_tolerance()
            comfort_tolerance_str = f"{float(comfort_tolerance):.1f}" if comfort_tolerance is not None else "N/A"
            air_velocity_offset_str = f"{float(air_velocity_offset):.1f}" if air_velocity_offset is not None else "N/A"
            humidity_offset_str = f"{float(humidity_offset):.1f}" if humidity_offset is not None else "N/A"
            
            log_message = (
                f"Target: {target_temp_str}°C (Current: {current_temp_str}°C), "
                f"Indoor: {indoor_temp_str}°C, Outdoor: {outdoor_temp_str}°C, "
                f"Comfort zone: {comfort_min_str}-{comfort_max_str}°C (adaptive temp: {comfort_temp_str}°C), "
                f"HVAC Mode: {actions.get('set_hvac_mode', current_hvac_mode)} ({actions.get('reason', 'adaptive control')}){hvac_change}, "
                f"Occupancy: {'Occupied' if self._occupied else 'Unoccupied'}{last_presence_time}, "
                f"Category: {self.config.get('comfort_category', 'II')} (±{comfort_tolerance_str}°C), "
                f"Air velocity offset: {air_velocity_offset_str}°C, Humidity offset: {humidity_offset_str}°C, "
                f"Fan: {actions.get('set_fan_mode', current_fan)}{fan_change}, "
                f"Compliance: \"{data.get('ashrae_compliant', False) and 'Compliant' or 'Non-compliant'}\" "
                f"triggered by action {trigger_action}"
            )
            
            _LOGGER.info(log_message)
            
            # Também criar entrada no logbook com informações mais detalhadas
            device_name = self.config.get("name", "Adaptive Climate")
            # Safe formatting of temperature values for logbook
            target_temp = actions.get('set_temperature', current_temp)
            target_temp_str = f"{float(target_temp):.1f}" if target_temp is not None else "N/A"
            indoor_temp_str = f"{float(indoor_temp):.1f}" if indoor_temp is not None else "N/A"
            outdoor_temp_str = f"{float(outdoor_temp):.1f}" if outdoor_temp is not None else "N/A"
            comfort_min_str = f"{float(comfort_min):.1f}" if comfort_min is not None else "N/A"
            comfort_max_str = f"{float(comfort_max):.1f}" if comfort_max is not None else "N/A"
            
            logbook_message = (
                f"{device_name}: {trigger_action} - "
                f"Target: {target_temp_str}°C, "
                f"Indoor: {indoor_temp_str}°C, Outdoor: {outdoor_temp_str}°C, "
                f"Comfort: {comfort_min_str}-{comfort_max_str}°C, "
                f"Mode: {actions.get('set_hvac_mode', current_hvac_mode)}{hvac_change}"
            )
            self._create_logbook_entry(logbook_message, self.climate_entity_id)

    async def set_manual_override(self, temperature: float, duration: int | None = None) -> None:
        """Set manual override."""
        self._manual_override = True
        self._last_target_temp = temperature
        
        if duration:
            self._override_expiry = dt_util.now() + timedelta(seconds=duration)
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
        # Safe temperature formatting
        temp_str = f"{float(temperature):.1f}" if temperature is not None else "custom"
        message = f"Manual override activated: {temp_str}°C{duration_text}"
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
        now = dt_util.now()
        
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
            # Safe format temperature values
            indoor_str = f"{float(indoor_temp):.1f}" if indoor_temp is not None else "N/A"
            outdoor_str = f"{float(outdoor_temp):.1f}" if outdoor_temp is not None else "N/A"
            diff_str = f"{float(temp_diff):.1f}" if temp_diff is not None else "N/A"
            message = f"Natural ventilation is now {status_text} (indoor: {indoor_str}°C, outdoor: {outdoor_str}°C, diff: {diff_str}°C)"
            self._create_logbook_entry(message)
            _LOGGER.info("Natural ventilation status changed: %s", status_text)
        else:
            self._natural_ventilation_active = new_status

    async def update_config(self, config_updates: dict[str, Any]) -> None:
        """Update configuration dynamically."""
        try:
            # Always create a fresh mutable copy from the original config
            if hasattr(self.config, "mapping"):
                # Handle MappingProxy objects
                updated_config = dict(self.config.mapping)
            elif hasattr(self.config, "items"):
                # Handle dict-like objects
                updated_config = dict(self.config)
            else:
                # Fallback for other cases
                _LOGGER.warning("Config object type not recognized: %s", type(self.config))
                updated_config = {}
                
            # Update the copy with new values
            updated_config.update(config_updates)
            
            # Replace the original config with the updated copy
            self.config = updated_config
            
            # Update calculator config
            self.calculator.update_config(self.config)
            
            _LOGGER.info("Configuration updated: %s", config_updates)
            
            # Trigger immediate update
        except Exception as err:
            _LOGGER.error("Failed to update configuration: %s - %s", type(err).__name__, err)
        await self.async_request_refresh()

    async def reset_outdoor_history(self) -> None:
        """Reset outdoor temperature history."""
        self._outdoor_temp_history.clear()
        self._running_mean_outdoor_temp = None
        _LOGGER.info("Outdoor temperature history reset")

    async def async_update_config_value(self, key: str, value: Any) -> None:
        """Update a single configuration value and notify entities.
        
        This method is thread-safe and prevents race conditions during
        concurrent configuration updates.
        """
        # Use asyncio.Lock to prevent race conditions
        if not hasattr(self, '_config_update_lock'):
            import asyncio
            self._config_update_lock = asyncio.Lock()
            
        async with self._config_update_lock:
            try:
                _LOGGER.debug("Acquiring config update lock for key: %s", key)
                
                # Always create a fresh mutable copy from the original config
                if hasattr(self.config, "mapping"):
                    # Handle MappingProxy objects
                    updated_config = dict(self.config.mapping)
                elif hasattr(self.config, "items"):
                    # Handle dict-like objects
                    updated_config = dict(self.config)
                else:
                    # Fallback for other cases
                    _LOGGER.warning("Config object type not recognized: %s", type(self.config))
                    updated_config = {}
                    
                # Validate value before updating
                old_value = updated_config.get(key)
                if old_value == value:
                    _LOGGER.debug("Configuration value unchanged: %s = %s", key, value)
                    return
                    
                # Update the specific key
                updated_config[key] = value
                
                # Replace the original config with the updated copy
                self.config = updated_config
                
                # Update calculator config
                self.calculator.update_config(self.config)
                
                # Update the coordinator data to reflect the change atomically
                if self.data is None:
                    self.data = {}
                self.data = dict(self.data)  # Create a copy to avoid mutations
                self.data[key] = value
                
                _LOGGER.info("Configuration value updated: %s = %s (was: %s)", key, value, old_value)
                
                # Notify all entities of the update
                self.async_update_listeners()
                
                # Trigger a refresh to recalculate with new config
                # Use a slight delay to allow batching of multiple updates
                if not hasattr(self, '_refresh_pending'):
                    self._refresh_pending = True
                    async def delayed_refresh():
                        await asyncio.sleep(0.1)  # 100ms debounce
                        self._refresh_pending = False
                        await self.async_request_refresh()
                    
                    # Schedule the delayed refresh
                    asyncio.create_task(delayed_refresh())
                
            except Exception as err:
                _LOGGER.error("Failed to update configuration value %s: %s - %s", key, type(err).__name__, err)
                raise

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with optional default."""
        try:
            return self.config.get(key, default)
        except Exception as err:
            _LOGGER.error("Failed to get configuration value %s: %s - %s", key, type(err).__name__, err)
            return default

    async def async_update_options(self, options: dict[str, Any]) -> None:
        """Update options from options flow."""
        try:
            async with self._update_lock:
                _LOGGER.info("Updating coordinator options: %s", options)
                
                # Update configuration with new options
                for key, value in options.items():
                    if key in self.config:
                        old_value = self.config[key]
                        self.config[key] = value
                        _LOGGER.debug("Updated option %s: %s -> %s", key, old_value, value)
                    else:
                        self.config[key] = value
                        _LOGGER.debug("Added new option %s: %s", key, value)
                
                # Update the calculator with new config
                self.calculator.update_config(self.config)
                
                # Notify all entities of the update
                self.async_update_listeners()
                
                # Trigger a refresh to recalculate with new options
                await self.async_request_refresh()
                
                _LOGGER.info("Options update completed successfully")
                
        except Exception as err:
            _LOGGER.error("Failed to update options: %s - %s", type(err).__name__, err)
            raise
