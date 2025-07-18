"""
Adaptive Climate Coordinator: Home Assistant DataUpdateCoordinator for adaptive climate control.
"""

# --- Imports ---
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util, slugify
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.storage import Store
from homeassistant.components.climate.const import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate import HVACMode
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.components import recorder
from homeassistant.const import (STATE_UNKNOWN, STATE_UNAVAILABLE)

from .const import DOMAIN, UPDATE_INTERVAL_MEDIUM
from .calculator import calculate_hvac_and_fan
from .mode_mapper import map_fan_mode, map_hvac_mode
from .season_detector import get_season

# --- Constants ---
_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1
STORAGE_KEY = "adaptive_climate_data"

# --- Main Class ---
class AdaptiveClimateCoordinator(DataUpdateCoordinator):
    """Coordinator for adaptive climate control."""

    def __init__(self, hass: HomeAssistant, 
                 config_entry_data: dict[str, Any], 
                 config_entry_options: dict[str, Any] = None
                 ) -> None:
        """
        Initialize the coordinator and set up listeners.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MEDIUM),
        )
        self.config: dict[str, Any] = dict(config_entry_data)
        if config_entry_options:
            self.config.update(config_entry_options)
        slug = slugify(self.config.get("name", "Adaptive Climate"))
        self.primary_entity_id: str = f"binary_sensor.{slug}_ashrae_compliance"

        # Internal state
        self._outdoor_temp_history: list[tuple[datetime, float]] = []
        self._indoor_temp_history: list[tuple[datetime, float]] = []
        self._running_mean_outdoor_temp: Optional[float] = None
        self._running_mean_indoor_temp: Optional[float] = None
        self._store: Store = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}_{self.config.get('name', 'default')}"
        )
        self._last_valid_params: Optional[dict[str, Any]] = None

        # Monitored entities
        self.climate_entity_id: str = self.config["climate_entity"]
        self.indoor_temp_sensor_id: str = self.config["indoor_temp_sensor"]
        self.outdoor_temp_sensor_id: str = self.config["outdoor_temp_sensor"]
        self.indoor_humidity_sensor_id: Optional[str] = self.config.get("indoor_humidity_sensor")
        self.outdoor_humidity_sensor_id: Optional[str] = self.config.get("outdoor_humidity_sensor")

        # Sensor fallbacks
        self._last_valid_indoor_temp: Optional[float] = None
        self._last_valid_outdoor_temp: Optional[float] = None
        self._last_valid_indoor_humidity: Optional[float] = None
        self._last_valid_outdoor_humidity: Optional[float] = None

        # Aggressive Cooling / Heating
        self._last_system_command = {}
        self._last_command_timestamp: Optional[datetime] = None

        self._setup_listeners()
        self.hass.async_create_task(self._load_persisted_data())

    async def _async_update_data(self) -> dict[str, Any]:
        """
        Update data and execute control actions.
        """
        if not self.hass.is_running:
            return self._last_valid_params or self._default_params("ha_starting")
        state = self.hass.states.get(self.climate_entity_id)
        if not state or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return self._last_valid_params or self._default_params("entity_disabled")

        auto_mode_enable = self.config.get("auto_mode_enable", True)

        if not auto_mode_enable:
            self.log_event(f"Auto mode disabled. No actions will be taken.")
            return self._last_valid_params or self._default_params("manual_mode")

        # Comfort calculation and control
        indoor_temp = self._get_value(self.indoor_temp_sensor_id, "indoor_temp")
        outdoor_temp = self._get_value(self.outdoor_temp_sensor_id, "outdoor_temp")
        indoor_humidity = self._get_value(self.indoor_humidity_sensor_id, "indoor_humidity")
        outdoor_humidity = self._get_value(self.outdoor_humidity_sensor_id, "outdoor_humidity")
        current_fan_mode = state.attributes.get("fan_mode") if state else None

        if indoor_temp is None or outdoor_temp is None:
            _LOGGER.warning(f"[{self.config.get('name')}] Indoor or outdoor ",
                            f"temperature unavailable. Skipping update.")
            return self._last_valid_params or self._default_params("entities_unavailable")

        season = get_season(self.hass.config.latitude)

        comfort_params = calculate_hvac_and_fan(
            indoor_temp=indoor_temp,
            outdoor_temp=outdoor_temp,
            min_temp=self.config.get("min_comfort_temp", 21),
            max_temp=self.config.get("max_comfort_temp", 27),
            season=season,
            category=self.config.get("comfort_category", "I"),
            air_velocity=current_fan_mode or "low",
            indoor_humidity=indoor_humidity,
            outdoor_humidity=outdoor_humidity,
            running_mean_outdoor_temp=self._running_mean_outdoor_temp,
            running_mean_indoor_temp=self._running_mean_indoor_temp,
            energy_save_mode=self.config.get("energy_save_mode", True),
            device_name=self.config.get("name", "Adaptive Climate"),
            override_temperature=self.config.get("override_temperature", 0),
            aggressive_cooling_threshold=self.config.get("aggressive_cooling_threshold", 2.0),
            aggressive_heating_threshold=self.config.get("aggressive_heating_threshold", 2.0),
        )
        _LOGGER.debug(
            f"[{self.config.get('name')}] Comfort parameters: "
            f"season={comfort_params.get('season')}, "
            f"category={comfort_params.get('category')}, "
            f"comfort_temp={comfort_params.get('comfort_temp')}, "
            f"hvac_mode={comfort_params.get('hvac_mode')}, "
            f"fan_mode={comfort_params.get('fan_mode')}, "
            f"ashrae_compliant={comfort_params.get('ashrae_compliant')}, "
            f"comfort_min_ashrae={comfort_params.get('comfort_min_ashrae')}, "
            f"comfort_max_ashrae={comfort_params.get('comfort_max_ashrae')}, "
            f"indoor_humidity={indoor_humidity}, "
            f"outdoor_humidity={outdoor_humidity}, "
            f"indoor_temp={indoor_temp}, "
            f"outdoor_temp={outdoor_temp}, "
            f"running_mean_indoor_temp={self._running_mean_indoor_temp}, "
            f"running_mean_outdoor_temp={self._running_mean_outdoor_temp}, "
            f"energy_save_mode={self.config.get('energy_save_mode')}"
        )

        # Determine control actions based on comfort parameters
        control_actions = self._determine_actions(indoor_temp, comfort_params)

        ac_hvac_mode = str(state.state)
        ac_fan_mode = str(state.attributes.get("fan_mode"))
        ac_temperature = round(float(state.attributes.get("temperature")), 2) if state.attributes.get("temperature") else None

        ac_state_dict = {
            "hvac_mode": ac_hvac_mode,
            "fan_mode": ac_fan_mode,
            "temperature": ac_temperature
        }

        desired_state_dict = {
            "hvac_mode": control_actions.get("set_hvac_mode"),
            "fan_mode": control_actions.get("set_fan_mode"),
            "temperature": control_actions.get("set_temperature")
        }

        decision = self._evaluate_control_decision(ac_state_dict, desired_state_dict)
        
        if decision == "manual_override":
            self.config["auto_mode_enable"] = False
            self.log_event(f"Manual control detected, auto mode disabled.")
            return self._last_valid_params or self._default_params("manual_override")

        if decision == "no_action_needed":
            _LOGGER.debug(f"[{self.config.get('name')}] AC already in desired state, no action needed.")
            return self._last_valid_params or self._default_params("no_action_needed")

        if decision == "waiting_for_state_change":
            _LOGGER.debug(f"[{self.config.get('name')}] Waiting for AC to reach desired state.")
            return self._last_valid_params or self._default_params("waiting_for_state_change")

        await self._execute_actions(control_actions)

        params = self._build_params(
            indoor_temp, outdoor_temp, indoor_humidity, outdoor_humidity, comfort_params, control_actions
        )
        self._last_valid_params = params.copy()
        await self._save_persisted_data(params)
        _LOGGER.debug(f"[{self.config.get('name')}] Control decision: {decision}. "
                      f"AC state: {ac_state_dict}, Desired: {desired_state_dict}, "
                      f"Last command: {self._last_system_command}")
        return params

    # --- Log event ---
    def log_event(self, message: str) -> None:
        """Log message to Home Assistant logbook and system logger."""
        formatted_message = f"[{self.config.get('name')}] {message}"
        self.hass.async_create_task(
            self.hass.services.async_call(
                "logbook", "log", {
                    "name": self.config.get("name"),
                    "message": message,
                    "entity_id": self.primary_entity_id,
                }
            )
        )
        _LOGGER.info(formatted_message)

    def _evaluate_control_decision(self, ac_state: dict, desired_state: dict) -> str:
        """
        Decides whether action is required, pending, or manual override detected.
        Returns one of:
        - 'manual_override'
        - 'no_action_needed'
        - 'waiting_for_state_change'
        - 'action_required'
        """
        if self._check_manual_override(self.hass.states.get(self.climate_entity_id)):
            return "manual_override"

        if ac_state == desired_state:
            return "no_action_needed"

        if desired_state == self._last_system_command:
            return "waiting_for_state_change"

        return "action_required"

    def _update_last_system_command(self, state: dict) -> None:
        """Updates the last command issued by the system."""
        self._last_system_command = {
            "hvac_mode": str(state.get("set_hvac_mode")),
            "fan_mode": str(state.get("set_fan_mode")),
            "temperature": round(float(state.get("set_temperature")), 2),
        }
        self._last_command_timestamp = dt_util.utcnow()

    def _check_manual_override(self, state) -> bool:
        """Check if the climate entity has been manually overridden."""
        ac_hvac_mode = str(state.state)
        ac_fan_mode = str(state.attributes.get("fan_mode"))
        ac_temperature = round(float(state.attributes.get("temperature")), 2) if state.attributes.get("temperature") else None

        last_command = self._last_system_command

        if self._last_command_timestamp and (dt_util.utcnow() - self._last_command_timestamp).total_seconds() < 15:
            return False

        last_hvac_mode = last_command.get("hvac_mode")
        last_fan_mode = last_command.get("fan_mode")
        last_temperature = last_command.get("temperature")

        def _values_different(a, b, tolerance=0.1):
            """Compare floats with tolerance."""
            if a is None or b is None:
                return False
            return abs(float(a) - float(b)) > tolerance

        # Check if the current state differs from the last command
        if (
            last_hvac_mode is not None and
            (
                ac_hvac_mode != last_hvac_mode or
                ac_fan_mode != last_fan_mode or
                _values_different(ac_temperature, last_temperature)
            )
        ):
            return True
        return False

    # --- Dynamic Configuration ---
    async def async_update_config_value(self, key: str, value: Any) -> None:
        """Update a single config value, persist parameters, and refresh."""
        self.config[key] = value
        await self._save_persisted_parameters_only()

        if key == "auto_mode_enable" and value is True:
            self._last_system_command = {}
            self._last_command_timestamp = None
            self.log_event("Auto mode re-enabled. System reset to resume automatic control.")

        await self.async_request_refresh()

        _LOGGER.debug(
            f"[{self.config.get('name')}] Config key '{key}' updated and persisted: {value}, "
            f"Primary entity: {self.primary_entity_id}"
        )

    async def _save_persisted_parameters_only(self) -> None:
        """Persist only configuration parameters."""
        data = await self._store.async_load() or {}
        data["config_parameters"] = {
            "min_comfort_temp": self.config.get("min_comfort_temp"),
            "max_comfort_temp": self.config.get("max_comfort_temp"),
            "temperature_change_threshold": self.config.get("temperature_change_threshold"),
            "override_temperature": self.config.get("override_temperature"),
            "aggressive_cooling_threshold": self.config.get("aggressive_cooling_threshold"),
            "aggressive_heating_threshold": self.config.get("aggressive_heating_threshold"),
        }
        await self._store.async_save(data)

    async def update_config(self, new_config: dict[str, Any]) -> None:
        """Update the coordinator configuration with new values."""
        self.config.update(new_config)
        _LOGGER.debug(f"[{self.config.get('name')}] Coordinator configuration updated: {new_config}")
        await self.async_request_refresh()

    # --- Outdoor Temperature History ---
    async def _load_outdoor_temp_history(self, days: int = 7):
        """Load outdoor temperature history from the recorder."""
        start_time = dt_util.now() - timedelta(days=days)
        entity_id = self.outdoor_temp_sensor_id
        states = await recorder.get_instance(self.hass).async_add_executor_job(
            get_significant_states, self.hass, start_time, dt_util.now(), [entity_id]
        )
        outdoor_history = []
        for state in states.get(entity_id, []):
            try:
                temp = float(state.state)
                outdoor_history.append((state.last_updated, temp))
            except Exception:
                continue
        self._outdoor_temp_history = outdoor_history
        self._running_mean_outdoor_temp = self._calculate_exponential_running_mean(self._outdoor_temp_history)

    # --- Indoor Temperature History ---
    async def _load_indoor_temp_history(self, days: int = 7):
        """Load indoor temperature history from the recorder."""
        start_time = dt_util.now() - timedelta(days=days)
        entity_id = self.indoor_temp_sensor_id
        states = await recorder.get_instance(self.hass).async_add_executor_job(
            get_significant_states, self.hass, start_time, dt_util.now(), [entity_id]
        )
        
        indoor_history = []
        for state in states.get(entity_id, []):
            try:
                temp = float(state.state)
                indoor_history.append((state.last_updated, temp))
            except Exception:
                continue
        self._indoor_temp_history = indoor_history
        self._running_mean_indoor_temp = self._calculate_exponential_running_mean(self._indoor_temp_history)

    # --- Time Since State ---
    async def get_time_since_state(self, entity_id: str, target_state: str) -> float:
        """Get the time in minutes since the entity was last in a specific state."""
        now = dt_util.now()
        states = await recorder.get_instance(self.hass).async_add_executor_job(
            get_significant_states, self.hass, now - timedelta(hours=24), now, [entity_id]
        )
        history = states.get(entity_id, [])
        for state in reversed(history):
            if state.state != target_state:
                last_change = state.last_changed
                return (now - last_change).total_seconds() / 60
        return 24 * 60

    # --- Action Execution ---
    async def _execute_actions(self, actions: dict[str, Any]) -> None:
        """Execute climate actions with minimal repeated logic."""
        state = self.hass.states.get(self.climate_entity_id)
        if not state or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            _LOGGER.warning(
                f"[{self.config.get('name')}] {self.climate_entity_id} "
                f" unavailable, skipping action execution."
                )
            return

        current_temperature = state.attributes.get('temperature')
        current_hvac_mode = state.state
        current_fan_mode = state.attributes.get('fan_mode')

        target_temperature = actions.get("set_temperature")
        target_fan_mode = actions.get("set_fan_mode")
        target_hvac_mode = actions.get("set_hvac_mode")

        threshold = self.config.get("temperature_change_threshold", 0.5)
        supported_fan_modes = state.attributes.get("fan_modes", [])
        supported_hvac_modes = state.attributes.get("hvac_modes", [])
        auto_mode_enable = self.config.get("auto_mode_enable", True)

        temperature_changed = False
        fan_changed = False
        hvac_changed = False

        if not auto_mode_enable:
            self.log_event(f"Auto mode disabled. No actions will be taken.")
            return

        if current_hvac_mode == HVACMode.OFF:
            self.log_event(f"HVAC is OFF, skipping further actions.")
            return

        def needs_update(current, target, threshold):
            return target is not None and (current is None or abs(target - current) >= threshold)

        _LOGGER.debug(f"[{self.config.get('name')}] Climate attributes before execution: "
                      f"temperature={current_temperature}, "
                      f"fan_mode={current_fan_mode}, "
                      f"hvac_mode={current_hvac_mode} "
                      )

        # Temperature
        if (needs_update(current_temperature, target_temperature, threshold)
            and (current_hvac_mode != "fan_only")
        ):
            await self._call_service(CLIMATE_DOMAIN, "set_temperature", {
                "entity_id": self.climate_entity_id,
                "temperature": target_temperature,
            })
            temperature_changed = True

        # Fan mode
        if target_fan_mode != current_fan_mode:
            if target_fan_mode in supported_fan_modes:
                await self._call_service(CLIMATE_DOMAIN, "set_fan_mode", {
                    "entity_id": self.climate_entity_id,
                    "fan_mode": target_fan_mode,
                })
                fan_changed = True

        # HVAC mode
        if target_hvac_mode != current_hvac_mode:
            if target_hvac_mode in supported_hvac_modes:
                await self._call_service(CLIMATE_DOMAIN, "set_hvac_mode", {
                    "entity_id": self.climate_entity_id,
                    "hvac_mode": target_hvac_mode,
                })
                hvac_changed = True

        if temperature_changed or fan_changed or hvac_changed:
            self._update_last_system_command(actions)
            self.log_event(f"Set temperature to {target_temperature}, "
                           f"fan_mode={target_fan_mode}, "
                           f"hvac_mode={target_hvac_mode}"
                           f" on {self.climate_entity_id}")
        else:
            self.log_event(f"No changes needed for climate entity {self.climate_entity_id}.")

    async def _call_service(self, domain, service, data):
        """Helper to call Home Assistant service with delay."""
        _LOGGER.debug(f"Calling service {domain}.{service} with data: {data}")
        await self.hass.services.async_call(domain, service, data)

    # --- Persistence ---
    async def _load_persisted_data(self) -> None:
        """Load persisted data from storage."""
        data = await self._store.async_load()
        if data:
            self._last_valid_params = data.get("last_sensor_data")
            self._system_turned_off = data.get("system_turned_off", False)
            self._last_system_command = data.get("last_system_command", {})
            timestamp = data.get("last_command_timestamp")
            self._last_command_timestamp = dt_util.parse_datetime(timestamp) if timestamp else None

        await self._save_persisted_parameters_only()
        await self._load_outdoor_temp_history()
        await self._load_indoor_temp_history()

    async def _save_persisted_data(self, data: dict[str, Any]) -> None:
        """Save the current state to persistent storage."""
        data_to_save = {
            "last_system_command": self._last_system_command,
            "last_command_timestamp": self._last_command_timestamp.isoformat() if self._last_command_timestamp else None,
            "last_sensor_data": data,
            "config_parameters": {
                "min_comfort_temp": self.config.get("min_comfort_temp"),
                "max_comfort_temp": self.config.get("max_comfort_temp"),
                "temperature_change_threshold": self.config.get("temperature_change_threshold"),
                "override_temperature": self.config.get("override_temperature"),
                "aggressive_cooling_threshold": self.config.get("aggressive_cooling_threshold"),
                "aggressive_heating_threshold": self.config.get("aggressive_heating_threshold"),
            },
            "last_updated": dt_util.now().isoformat(),
        }
        await self._store.async_save(data_to_save)

    # --- Helpers ---
    def _get_value(self, entity_id: Optional[str], sensor_type: Optional[str] = None) -> Optional[float]:
        """Get the value of a sensor entity, with fallback to last valid reading."""
        if not entity_id:
            _LOGGER.warning(f"[{self.config.get('name')}] Sensor entity ID is missing ({sensor_type}).")
            return None

        state = self.hass.states.get(entity_id)
        if state is None:
            _LOGGER.error(f"[{self.config.get('name')}] Sensor '{entity_id}' not found in Home Assistant.")
            return None

        if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            _LOGGER.warning(f"[{self.config.get('name')}] Sensor '{entity_id}' is unavailable. Using last known value.")
            last_valid_map = {
                "indoor_temp": self._last_valid_indoor_temp,
                "outdoor_temp": self._last_valid_outdoor_temp,
                "indoor_humidity": self._last_valid_indoor_humidity,
                "outdoor_humidity": self._last_valid_outdoor_humidity
            }
            return last_valid_map.get(sensor_type)

        try:
            value = float(state.state)
            last_valid_attr_map = {
                "indoor_temp": "_last_valid_indoor_temp",
                "outdoor_temp": "_last_valid_outdoor_temp",
                "indoor_humidity": "_last_valid_indoor_humidity",
                "outdoor_humidity": "_last_valid_outdoor_humidity"
            }
            if sensor_type in last_valid_attr_map:
                setattr(self, last_valid_attr_map[sensor_type], value)
            return value
        except (ValueError, TypeError):
            _LOGGER.warning(f"[{self.config.get('name')}] Failed to convert state '{state.state}' "
                            f"of {entity_id} to float.")
            return None

    def _build_params(self, indoor, outdoor, indoor_hum, outdoor_hum, comfort, actions) -> dict[str, Any]:
        """Build the parameters dictionary for the coordinator."""
        return {
            "adaptive_comfort_temp": comfort.get("comfort_temp"),
            "comfort_temp_min": comfort.get("comfort_min_ashrae"),
            "comfort_temp_max": comfort.get("comfort_max_ashrae"),
            "indoor_temperature": indoor,
            "outdoor_temperature": outdoor,
            "indoor_humidity": indoor_hum if self.indoor_humidity_sensor_id else None,
            "outdoor_humidity": outdoor_hum if self.outdoor_humidity_sensor_id else None,
            "running_mean_outdoor_temp": self._running_mean_outdoor_temp,
            "running_mean_indoor_temp": self._running_mean_indoor_temp,
            "control_actions": actions,
            "ashrae_compliant": comfort.get("ashrae_compliant"),
            "last_updated": dt_util.now(),
        }

    def _default_params(self, status: str) -> dict[str, Any]:
        """Return default parameters when no valid data is available."""
        return {
            "adaptive_comfort_temp": 22.0,
            "comfort_temp_min": 20.0,
            "comfort_temp_max": 24.0,
            "status": status,
        }

    def _update_outdoor_temp_history(self, outdoor_temp: float) -> None:
        """Update the outdoor temperature history with the latest reading."""
        now = dt_util.now()
        self._outdoor_temp_history.append((now, outdoor_temp))
        self._outdoor_temp_history = [
            (ts, temp) for ts, temp in self._outdoor_temp_history if ts > now - timedelta(days=7)
        ]
        self._running_mean_outdoor_temp = self._calculate_exponential_running_mean(self._outdoor_temp_history)

    def _update_indoor_temp_history(self, indoor_temp: float) -> None:
        """Update the indoor temperature history with the latest reading."""
        now = dt_util.now()
        self._indoor_temp_history.append((now, indoor_temp))
        self._indoor_temp_history = [
            (ts, temp) for ts, temp in self._indoor_temp_history if ts > now - timedelta(days=7)
        ]
        self._running_mean_indoor_temp = self._calculate_exponential_running_mean(self._indoor_temp_history)

    def _calculate_exponential_running_mean(self, history: list[tuple[datetime, float]], 
                                            alpha: float = 0.8) -> Optional[float]:
        """Calcula a média móvel exponencial para o histórico fornecido."""
        temps = sorted(history, key=lambda x: x[0])
        running_mean = None
        for _, temp in temps:
            if running_mean is None:
                running_mean = temp
            else:
                running_mean = (1 - alpha) * temp + alpha * running_mean
        return running_mean

    def _determine_actions(self, indoor_temp: float, comfort: dict[str, Any]) -> dict[str, Any]:
        """Determine control actions based on comfort calculation and supported HVAC modes."""
        target_temp = comfort.get("comfort_temp")
        hvac_mode = comfort.get("hvac_mode")
        fan_mode = comfort.get("fan_mode")

        if hvac_mode == "fan_only" and fan_mode in ["highest", "max"]:
            fan_mode = "high"

        _LOGGER.debug(f"[{self.config.get('name')}] Initial determine_actions: "
                      f"target_temp={target_temp}, hvac_mode={hvac_mode}, fan_mode={fan_mode}"
                      )

        state = self.hass.states.get(self.climate_entity_id)
        supported_hvac_modes = []
        supported_fan_modes = []
        if state:
            supported_hvac_modes = [str(mode) for mode in state.attributes.get("hvac_modes", [])]
            supported_fan_modes = [str(mode) for mode in state.attributes.get("fan_modes", [])]

        hvac_mode = map_hvac_mode(
            str(hvac_mode),
            supported_hvac_modes) if supported_hvac_modes else hvac_mode
        
        fan_mode = map_fan_mode(str(fan_mode), supported_fan_modes) if supported_fan_modes else fan_mode
        
        # If fan_mode is "highest" and not supported, swap for "high" if supported
        if fan_mode == "highest" and "highest" not in supported_fan_modes and "high" in supported_fan_modes:
            fan_mode = "high"
 
        return {
            "set_temperature": target_temp,
            "set_hvac_mode": hvac_mode,
            "set_fan_mode": fan_mode,
            "reason": f"Calculated hvac mode: {hvac_mode}, temperature: {target_temp}, fan mode: {fan_mode}.",
            }

    # --- Listeners ---
    def _setup_listeners(self) -> None:
        """Register state change listener for climate entity only."""
        entities = [self.climate_entity_id]
        async_track_state_change_event(self.hass, entities, self._handle_state_change)

    @callback
    def _handle_state_change(self, event) -> None:
        """
        Handle state changes of monitored entities.
        Only disables auto mode if manual control is detected and auto mode is currently enabled.
        """
        # Check if the event is for the monitored climate entity
        entity_id = event.data.get("entity_id")
        if entity_id != self.climate_entity_id:
            _LOGGER.debug(f"[{self.config.get('name')}] Ignored state change for {entity_id}")
            return
        
        # Continue with normal update/refresh
        self.hass.async_create_task(self.async_request_refresh())