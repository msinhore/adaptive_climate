"""Adaptive Climate Coordinator."""

from __future__ import annotations

import logging
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

        self._outdoor_temp_history: list[tuple[datetime, float]] = []
        self._running_mean_outdoor_temp: Optional[float] = None

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

        self._setup_listeners()
        self.hass.async_create_task(self._load_persisted_data())

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest data and determine actions."""
        indoor_temp = self._get_value(self.indoor_temp_sensor_id)
        outdoor_temp = self._get_value(self.outdoor_temp_sensor_id)
        indoor_humidity = self._get_value(self.indoor_humidity_sensor_id)
        outdoor_humidity = self._get_value(self.outdoor_humidity_sensor_id)

        if indoor_temp is None or outdoor_temp is None:
            return self._last_valid_params or self._default_params("entities_unavailable")

        self._update_outdoor_temp_history(outdoor_temp)
        self._update_occupancy()
        self._check_override_expiry()

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
        )

        control_actions = self._determine_actions(indoor_temp, comfort_params)
        if not self._manual_override:
            await self._execute_actions(control_actions)

        params = self._build_params(indoor_temp, outdoor_temp, indoor_humidity, outdoor_humidity, comfort_params, control_actions)
        self._last_valid_params = params.copy()
        await self._save_persisted_data(params)

        return params

    # Helpers

    def _get_value(self, entity_id: Optional[str]) -> Optional[float]:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                return float(state.state)
            except (ValueError, TypeError):
                return None
        return None

    def _build_params(self, indoor, outdoor, indoor_hum, outdoor_hum, comfort, actions) -> dict[str, Any]:
        return {
            **comfort,
            "indoor_temperature": indoor,
            "outdoor_temperature": outdoor,
            "indoor_humidity": indoor_hum,
            "outdoor_humidity": outdoor_hum,
            "running_mean_outdoor_temp": self._running_mean_outdoor_temp,
            "occupancy": "occupied" if self._occupied else "unoccupied",
            "manual_override": self._manual_override,
            "control_actions": actions,
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
        state = self.hass.states.get(self.occupancy_sensor_id)
        if state and state.state in (STATE_ON, STATE_OFF):
            self._occupied = state.state == STATE_ON

    def _check_override_expiry(self) -> None:
        if self._manual_override and self._override_expiry and dt_util.now() >= self._override_expiry:
            self._manual_override = False
            self._override_expiry = None

    def _determine_actions(self, indoor_temp: float, comfort: dict[str, Any]) -> dict[str, Any]:
        """Determine control actions based on comfort calculation and supported HVAC modes."""

        target_temp = comfort.get("comfort_temp", indoor_temp)
        hvac_mode = comfort.get("hvac_mode", "off")

        # Get supported HVAC modes of the device
        state = self.hass.states.get(self.climate_entity_id)
        supported_modes = []
        if state:
            supported_modes = state.attributes.get("hvac_modes", [])

        # Fallback if calculated hvac_mode is not supported
        if hvac_mode not in supported_modes:
            _LOGGER.warning(f"hvac_mode '{hvac_mode}' not supported by {self.climate_entity_id}. Falling back.")
            if HVACMode.FAN_ONLY in supported_modes:
                hvac_mode = HVACMode.FAN_ONLY
            else:
                hvac_mode = HVACMode.OFF

        actions = {
            "set_temperature": target_temp,
            "set_hvac_mode": hvac_mode,
            "reason": f"Calculated {hvac_mode} based on comfort, adjusted for supported modes.",
        }

        return actions

    async def _execute_actions(self, actions: dict[str, Any]) -> None:
        """Execute the determined HVAC and temperature actions."""
        if actions["set_temperature"] is not None:
            _LOGGER.debug(f"Setting temperature to {actions['set_temperature']} on {self.climate_entity_id}")
            await self.hass.services.async_call(
                CLIMATE_DOMAIN, "set_temperature",
                {"entity_id": self.climate_entity_id, ATTR_TEMPERATURE: actions["set_temperature"]},
            )
        if actions["set_hvac_mode"] is not None:
            _LOGGER.debug(f"Setting hvac_mode to {actions['set_hvac_mode']} on {self.climate_entity_id}")
            await self.hass.services.async_call(
                CLIMATE_DOMAIN, "set_hvac_mode",
                {"entity_id": self.climate_entity_id, "hvac_mode": actions["set_hvac_mode"]},
            )

    # Persistence

    async def _load_persisted_data(self) -> None:
        data = await self._store.async_load()
        if data:
            self._last_valid_params = data.get("last_sensor_data")

    async def _save_persisted_data(self, data: dict[str, Any]) -> None:
        await self._store.async_save({"last_sensor_data": data})

    # Event listeners

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