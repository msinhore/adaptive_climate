"""Adaptive Climate Coordinator."""

from __future__ import annotations

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional

from homeassistant.core import HomeAssistant, State, callback
from homeassistant.util import dt as dt_util
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.storage import Store
from homeassistant.const import (
    ATTR_TEMPERATURE, STATE_ON, STATE_OFF, STATE_UNKNOWN, STATE_UNAVAILABLE,
)
from homeassistant.components.climate.const import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate import HVACMode

from .const import (
    DOMAIN, UPDATE_INTERVAL_MEDIUM,
)
from .calculator import calculate_hvac_and_fan

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "adaptive_climate_data"


class AdaptiveClimateCoordinator(DataUpdateCoordinator):
    """Coordinator for adaptive climate control."""

    def __init__(self, hass: HomeAssistant, config_entry_data: dict[str, Any]) -> None:
        """Initialize."""
        super().__init__(hass, _LOGGER, name=DOMAIN,
                         update_interval=timedelta(minutes=UPDATE_INTERVAL_MEDIUM))

        self.config = dict(config_entry_data)

        self._manual_override = False
        self._override_expiry: Optional[datetime] = None
        self._last_target_temp: Optional[float] = None
        self._occupied = True
        self._last_no_occupancy: Optional[datetime] = None

        self._outdoor_temp_history: list[tuple[datetime, float]] = []
        self._running_mean_outdoor_temp: Optional[float] = None
        self._presence_returned_at = None

        self._store = Store(hass, STORAGE_VERSION,
                            f"{STORAGE_KEY}_{self.config.get('name', 'default')}")
        self._last_valid_params: Optional[dict[str, Any]] = None

        # Entities
        self.climate_entity_id = self.config["climate_entity"]
        self.indoor_temp_sensor_id = self.config["indoor_temp_sensor"]
        self.outdoor_temp_sensor_id = self.config["outdoor_temp_sensor"]
        self.indoor_humidity_sensor_id = self.config.get("indoor_humidity_sensor")
        self.outdoor_humidity_sensor_id = self.config.get("outdoor_humidity_sensor")
        self.occupancy_sensor_id = self.config.get("occupancy_sensor")

        # Sensor  fallbacks
        self._last_valid_indoor_temp = None
        self._last_valid_outdoor_temp = None
        self._last_valid_indoor_humidity = None
        self._last_valid_outdoor_humidity = None

        self._setup_listeners()
        self.hass.async_create_task(self._load_persisted_data())

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest data and determine actions."""
        indoor_temp = self._get_value(self.indoor_temp_sensor_id, "indoor_temp")
        outdoor_temp = self._get_value(self.outdoor_temp_sensor_id, "outdoor_temp")
        indoor_humidity = self._get_value(self.indoor_humidity_sensor_id, "indoor_humidity")
        outdoor_humidity = self._get_value(self.outdoor_humidity_sensor_id, "outdoor_humidity")

        if indoor_temp is None or outdoor_temp is None:
            _LOGGER.warning(f"[{self.config.get('name')}] Indoor or outdoor temperature unavailable. Skipping update.")
            return self._last_valid_params or self._default_params("entities_unavailable")

        self._update_outdoor_temp_history(outdoor_temp)
        self._update_occupancy()
        self._check_override_expiry()

        climate_state = self.hass.states.get(self.climate_entity_id)
        auto_start_enable = self.config.get("auto_start_enable", False)
        auto_start_minutes = self.config.get("auto_start_minutes", 5)

        if not climate_state or climate_state.state == HVACMode.OFF:
            # If was auto_shutdown and presence returned, verifies auto_start
            if getattr(self, "_system_turned_off", False) and self._occupied and self._presence_returned_at:
                if self.config.get("auto_start_enable", False):
                    auto_start_minutes = self.config.get("auto_start_minutes", 5)
                    elapsed = (dt_util.now() - self._presence_returned_at).total_seconds() / 60
                    if elapsed >= auto_start_minutes:
                        _LOGGER.info(f"[{self.config.get('name')}] Presence returned after {elapsed:.1f} minutes. Starting AC.")
                        self._system_turned_off = False
                        # Continue normal flow to re-start the AC
                    else:
                        _LOGGER.debug(f"[{self.config.get('name')}] Presence returned but not enough time elapsed ({elapsed:.1f} min). Skipping auto start.")
                        return self._last_valid_params or self._default_params("waiting_presence")
                else:
                    _LOGGER.info(f"[{self.config.get('name')}] Presence returned but auto start is disabled. Skipping.")
                    return self._last_valid_params or self._default_params("waiting_presence")
            elif getattr(self, "_system_turned_off", False):
                # If system turned off by itself and no presence, do nothing
                return self._last_valid_params or self._default_params("ac_off") 
            else:
                _LOGGER.debug(f"[{self.config.get('name')}] {self.climate_entity_id} is off (by user?). Skipping automatic actions.")
                return self._last_valid_params or self._default_params("ac_off")
    
        # Auto shutdown logic
        if self.config.get("auto_shutdown_enable", False):
            shutdown_minutes = self.config.get("auto_shutdown_minutes", 60)
            if climate_state.state != HVACMode.OFF and not self._occupied:
                if self._last_no_occupancy is None:
                    self._last_no_occupancy = dt_util.now()
                elapsed = (dt_util.now() - self._last_no_occupancy).total_seconds() / 60
                if elapsed < shutdown_minutes:
                    _LOGGER.debug(f"[{self.config.get('name')}] No occupancy detected for {elapsed:.1f} minutes of {shutdown_minutes}; waiting for shutdown threshold.")
                elif elapsed >= shutdown_minutes:
                    _LOGGER.info(f"[{self.config.get('name')}] No occupancy for {elapsed:.1f} minutes of {shutdown_minutes}; shutting down AC.")
                    self._system_turned_off = True 
                    await self._shutdown_climate()
                    return self._last_valid_params or self._default_params("auto_shutdown")
            else:
                 self._last_no_occupancy = None

        comfort_params = calculate_hvac_and_fan(
            indoor_temp=indoor_temp,
            outdoor_temp=outdoor_temp,
            min_temp=self.config.get("min_comfort_temp", 21),
            max_temp=self.config.get("max_comfort_temp", 27),
            season=self.config.get("season", "summer"),
            category=self.config.get("comfort_category", "II"),
            air_velocity=self.config.get("air_velocity", "low"),
            mean_radiant_temp=self._get_value(self.config.get("mean_radiant_temp_sensor")),
            indoor_humidity=indoor_humidity,
            outdoor_humidity=outdoor_humidity,
            running_mean_outdoor_temp=self._running_mean_outdoor_temp,
            energy_save_mode=self.config.get("energy_save_mode", True),
        )

        _LOGGER.debug(f"[{self.config.get('name')}] Calculated comfort parameters: {comfort_params}")

        control_actions = self._determine_actions(indoor_temp, comfort_params)
        _LOGGER.debug(f"[{self.config.get('name')}] Determined control actions: {control_actions}")

        if not self._manual_override:
            await self._execute_actions(control_actions)
        else:
            _LOGGER.info(f"[{self.config.get('name')}] Manual override active. Skipping automatic control actions.")

        params = self._build_params(indoor_temp, outdoor_temp, indoor_humidity, outdoor_humidity, comfort_params, control_actions)
        self._last_valid_params = params.copy()
        await self._save_persisted_data(params)

        return params

    async def update_config(self, new_config: dict[str, Any]) -> None:
        """Update the coordinator configuration with new values."""
        self.config.update(new_config)
        _LOGGER.debug(f"[{self.config.get('name')}] Coordinator configuration updated: {new_config}")
        await self.async_request_refresh()

    # Helpers

    def _get_value(self, entity_id: Optional[str], sensor_type: Optional[str] = None) -> Optional[float]:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                value = float(state.state)
                # Saves the last valid reading for each sensor type
                if sensor_type == "indoor_temp":
                    self._last_valid_indoor_temp = value
                elif sensor_type == "outdoor_temp":
                    self._last_valid_outdoor_temp = value
                elif sensor_type == "indoor_humidity":
                    self._last_valid_indoor_humidity = value
                elif sensor_type == "outdoor_humidity":
                    self._last_valid_outdoor_humidity = value
                return value
            except (ValueError, TypeError):
                _LOGGER.warning(f"[{self.config.get('name')}] Failed to convert state '{state.state}' of {entity_id} to float.")
                return None
        # If unavailable, returns the last valid read
        if sensor_type == "indoor_temp":
            return self._last_valid_indoor_temp
        elif sensor_type == "outdoor_temp":
            return self._last_valid_outdoor_temp
        elif sensor_type == "indoor_humidity":
            return self._last_valid_indoor_humidity
        elif sensor_type == "outdoor_humidity":
            return self._last_valid_outdoor_humidity
        return None

    def _build_params(self, indoor, outdoor, indoor_hum, outdoor_hum, comfort, actions) -> dict[str, Any]:
        return {
            "adaptive_comfort_temp": comfort.get("comfort_temp"),
            "comfort_temp_min": comfort.get("comfort_min_ashrae"),
            "comfort_temp_max": comfort.get("comfort_max_ashrae"),
            "indoor_temperature": indoor,
            "outdoor_temperature": outdoor,
            "indoor_humidity": indoor_hum,
            "outdoor_humidity": outdoor_hum,
            "running_mean_outdoor_temp": self._running_mean_outdoor_temp,
            "occupancy": "occupied" if self._occupied else "unoccupied",
            "manual_override": self._manual_override,
            "control_actions": actions,
            "ashrae_compliant": comfort.get("ashrae_compliant"),
            "last_updated": dt_util.now(),
        }

    def _default_params(self, status: str) -> dict[str, Any]:
        return {
            "adaptive_comfort_temp": 22.0,
            "comfort_temp_min": 20.0,
            "comfort_temp_max": 24.0,
            "status": status,
        }

    def _update_outdoor_temp_history(self, outdoor_temp: float) -> None:
        now = dt_util.now()
        self._outdoor_temp_history.append((now, outdoor_temp))
        self._outdoor_temp_history = [(ts, temp) for ts, temp in self._outdoor_temp_history
                                      if ts > now - timedelta(days=7)]
        temps = [temp for _, temp in self._outdoor_temp_history]
        self._running_mean_outdoor_temp = sum(temps) / len(temps) if temps else outdoor_temp

    def _update_occupancy(self) -> None:
        if not self.occupancy_sensor_id:
            return
        was_occupied = self._occupied
        state = self.hass.states.get(self.occupancy_sensor_id)
        if state and state.state in (STATE_ON, STATE_OFF):
            self._occupied = state.state == STATE_ON

        if self._occupied:
            if not was_occupied:
                self._presence_returned_at = dt_util.now()
            self._last_no_occupancy = None
        else:
            if self._last_no_occupancy is None:
                self._last_no_occupancy = dt_util.now()
            self._presence_returned_at = None

    def _check_override_expiry(self) -> None:
        if self._manual_override and self._override_expiry:
            remaining = (self._override_expiry - dt_util.now()).total_seconds()
            if remaining > 0:
                _LOGGER.debug(f"[{self.config.get('name')}] Manual override active. Time remaining: {remaining/60:.1f} minutes.")
            if dt_util.now() >= self._override_expiry:
                _LOGGER.info(f"[{self.config.get('name')}] Manual override expired.")
                self._manual_override = False
                self._override_expiry = None

    def _determine_actions(self, indoor_temp: float, comfort: dict[str, Any]) -> dict[str, Any]:
        """Determine control actions based on comfort calculation and supported HVAC modes."""
        target_temp = comfort.get("comfort_temp", indoor_temp)
        hvac_mode = comfort.get("hvac_mode", "off")
        fan_mode = comfort.get("fan_mode", "off")

        _LOGGER.debug(f"[{self.config.get('name')}] Initial determine_actions: target_temp={target_temp}, hvac_mode={hvac_mode}, fan_mode={fan_mode}")

        # Do not switch off for comfort if energy_save_mode is False
        if not self.config.get("energy_save_mode", True) and hvac_mode == HVACMode.OFF:
            state = self.hass.states.get(self.climate_entity_id)
            _LOGGER.debug(f"[{self.config.get('name')}] energy_save_mode is False and calculated hvac_mode is OFF. Current state: {state.state if state else 'unknown'}")
            if state and state.state != HVACMode.OFF:
                _LOGGER.debug(f"[{self.config.get('name')}] Overriding hvac_mode OFF to {state.state} and fan_mode to {state.attributes.get('fan_mode', fan_mode)}")
                hvac_mode = state.state
                fan_mode = state.attributes.get("fan_mode", fan_mode)
    
        state = self.hass.states.get(self.climate_entity_id)
        supported_modes = []
        if state:
            supported_modes = [str(mode) for mode in state.attributes.get("hvac_modes", [])]
        _LOGGER.debug(f"[{self.config.get('name')}] Supported hvac_modes: {supported_modes}")

        hvac_mode_str = str(hvac_mode)
        if hvac_mode_str not in supported_modes:
            _LOGGER.warning(f"[{self.config.get('name')}] hvac_mode '{hvac_mode_str}' not supported by {self.climate_entity_id}. Falling back to OFF.")
            if str(HVACMode.FAN_ONLY) in supported_modes:
                hvac_mode = HVACMode.FAN_ONLY
            else:
                hvac_mode = state.state if state else HVACMode.OFF
        _LOGGER.debug(f"[{self.config.get('name')}] Final determine_actions: set_temperature={target_temp}, set_hvac_mode={hvac_mode}, set_fan_mode={fan_mode}")
        return {
            "set_temperature": target_temp,
            "set_hvac_mode": hvac_mode,
            "set_fan_mode": fan_mode,
            "reason": {
                f"Calculated {hvac_mode}, temperature{target_temp}, "
                f"fan mode: {fan_mode} based on comfort, adjusted for supported modes.",
            }
        }

    async def _execute_actions(self, actions: dict[str, Any]) -> None:
        """Update temperature and fan_mode before setting hvac_mode, with delays between calls."""

        state = self.hass.states.get(self.climate_entity_id)
        if not state or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            _LOGGER.warning(f"[{self.config.get('name')}] {self.climate_entity_id} unavailable, skipping action execution.")
            return

        current_hvac_mode = state.state
        current_temp = state.attributes.get("temperature")
        current_fan_mode = state.attributes.get("fan_mode")

        target_temp = actions["set_temperature"]
        target_hvac_mode = actions["set_hvac_mode"]
        target_fan_mode = actions.get("set_fan_mode")

        changed = False

        # Set temperature if needed
        if target_temp is not None and (current_temp is None or abs(target_temp - current_temp) >= 0.5):
            await self.hass.services.async_call(
                CLIMATE_DOMAIN,
                "set_temperature",
                {
                    "entity_id": self.climate_entity_id,
                    "temperature": target_temp,
                },
            )
            await asyncio.sleep(0.5)
            changed = True

        # Set fan mode if needed
        if target_fan_mode and target_fan_mode != current_fan_mode:
            await self.hass.services.async_call(
                CLIMATE_DOMAIN,
                "set_fan_mode",
                {
                    "entity_id": self.climate_entity_id,
                    "fan_mode": target_fan_mode,
                },
            )
            await asyncio.sleep(0.5)
            changed = True

        # If changing to a mode different from current and not OFF, send OFF first
        if (
            target_hvac_mode != current_hvac_mode
            and target_hvac_mode != HVACMode.OFF
            and current_hvac_mode != HVACMode.OFF
        ):
            _LOGGER.info(
                f"[{self.config.get('name')}] Sending intermediate OFF before changing hvac_mode from {current_hvac_mode} to {target_hvac_mode} on {self.climate_entity_id}"
            )
            await self.hass.services.async_call(
                CLIMATE_DOMAIN,
                "set_hvac_mode",
                {
                    "entity_id": self.climate_entity_id,
                    "hvac_mode": HVACMode.OFF,
                },
            )
            await asyncio.sleep(0.5)

        # Set hvac mode if needed
        if target_hvac_mode != current_hvac_mode:
            await self.hass.services.async_call(
                CLIMATE_DOMAIN,
                "set_hvac_mode",
                {
                    "entity_id": self.climate_entity_id,
                    "hvac_mode": target_hvac_mode,
                },
            )
            changed = True

        if changed:
            _LOGGER.info(
                f"[{self.config.get('name')}] Set temperature={target_temp}, fan_mode={target_fan_mode}, hvac_mode={target_hvac_mode} on {self.climate_entity_id}"
            )
        else:
            _LOGGER.debug(
                f"[{self.config.get('name')}] No change needed for {self.climate_entity_id} (hvac_mode={current_hvac_mode}, fan_mode={current_fan_mode}, temperature={current_temp})"
            )

    async def _load_persisted_data(self) -> None:
        data = await self._store.async_load()
        if data:
            self._last_valid_params = data.get("last_sensor_data")
            self._system_turned_off = data.get("system_turned_off", False)

            # Restore manual override state
            self._manual_override = data.get("manual_override", False)
            expiry_str = data.get("override_expiry")
            if expiry_str:
                self._override_expiry = dt_util.parse_datetime(expiry_str)
            else:
                self._override_expiry = None
            
    async def _save_persisted_data(self, data: dict[str, Any]) -> None:
        data_to_save = {
            "last_sensor_data": data,
            "last_updated": dt_util.now().isoformat(),
            "system_turned_off": getattr(self, "_system_turned_off", False),
            "manual_override": getattr(self, "_manual_override", False),
            "override_expiry": self._override_expiry.isoformat() if self._override_expiry else None,
        }
        await self._store.async_save(data_to_save)


    def _setup_listeners(self) -> None:
        entities = [self.climate_entity_id, self.indoor_temp_sensor_id, self.outdoor_temp_sensor_id]
        if self.indoor_humidity_sensor_id:
            entities.append(self.indoor_humidity_sensor_id)
        if self.outdoor_humidity_sensor_id:
            entities.append(self.outdoor_humidity_sensor_id)
        if self.occupancy_sensor_id:
            entities.append(self.occupancy_sensor_id)
        async_track_state_change_event(self.hass, entities, self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        self.async_set_updated_data(self.data or {})
        self.hass.async_create_task(self.async_request_refresh())
        state = self.hass.states.get(self.climate_entity_id)
        if state and state.state != HVACMode.OFF:
            self._system_turned_off = False

        # User override detection
        if self.config.get("user_override_enable", True):
            if event.data.get("entity_id") == self.climate_entity_id and event.data.get("old_state") and event.data.get("new_state"):
                attrs_old = event.data["old_state"].attributes
                attrs_new = event.data["new_state"].attributes
                # Only activate override if the new state is not OFF
                if event.data["new_state"].state != HVACMode.OFF:
                    temp_changed = attrs_old.get("temperature") != attrs_new.get("temperature")
                    fan_changed = attrs_old.get("fan_mode") != attrs_new.get("fan_mode")
                    mode_changed = event.data["old_state"].state != event.data["new_state"].state
                    if temp_changed or fan_changed or mode_changed:
                        minutes = self.config.get("user_override_minutes", 30)
                        self._manual_override = True
                        self._override_expiry = dt_util.now() + timedelta(minutes=minutes)
                        _LOGGER.info(f"[{self.config.get('name')}] Manual override activated for {minutes} minutes.")