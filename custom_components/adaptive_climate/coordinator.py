# --- Future Imports ---
from __future__ import annotations

import asyncio

# --- Standard Library ---
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# --- Home Assistant Imports ---
from homeassistant.components import recorder
from homeassistant.components.climate.const import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Context, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

# --- Custom Component Imports ---
from custom_components.adaptive_climate.utils.calculator import ComfortCalculator
from custom_components.adaptive_climate.const import (
    DOMAIN,
    UPDATE_INTERVAL_LONG,
    UPDATE_INTERVAL_MEDIUM,
    UPDATE_INTERVAL_SHORT,
)
from custom_components.adaptive_climate.utils import (
    get_season,
    create_command_context,
    is_system_event_context,
    has_meaningful_user_change,
    collect_area_fans,
)

# --- Constants ---
_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1
STORAGE_KEY = "adaptive_climate_data"
GLOBAL_CLIMATE_ENTITIES: set[str] = set()


class AdaptiveClimateCoordinator(DataUpdateCoordinator):
    """Coordinator for adaptive climate control with simplified structure."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_data: Dict[str, Any],
        config_entry_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the coordinator with simplified setup."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=UPDATE_INTERVAL_SHORT
            ),  # Start with shorter interval for faster response
        )

        # Setup configuration
        self._setup_config(config_entry_data, config_entry_options)
        self._setup_entities()
        self._setup_storage()
        self._setup_listeners()

        _LOGGER.debug(
            f"[{self.device_name}] Coordinator initialized successfully"
        )

        # Cache for area orchestration decisions (simple dwell)
        self._last_role_decision_ts: Optional[datetime] = None
        self._last_role_primary: Optional[bool] = None
        self._role_dwell_minutes: int = 15
        # Sensor warning flag to avoid noisy logs on startup
        self._sensor_warning_logged: bool = False

    @property
    def device_name(self) -> str:
        """Get device name for logging."""
        return self.config.get("name", "Adaptive Climate")

    def _setup_config(
        self,
        config_entry_data: Dict[str, Any],
        config_entry_options: Optional[Dict[str, Any]],
    ) -> None:
        """Setup configuration and primary entity ID."""
        self.config: Dict[str, Any] = dict(config_entry_data)
        if config_entry_options:
            self.config.update(config_entry_options)

        entity = self.config.get("entity")
        if entity and "." in entity:
            name_slug = slugify(entity.split(".")[-1]).replace("-", "_")
        else:
            name_slug = slugify(self.device_name).replace("-", "_")
        self.primary_entity_id = (
            f"{entity}_ashrae_compliance"
            if entity
            else f"binary_sensor.{name_slug}_ashrae_compliance"
        )

        _LOGGER.debug(
            f"[{self.device_name}] Configuration setup completed - Primary entity: {self.primary_entity_id}"
        )

    def _setup_entities(self) -> None:
        """Setup and validate monitored entities."""
        self.climate_entity_id = self.config.get("entity") or self.config.get(
            "climate_entity"
        )
        if not self.climate_entity_id:
            raise ValueError(
                f"[{self.device_name}] Missing required "
                "'entity' or 'climate_entity' definition."
            )

        # Allow reusing the same climate in multiple entries when using area-based fan-out.
        # We only guard against duplicate coordinators within the same HA process by
        # removing stale references and then registering current one.
        try:
            GLOBAL_CLIMATE_ENTITIES.discard(self.climate_entity_id)
        except Exception:
            pass
        GLOBAL_CLIMATE_ENTITIES.add(self.climate_entity_id)

        # Setup sensor entities
        self.indoor_temp_sensor_id = self.config.get("indoor_temp_sensor")
        self.outdoor_temp_sensor_id = self.config.get("outdoor_temp_sensor")
        self.indoor_humidity_sensor_id = self.config.get(
            "indoor_humidity_sensor"
        )
        self.outdoor_humidity_sensor_id = self.config.get(
            "outdoor_humidity_sensor"
        )

        # Setup state tracking
        self._last_valid_indoor_temp: Optional[float] = None
        self._last_valid_outdoor_temp: Optional[float] = None
        self._last_valid_indoor_humidity: Optional[float] = None
        self._last_valid_outdoor_humidity: Optional[float] = None
        self._last_system_command: Dict[str, Any] = {}
        self._last_command_timestamp: Optional[datetime] = None
        self._outdoor_temp_history: List[Tuple[datetime, float]] = []
        self._running_mean_temp: Optional[float] = None
        self._last_valid_params: Optional[Dict[str, Any]] = None
        self._startup_completed: bool = (
            False  # Flag to track startup completion
        )

        # Track important events for logbook (only log once)
        self._override_logged: bool = False
        self._auto_mode_logged: bool = False

        # NEW: Track user power-off and manual pause states
        self._user_power_off_detected: bool = False
        self._manual_pause_until: Optional[datetime] = None
        self._last_manual_context_id: Optional[str] = (
            None  # Track last manual context to avoid duplicates
        )

        # Use normalized device name as system identifier (simple and persistent)
        normalized_name = self._normalize_device_name(self.device_name)
        self._system_id = f"adaptive_climate_{normalized_name}"
        _LOGGER.debug(
            f"[{self.device_name}] Using normalized device name as system ID: {self._system_id}"
        )

        # Setup calculator
        self._calculator = ComfortCalculator()

        _LOGGER.debug(f"[{self.device_name}] Entities setup completed:")
        _LOGGER.debug(
            f"[{self.device_name}]   - Climate entity: {self.climate_entity_id}"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Indoor temp sensor: {self.indoor_temp_sensor_id}"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Outdoor temp sensor: {self.outdoor_temp_sensor_id}"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Indoor humidity sensor: {self.indoor_humidity_sensor_id}"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Outdoor humidity sensor: {self.outdoor_humidity_sensor_id}"
        )

    def _detect_device_capabilities(self) -> Dict[str, bool]:
        """Detect device capabilities based on current state."""
        _LOGGER.debug(f"[{self.device_name}] Detecting device capabilities...")

        state = self.hass.states.get(self.climate_entity_id)
        if not state:
            _LOGGER.warning(
                f"[{self.device_name}] Climate entity {self.climate_entity_id} not found"
            )
            return {
                "is_cool": False,
                "is_heat": False,
                "is_fan": False,
                "is_dry": False,
            }

        # Get supported modes
        hvac_modes = state.attributes.get("hvac_modes", [])
        fan_modes = state.attributes.get("fan_modes", [])

        # Check service support
        supports_set_temperature = self._check_service_support(
            CLIMATE_DOMAIN, "set_temperature", self.climate_entity_id
        )
        supports_set_hvac_mode = self._check_service_support(
            CLIMATE_DOMAIN, "set_hvac_mode", self.climate_entity_id
        )
        supports_set_fan_mode = self._check_service_support(
            CLIMATE_DOMAIN, "set_fan_mode", self.climate_entity_id
        )

        # Determine capabilities
        capabilities = {
            "is_cool": "cool" in hvac_modes,
            "is_heat": "heat" in hvac_modes,
            "is_fan": "fan_only" in hvac_modes or len(fan_modes) > 0,
            "is_dry": "dry" in hvac_modes,
            "supports_set_temperature": supports_set_temperature,
            "supports_set_hvac_mode": supports_set_hvac_mode,
            "supports_set_fan_mode": supports_set_fan_mode,
        }

        _LOGGER.info(f"[{self.device_name}] Device capabilities detected:")
        _LOGGER.info(f"[{self.device_name}]   - HVAC modes: {hvac_modes}")
        _LOGGER.info(f"[{self.device_name}]   - Fan modes: {fan_modes}")
        _LOGGER.info(
            f"[{self.device_name}]   - Supports set_temperature: {supports_set_temperature}"
        )
        _LOGGER.info(
            f"[{self.device_name}]   - Supports set_hvac_mode: {supports_set_hvac_mode}"
        )
        _LOGGER.info(
            f"[{self.device_name}]   - Supports set_fan_mode: {supports_set_fan_mode}"
        )

        return capabilities

    def _update_config_with_capabilities(
        self, capabilities: Dict[str, bool]
    ) -> None:
        """Update configuration with detected capabilities."""
        _LOGGER.debug(
            f"[{self.device_name}] Updating configuration with detected capabilities..."
        )

        # Update config with detected capabilities
        self.config["enable_cool_mode"] = capabilities["is_cool"]
        self.config["enable_heat_mode"] = capabilities["is_heat"]
        self.config["enable_fan_mode"] = capabilities["is_fan"]
        self.config["enable_dry_mode"] = capabilities["is_dry"]

        _LOGGER.debug(
            f"[{self.device_name}] Configuration updated with capabilities:"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - enable_cool_mode: {self.config['enable_cool_mode']}"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - enable_heat_mode: {self.config['enable_heat_mode']}"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - enable_fan_mode: {self.config['enable_fan_mode']}"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - enable_dry_mode: {self.config['enable_dry_mode']}"
        )

        # Log device type detection
        if capabilities["is_cool"] and capabilities["is_heat"]:
            device_type = "Heat/Cool (AC)"
        elif capabilities["is_heat"]:
            device_type = "Heat Only (TRV/Heater)"
        elif capabilities["is_cool"]:
            device_type = "Cool Only (AC)"
        elif capabilities["is_fan"]:
            device_type = "Fan Only"
        else:
            device_type = "Unknown"

        _LOGGER.info(
            f"[{self.device_name}] Device type detected: {device_type}"
        )

    async def _setup_device_capabilities(self) -> None:
        """Setup device capabilities detection."""
        _LOGGER.debug(
            f"[{self.device_name}] Setting up device capabilities detection..."
        )

        # Wait a moment for entities to be available
        await asyncio.sleep(2)

        # Detect capabilities
        capabilities = self._detect_device_capabilities()

        # Update configuration with detected capabilities
        self._update_config_with_capabilities(capabilities)

        _LOGGER.debug(
            f"[{self.device_name}] Device capabilities setup completed"
        )

    def _normalize_device_name(self, device_name: str) -> str:
        """Normalize device name for use as system identifier."""
        import unicodedata

        # Remove accents and convert to lowercase
        normalized = unicodedata.normalize("NFD", device_name)
        normalized = "".join(
            c for c in normalized if not unicodedata.combining(c)
        )

        # Replace spaces and special characters with underscores
        normalized = (
            normalized.replace(" ", "_").replace("-", "_").replace(".", "_")
        )

        # Remove any remaining special characters except alphanumeric and underscores
        normalized = "".join(c for c in normalized if c.isalnum() or c == "_")

        # Convert to lowercase
        normalized = normalized.lower()

        # Remove leading/trailing underscores
        normalized = normalized.strip("_")

        return normalized

    def _setup_storage(self) -> None:
        """Setup storage for persisting data."""
        self._store = Store(
            self.hass, STORAGE_VERSION, f"{STORAGE_KEY}_{self.device_name}"
        )
        _LOGGER.debug(f"[{self.device_name}] Storage setup completed")

    def _setup_listeners(self) -> None:
        """Register state change listener and startup tasks."""
        entities = [self.climate_entity_id]
        async_track_state_change_event(
            self.hass, entities, self._handle_state_change
        )

        # Execute startup immediately for faster response
        self.hass.async_create_task(self._startup())
        _LOGGER.debug(
            f"[{self.device_name}] Listeners setup completed - monitoring: {entities}"
        )

    async def _startup(self) -> None:
        """Load persisted data and run initial control cycle if needed."""
        _LOGGER.debug(f"[{self.device_name}] Starting initialization...")

        # Setup device capabilities detection first
        await self._setup_device_capabilities()

        # Load persisted data first
        await self._load_persisted_data()
        await self._persist_data(params_only=True)

        # Load outdoor temperature history
        await self._load_outdoor_temp_history()

        # Check if auto mode is enabled and execute immediately
        if self.config.get("auto_mode_enable", False):
            _LOGGER.debug(
                f"[{self.device_name}] Auto mode enabled - executing immediate control cycle"
            )

            # Execute control cycle immediately
            await self._execute_immediate_control_cycle()
        else:
            _LOGGER.debug(
                f"[{self.device_name}] Auto mode disabled - skipping initial control cycle"
            )

        self._startup_completed = True
        _LOGGER.debug(f"[{self.device_name}] Initialization completed")

        # Adjust update interval to normal after startup
        if self.config.get("auto_mode_enable", False):
            self._adjust_update_interval()

    def _adjust_update_interval(self) -> None:
        """Adjust update interval based on auto mode status."""
        if self.config.get("auto_mode_enable", False):
            # Use medium interval for normal operation
            self.update_interval = timedelta(minutes=UPDATE_INTERVAL_MEDIUM)
            _LOGGER.debug(
                f"[{self.device_name}] Update interval adjusted to {UPDATE_INTERVAL_MEDIUM} minutes for normal operation"
            )
        else:
            # Use longer interval when auto mode is disabled
            self.update_interval = timedelta(minutes=UPDATE_INTERVAL_LONG)
            _LOGGER.debug(
                f"[{self.device_name}] Update interval adjusted to {UPDATE_INTERVAL_LONG} minutes (auto mode disabled)"
            )

    async def _execute_immediate_control_cycle(self) -> None:
        """Execute an immediate control cycle with optimized timing."""
        _LOGGER.debug(
            f"[{self.device_name}] Executing immediate control cycle..."
        )

        try:
            # Wait a short moment for sensors to be available
            await asyncio.sleep(2)

            # Check if climate entity is available
            state = self.hass.states.get(self.climate_entity_id)
            if not state or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                _LOGGER.warning(
                    f"[{self.device_name}] Climate entity not available during startup - will retry on next update"
                )
                return

            # Get sensor data
            sensor_data = self._get_sensor_data(state)
            if not sensor_data:
                _LOGGER.warning(
                    f"[{self.device_name}] Sensor data unavailable during startup - will retry on next update"
                )
                return

            # Calculate comfort parameters
            comfort_params = self._calculate_comfort(sensor_data)
            if not comfort_params:
                _LOGGER.warning(
                    f"[{self.device_name}] Comfort calculation failed during startup - will retry on next update"
                )
                return

            # Determine and execute actions
            actions = self._determine_actions(comfort_params)

            if self._should_execute_actions(actions):
                _LOGGER.debug(
                    f"[{self.device_name}] Startup actions will be executed"
                )
                await self._execute_all_actions(actions)
            else:
                _LOGGER.debug(
                    f"[{self.device_name}] No startup actions needed - system already in desired state"
                )

            _LOGGER.debug(
                f"[{self.device_name}] Immediate control cycle completed successfully"
            )

        except Exception as e:
            _LOGGER.error(
                f"[{self.device_name}] Failed to execute immediate control cycle: {e}"
            )
            # Don't fail startup, just log the error

    async def _load_persisted_data(self) -> None:
        """Load persisted data from storage."""
        try:
            data = await self._store.async_load()
            if data:
                _LOGGER.debug(
                    f"[{self.device_name}] Loading persisted data..."
                )

                # Load last system command
                if (
                    "last_system_command" in data
                    and data["last_system_command"]
                ):
                    self._last_system_command = data["last_system_command"]
                    _LOGGER.debug(
                        f"[{self.device_name}] Loaded last system command: {self._last_system_command}"
                    )

                # Load last command timestamp
                if (
                    "last_command_timestamp" in data
                    and data["last_command_timestamp"]
                ):
                    try:
                        self._last_command_timestamp = dt_util.parse_datetime(
                            data["last_command_timestamp"]
                        )
                        _LOGGER.debug(
                            f"[{self.device_name}] Loaded last command timestamp: {self._last_command_timestamp}"
                        )
                    except Exception as e:
                        _LOGGER.warning(
                            f"[{self.device_name}] Failed to parse last command timestamp: {e}"
                        )

                # Load config parameters
                if "config_parameters" in data and data["config_parameters"]:
                    config_params = data["config_parameters"]
                    for key, value in config_params.items():
                        if key in self.config:
                            self.config[key] = value
                    _LOGGER.debug(
                        f"[{self.device_name}] Loaded config parameters: {config_params}"
                    )

                # NEW: Load user power-off state
                if "user_power_off_detected" in data:
                    self._user_power_off_detected = data[
                        "user_power_off_detected"
                    ]
                    _LOGGER.debug(
                        f"[{self.device_name}] Loaded user power-off state: {self._user_power_off_detected}"
                    )

                # NEW: Load manual pause state
                if "manual_pause_until" in data and data["manual_pause_until"]:
                    try:
                        self._manual_pause_until = dt_util.parse_datetime(
                            data["manual_pause_until"]
                        )
                        _LOGGER.debug(
                            f"[{self.device_name}] Loaded manual pause until: {self._manual_pause_until}"
                        )
                    except Exception as e:
                        _LOGGER.warning(
                            f"[{self.device_name}] Failed to parse manual pause timestamp: {e}"
                        )

                # NEW: Load last manual context ID
                if "last_manual_context_id" in data:
                    self._last_manual_context_id = data[
                        "last_manual_context_id"
                    ]
                    _LOGGER.debug(
                        f"[{self.device_name}] Loaded last manual context ID: {self._last_manual_context_id}"
                    )

                _LOGGER.debug(
                    f"[{self.device_name}] Persisted data loaded successfully"
                )
            else:
                _LOGGER.debug(f"[{self.device_name}] No persisted data found")
        except Exception as e:
            _LOGGER.error(
                f"[{self.device_name}] Failed to load persisted data: {e}"
            )

    def log_event(self, message: str) -> None:
        """Log important message to Home Assistant logbook."""
        formatted_message = f"[{self.device_name}] {message}"
        self.hass.async_create_task(
            self.hass.services.async_call(
                "logbook",
                "log",
                {
                    "name": self.device_name,
                    "message": message,
                    "entity_id": self.primary_entity_id,
                },
            )
        )
        _LOGGER.info(formatted_message)

    async def _persist_data(
        self, data: Optional[Dict[str, Any]] = None, params_only: bool = False
    ) -> None:
        """Unified method for data persistence."""
        try:
            if params_only:
                data_to_save = {"config_parameters": self._get_config_params()}
                _LOGGER.debug(
                    f"[{self.device_name}] Persisting configuration parameters only"
                )
            else:
                data_to_save = {
                    "last_system_command": self._last_system_command,
                    "last_command_timestamp": (
                        self._last_command_timestamp.isoformat()
                        if self._last_command_timestamp
                        else None
                    ),
                    "last_sensor_data": data,
                    "config_parameters": self._get_config_params(),
                    "last_updated": dt_util.now().isoformat(),
                    # NEW: Persist user power-off and manual pause states
                    "user_power_off_detected": self._user_power_off_detected,
                    "manual_pause_until": (
                        self._manual_pause_until.isoformat()
                        if self._manual_pause_until
                        else None
                    ),
                    "last_manual_context_id": self._last_manual_context_id,
                }
                _LOGGER.debug(
                    f"[{self.device_name}] Persisting full data with sensor data"
                )
                if (
                    self._last_system_command
                    and self._last_system_command.get("command_id")
                ):
                    _LOGGER.debug(
                        f"[{self.device_name}] Including command signature: {self._last_system_command.get('command_id')}"
                    )
            await self._store.async_save(data_to_save)
            _LOGGER.debug(f"[{self.device_name}] Data persisted successfully")
        except Exception as e:
            _LOGGER.error(f"[{self.device_name}] Failed to persist data: {e}")

    def _get_config_params(self) -> Dict[str, Any]:
        """Get configuration parameters for storage."""
        return {
            "min_comfort_temp": self.config.get("min_comfort_temp"),
            "max_comfort_temp": self.config.get("max_comfort_temp"),
            "temperature_change_threshold": self.config.get(
                "temperature_change_threshold"
            ),
            "override_temperature": self.config.get("override_temperature"),
            "aggressive_cooling_threshold": self.config.get(
                "aggressive_cooling_threshold"
            ),
            "aggressive_heating_threshold": self.config.get(
                "aggressive_heating_threshold"
            ),
            "energy_save_mode": self.config.get("energy_save_mode", False),
            "auto_mode_enable": self.config.get("auto_mode_enable", False),
            # New HVAC and Fan Control parameters
            "enable_fan_mode": self.config.get("enable_fan_mode", True),
            "enable_cool_mode": self.config.get("enable_cool_mode", True),
            "enable_heat_mode": self.config.get("enable_heat_mode", True),
            "enable_dry_mode": self.config.get("enable_dry_mode", True),
            "enable_off_mode": self.config.get("enable_off_mode", True),
            "max_fan_speed": self.config.get("max_fan_speed", "high"),
            "min_fan_speed": self.config.get("min_fan_speed", "low"),
            # NEW: Manual pause duration
            "manual_pause_duration": self.config.get(
                "manual_pause_duration", 30
            ),
        }

    async def _async_update_data(
        self, skip_override_check: bool = False
    ) -> Dict[str, Any]:
        """Main update method with simplified logic."""
        _LOGGER.debug(f"[{self.device_name}] Starting data update cycle")

        if not self.hass.is_running:
            _LOGGER.debug(
                f"[{self.device_name}] Home Assistant not running - returning default params"
            )
            return self._get_default_params("ha_starting")

        state = self.hass.states.get(self.climate_entity_id)
        if not state:
            _LOGGER.debug(
                f"[{self.device_name}] Climate entity not available - returning default params"
            )
            return self._get_default_params("climate_unavailable")

        # Check if auto mode is enabled
        if not self.config.get("auto_mode_enable", True):
            _LOGGER.debug(
                f"[{self.device_name}] Auto mode disabled - no actions will be taken"
            )
            return self._get_default_params("manual_mode")
        else:
            # Log first auto mode activation
            if not self._auto_mode_logged:
                self.log_event("Auto mode activated")
                self._auto_mode_logged = True

        # NEW: Check if user has powered off the climate device
        current_hvac_mode = state.state
        if self._user_power_off_detected:
            if current_hvac_mode == "off":
                _LOGGER.debug(
                    f"[{self.device_name}] Climate is off by user - waiting for user to turn it back on"
                )
                return self._get_default_params("user_power_off")
            else:
                # User has turned the climate back on - resume normal operation
                _LOGGER.debug(
                    f"[{self.device_name}] User has turned climate back on - resuming normal operation"
                )
                self._user_power_off_detected = False
                self.log_event(
                    "User turned climate back on - resuming automatic control"
                )

        # NEW: Check if we're in manual pause period (for non-power-off changes)
        if self._manual_pause_until:
            now = dt_util.utcnow()
            if now < self._manual_pause_until:
                remaining_minutes = int(
                    (self._manual_pause_until - now).total_seconds() / 60
                )
                remaining_seconds = int(
                    (self._manual_pause_until - now).total_seconds()
                )
                _LOGGER.debug(
                    f"[{self.device_name}] In manual pause period - {remaining_minutes}m {remaining_seconds % 60}s "
                    f"remaining (until {self._manual_pause_until})"
                )
                return self._get_default_params("manual_pause")
            else:
                # Pause period has ended - resume normal operation
                _LOGGER.debug(
                    f"[{self.device_name}] Manual pause period ended at {self._manual_pause_until} - resuming automatic control"
                )
                self._manual_pause_until = None
                # Clear the last manual context ID when pause ends to allow fresh detections
                self._last_manual_context_id = None
                self.log_event(
                    "Manual pause period ended - resuming automatic control"
                )

        # Get sensor data
        _LOGGER.debug(f"[{self.device_name}] Collecting sensor data...")
        sensor_data = self._get_sensor_data(state)
        if not sensor_data:
            _LOGGER.debug(
                f"[{self.device_name}] Sensor data unavailable - returning default params"
            )
            return self._get_default_params("entities_unavailable")

        _LOGGER.debug(
            f"[{self.device_name}] Sensor data collected successfully:"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Indoor temp: {sensor_data['indoor_temp']:.1f}°C"
            if sensor_data["indoor_temp"] is not None
            else f"[{self.device_name}]   - Indoor temp: None"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Outdoor temp: {sensor_data['outdoor_temp']:.1f}°C"
            if sensor_data["outdoor_temp"] is not None
            else f"[{self.device_name}]   - Outdoor temp: None"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Indoor humidity: {sensor_data['indoor_humidity']:.1f}%"
            if sensor_data["indoor_humidity"] is not None
            else f"[{self.device_name}]   - Indoor humidity: None"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Outdoor humidity: {sensor_data['outdoor_humidity']:.1f}%"
            if sensor_data["outdoor_humidity"] is not None
            else f"[{self.device_name}]   - Outdoor humidity: None"
        )

        # Calculate comfort parameters
        _LOGGER.debug(
            f"[{self.device_name}] Calculating comfort parameters..."
        )
        comfort_params = self._calculate_comfort(sensor_data)
        if not comfort_params:
            _LOGGER.debug(
                f"[{self.device_name}] Comfort calculation failed - returning default params"
            )
            return self._get_default_params("calculation_failed")

        _LOGGER.debug(f"[{self.device_name}] Comfort parameters calculated:")
        _LOGGER.debug(
            f"[{self.device_name}]   - ASHRAE compliant: {comfort_params.get('ashrae_compliant')}"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Season: {comfort_params.get('season')}"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Category: {comfort_params.get('category')}"
        )

        # Safe formatting for comfort parameters
        comfort_temp = comfort_params.get("comfort_temp")
        comfort_min = comfort_params.get("comfort_min_ashrae")
        comfort_max = comfort_params.get("comfort_max_ashrae")

        _LOGGER.debug(
            f"[{self.device_name}]   - Comfort temp: {comfort_temp:.2f}°C"
            if comfort_temp is not None
            else f"[{self.device_name}]   - Comfort temp: None"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Comfort range: {comfort_min:.2f}°C - {comfort_max:.2f}°C"
            if comfort_min is not None and comfort_max is not None
            else f"[{self.device_name}]   - Comfort range: None"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - HVAC mode: {comfort_params.get('hvac_mode')}"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Fan mode: {comfort_params.get('fan_mode')}"
        )

        # Determine and execute actions
        _LOGGER.debug(f"[{self.device_name}] Determining control actions...")
        actions = self._determine_actions(comfort_params)

        # Area orchestration gate (always evaluated; if area cannot be resolved, it will allow by default)
        try:
            if not self._area_orchestration_gate(comfort_params):
                _LOGGER.debug(
                    f"[{self.device_name}] Area orchestration gate: not allowed to act now"
                )
                return self._get_default_params("area_orchestration_blocked")
        except Exception as e:
            _LOGGER.warning(
                f"[{self.device_name}] Area orchestration gate failed, proceeding without orchestration: {e}"
            )

        _LOGGER.debug(f"[{self.device_name}] Control actions determined:")
        _LOGGER.debug(
            f"[{self.device_name}]   - Set temperature: {actions.get('set_temperature')}°C (integer for AC)"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Set HVAC mode: {actions.get('set_hvac_mode')}"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Set fan mode: {actions.get('set_fan_mode')}"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Reason: {actions.get('reason')}"
        )

        if self._should_execute_actions(actions):
            _LOGGER.debug(f"[{self.device_name}] Actions will be executed")
            await self._execute_all_actions(actions)
        else:
            _LOGGER.debug(
                f"[{self.device_name}] No actions needed - system already in desired state"
            )

        # Build and save result
        _LOGGER.debug(f"[{self.device_name}] Building result parameters...")
        result_params = self._build_result_params(
            sensor_data, comfort_params, actions
        )
        self._last_valid_params = result_params.copy()
        await self._persist_data(result_params)

        _LOGGER.debug(
            f"[{self.device_name}] Data update cycle completed successfully"
        )
        return result_params

    def _get_sensor_data(self, state) -> Optional[Dict[str, Any]]:
        """Get all sensor data in one method."""
        _LOGGER.debug(
            f"[{self.device_name}] Collecting sensor data from entities..."
        )

        indoor_temp = self._get_value(
            self.indoor_temp_sensor_id, "indoor_temp"
        )
        outdoor_temp = self._get_value(
            self.outdoor_temp_sensor_id, "outdoor_temp"
        )
        indoor_humidity = self._get_value(
            self.indoor_humidity_sensor_id, "indoor_humidity"
        )
        outdoor_humidity = self._get_value(
            self.outdoor_humidity_sensor_id, "outdoor_humidity"
        )

        # Fallback to last valid readings if current is unknown/unavailable
        if indoor_temp is None and self._last_valid_indoor_temp is not None:
            indoor_temp = self._last_valid_indoor_temp
            _LOGGER.debug(
                f"[{self.device_name}] Using last valid indoor temperature: {indoor_temp}"
            )
        if outdoor_temp is None and self._last_valid_outdoor_temp is not None:
            outdoor_temp = self._last_valid_outdoor_temp
            _LOGGER.debug(
                f"[{self.device_name}] Using last valid outdoor temperature: {outdoor_temp}"
            )

        if indoor_temp is None or outdoor_temp is None:
            if not self._sensor_warning_logged:
                _LOGGER.warning(
                    f"[{self.device_name}] Sensor data unavailable during startup - will retry on next update"
                )
                self._sensor_warning_logged = True
            else:
                _LOGGER.debug(
                    f"[{self.device_name}] Skipping cycle due to missing temperature sensors (still unavailable)."
                )
            return None
        else:
            # Reset warning flag once we have good data
            if self._sensor_warning_logged:
                _LOGGER.debug(
                    f"[{self.device_name}] Temperature sensors recovered - resuming normal operation"
                )
                self._sensor_warning_logged = False

        sensor_data = {
            "indoor_temp": indoor_temp,
            "outdoor_temp": outdoor_temp,
            "indoor_humidity": indoor_humidity,
            "outdoor_humidity": outdoor_humidity,
            "current_fan_mode": (
                state.attributes.get("fan_mode") if state else None
            ),
        }

        _LOGGER.debug(
            f"[{self.device_name}] Sensors -> indoor={indoor_temp if indoor_temp is not None else 'NA'}°C, "
            f"outdoor={outdoor_temp if outdoor_temp is not None else 'NA'}°C, "
            f"humidity_in={indoor_humidity if indoor_humidity is not None else 'NA'}%, "
            f"humidity_out={outdoor_humidity if outdoor_humidity is not None else 'NA'}%, "
            f"fan={sensor_data['current_fan_mode']}"
        )

        return sensor_data

    def _calculate_comfort(
        self, sensor_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Calculate comfort parameters with error handling."""
        _LOGGER.debug(f"[{self.device_name}] Starting comfort calculation...")
        try:
            season = get_season(self.hass.config.latitude)
            _LOGGER.debug(f"[{self.device_name}] Detected season: {season}")

            # Get device temperature limits from the climate entity with sanity checks
            state = self.hass.states.get(self.climate_entity_id)
            raw_min = state.attributes.get("min_temp") if state else None
            raw_max = state.attributes.get("max_temp") if state else None
            try:
                device_min_temp = float(raw_min) if raw_min is not None else 16.0
            except Exception:
                device_min_temp = 16.0
            try:
                device_max_temp = float(raw_max) if raw_max is not None else 30.0
            except Exception:
                device_max_temp = 30.0

            # Guard against bogus ranges occasionally exposed by some climate platforms
            # Require reasonable bounds and ordering; otherwise fall back to safe defaults
            if (
                device_min_temp >= device_max_temp
                or device_min_temp < 5.0
                or device_max_temp > 40.0
                or (device_max_temp - device_min_temp) < 5.0
            ):
                _LOGGER.debug(
                    f"[{self.device_name}] Detected unrealistic device temperature limits "
                    f"({device_min_temp}°C - {device_max_temp}°C). Falling back to 16°C - 30°C."
                )
                device_min_temp = 16.0
                device_max_temp = 30.0

            _LOGGER.debug(
                f"[{self.device_name}] Device temperature limits: {device_min_temp}°C - {device_max_temp}°C"
            )

            # Compact input summary
            _LOGGER.debug(
                f"[{self.device_name}] Comfort inputs -> T_in={sensor_data['indoor_temp'] if sensor_data['indoor_temp'] is not None else 'NA'}°C, "
                f"T_out={sensor_data['outdoor_temp'] if sensor_data['outdoor_temp'] is not None else 'NA'}°C, "
                f"H_in={sensor_data['indoor_humidity'] if sensor_data['indoor_humidity'] is not None else 'NA'}%, "
                f"H_out={sensor_data['outdoor_humidity'] if sensor_data['outdoor_humidity'] is not None else 'NA'}%, "
                f"T_rm={self._running_mean_temp if self._running_mean_temp is not None else 'NA'}°C, fan={sensor_data['current_fan_mode']}, "
                f"energy_save={self.config.get('energy_save_mode', False)}, cat={self.config.get('comfort_category', 'I')}, "
                f"comfort_min={self.config.get('min_comfort_temp')}, comfort_max={self.config.get('max_comfort_temp')}, "
                f"cool_thr={self.config.get('aggressive_cooling_threshold', 2.0)}, heat_thr={self.config.get('aggressive_heating_threshold', 2.0)}"
            )

            comfort_params = self._calculator.calculate(
                indoor_temp=sensor_data["indoor_temp"],
                outdoor_temp=sensor_data["outdoor_temp"],
                min_temp=device_min_temp,  # Use device limits, not comfort limits
                max_temp=device_max_temp,  # Use device limits, not comfort limits
                season=season,
                category=self.config.get("comfort_category", "I"),
                air_velocity=sensor_data["current_fan_mode"] or "low",
                indoor_humidity=sensor_data["indoor_humidity"],
                outdoor_humidity=sensor_data["outdoor_humidity"],
                running_mean_temp=self._running_mean_temp,
                energy_save_mode=self.config.get("energy_save_mode", False),
                device_name=self.device_name,
                aggressive_cooling_threshold=self.config.get(
                    "aggressive_cooling_threshold", 2.0
                ),
                aggressive_heating_threshold=self.config.get(
                    "aggressive_heating_threshold", 2.0
                ),
                # New HVAC and Fan Control parameters
                enable_fan_mode=self.config.get("enable_fan_mode", True),
                enable_cool_mode=self.config.get("enable_cool_mode", True),
                enable_heat_mode=self.config.get("enable_heat_mode", True),
                enable_dry_mode=self.config.get("enable_dry_mode", True),
                enable_off_mode=self.config.get("enable_off_mode", True),
                max_fan_speed=self.config.get("max_fan_speed", "high"),
                min_fan_speed=self.config.get("min_fan_speed", "low"),
                # Temperature override parameter
                override_temperature=self.config.get(
                    "override_temperature", 0
                ),
                # Temperature change threshold parameter
                temperature_change_threshold=self.config.get(
                    "temperature_change_threshold", 0.5
                ),
                # Respect user comfort bounds (if set)
                user_comfort_min=self.config.get("min_comfort_temp"),
                user_comfort_max=self.config.get("max_comfort_temp"),
            )

            # Include some raw values useful for orchestration side decisions
            comfort_params["indoor_temperature"] = sensor_data.get(
                "indoor_temp"
            )
            comfort_params["indoor_humidity"] = sensor_data.get(
                "indoor_humidity"
            )

            # Compact calculation results
            comfort_temp = comfort_params.get("comfort_temp")
            comfort_min = (
                comfort_params.get("ashrae_min_temperature")
                or comfort_params.get("comfort_min_ashrae")
            )
            comfort_max = (
                comfort_params.get("ashrae_max_temperature")
                or comfort_params.get("comfort_max_ashrae")
            )
            target_temp = comfort_params.get("target_temp")
            _LOGGER.debug(
                f"[{self.device_name}] Comfort -> ashrae_Tc={comfort_temp if comfort_temp is not None else 'NA'}°C, "
                f"ashrae_range={comfort_min if comfort_min is not None else 'NA'}-{comfort_max if comfort_max is not None else 'NA'}°C, "
                f"user_range={comfort_params.get('user_min_temperature')}-{comfort_params.get('user_max_temperature')}°C, "
                f"target={target_temp if target_temp is not None else 'NA'}°C, "
                f"hvac={comfort_params.get('hvac_mode')}, fan={comfort_params.get('fan_mode')}, ashrae={comfort_params.get('ashrae_compliant')}"
            )

            _LOGGER.debug(
                f"[{self.device_name}] Comfort calculation completed successfully"
            )
            # Stash for secondary fan control in this cycle
            try:
                self._current_comfort_params = dict(comfort_params)
            except Exception:
                self._current_comfort_params = comfort_params
            return comfort_params
        except Exception as e:
            _LOGGER.error(
                f"[{self.device_name}] Failed to calculate comfort parameters: {e}"
            )
            return None







    def _should_use_auto_device_selection(self) -> bool:
        """Determine if automatic device selection should be used."""
        return self.config.get("auto_device_selection", False)

    def _get_area_devices_auto(self, comfort_params: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str], str]:
        """Get area devices using automatic selection based on device type and season."""
        from custom_components.adaptive_climate.utils import (
            area_orchestration_gate as utils_area_gate,
            collect_area_fans,
        )

        # Use automatic device selection based on device type and season
        allowed, primary_id, secondary_id, side = utils_area_gate(
            self.hass, self.climate_entity_id, comfort_params
        )
        
        _LOGGER.debug(
            f"[{self.device_name}] Auto device selection -> allowed={allowed} | primary={primary_id} | secondary={secondary_id} | side={side}"
        )
        
        return allowed, primary_id, secondary_id, side

    def _get_area_devices_manual(self, comfort_params: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str], str]:
        """Get area devices using manual configuration."""
        from custom_components.adaptive_climate.utils import (
            collect_area_fans,
        )

        # Use manual device configuration
        primary_climates = self.config.get("primary_climates", [])
        secondary_climates = self.config.get("secondary_climates", [])
        
        # Check if this device is configured as primary
        is_primary = self.climate_entity_id in primary_climates
        is_secondary = self.climate_entity_id in secondary_climates
        
        # Determine side based on season and comfort parameters
        season_str: str = comfort_params.get("season") or "summer"
        indoor_temp = comfort_params.get("indoor_temperature")
        comfort_min = comfort_params.get("comfort_min_ashrae")
        comfort_max = comfort_params.get("comfort_max_ashrae")
        
        if season_str == "winter":
            side = "heat"
        elif season_str == "summer":
            if indoor_temp is not None and comfort_min is not None and comfort_max is not None:
                if indoor_temp > comfort_max:
                    side = "cool"
                else:
                    side = "fan"
            else:
                side = "cool"
        else:  # shoulder season
            if indoor_temp is not None and comfort_min is not None and comfort_max is not None:
                if indoor_temp > comfort_max:
                    side = "cool"
                elif indoor_temp < comfort_min:
                    side = "heat"
                else:
                    side = "fan"
            else:
                side = "fan"
        
        # Determine primary and secondary IDs
        primary_id = primary_climates[0] if primary_climates else None
        secondary_id = secondary_climates[0] if secondary_climates else None
        
        # Allow action if this device is primary or if no primary is configured
        allowed = is_primary or (not primary_climates and is_secondary) or (not primary_climates and not secondary_climates)
        
        _LOGGER.debug(
            f"[{self.device_name}] Manual device selection -> allowed={allowed} | primary={primary_id} | secondary={secondary_id} | side={side} | is_primary={is_primary} | is_secondary={is_secondary}"
        )
        
        return allowed, primary_id, secondary_id, side

    def _area_orchestration_gate(self, comfort_params: Dict[str, Any]) -> bool:
        """Decide if this coordinator is allowed to act now given area roles.

        Returns True if allowed to act as primary (normal) or as secondary only
        when a hard breach exists; otherwise False to block actions.
        """
        # Choose between automatic and manual device selection
        if self._should_use_auto_device_selection():
            allowed, primary_id, secondary_id, side = self._get_area_devices_auto(comfort_params)
            _LOGGER.debug(
                f"[{self.device_name}] Using AUTOMATIC device selection"
            )
        else:
            allowed, primary_id, secondary_id, side = self._get_area_devices_manual(comfort_params)
            _LOGGER.debug(
                f"[{self.device_name}] Using MANUAL device selection"
            )

        if not allowed:
            return False

        # Backward-compatible fan selection for logging/secondary use
        season_str: str = comfort_params.get("season") or "summer"

        # Determine secondary fans (aux ventilation) for summer/shoulder
        fan_candidates = collect_area_fans(self.hass, self.climate_entity_id)
        selected_fans: List[str] = []
        try:
            if side in ("cool", "fan") and fan_candidates:
                max_fans = int(self.config.get("secondary_fan_max_count", 2))
                selected_fans = sorted(fan_candidates)[:max_fans]
        except Exception:
            selected_fans = []

        # Dwell: keep previous decision for some minutes to avoid flapping
        now = dt_util.utcnow()
        if (
            self._last_role_decision_ts
            and (now - self._last_role_decision_ts)
            < timedelta(minutes=self._role_dwell_minutes)
        ):
            if self._last_role_primary is True:
                return True
            else:
                return False

        self._last_role_decision_ts = now
        self._last_role_primary = True
        return True

    def _should_execute_actions(self, actions: Dict[str, Any]) -> bool:
        """Determine if actions should be executed."""
        _LOGGER.debug(
            f"[{self.device_name}] Evaluating if actions should be executed..."
        )

        state = self.hass.states.get(self.climate_entity_id)
        if not state:
            _LOGGER.debug(
                f"[{self.device_name}] No climate state available - no actions"
            )
            return False

        current_state = {
            "hvac_mode": str(state.state),
            "fan_mode": str(state.attributes.get("fan_mode")),
            "temperature": (
                float(state.attributes.get("temperature"))
                if state.attributes.get("temperature") is not None
                else None
            ),
        }

        desired_state = {
            "hvac_mode": actions.get("set_hvac_mode"),
            "fan_mode": actions.get("set_fan_mode"),
            "temperature": actions.get("set_temperature"),
        }

        _LOGGER.debug(
            f"[{self.device_name}] Compare -> hvac: {current_state['hvac_mode']}->{desired_state['hvac_mode']}, "
            f"fan: {current_state['fan_mode']}->{desired_state['fan_mode']}, "
            f"temp: {current_state['temperature']}->{desired_state['temperature']}°C"
        )

        # Check each component individually
        hvac_changed = current_state["hvac_mode"] != desired_state["hvac_mode"]
        fan_changed = current_state["fan_mode"] != desired_state["fan_mode"]

        # Use temperature_change_threshold from config instead of hardcoded value
        temperature_threshold = self.config.get(
            "temperature_change_threshold", 0.5
        )
        temp_changed = (
            current_state["temperature"] is not None
            and desired_state["temperature"] is not None
            and abs(
                current_state["temperature"] - desired_state["temperature"]
            )
            >= temperature_threshold
        )

        _LOGGER.debug(f"[{self.device_name}] Change detection:")
        _LOGGER.debug(
            f"[{self.device_name}]   - HVAC mode changed: {hvac_changed}"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Fan mode changed: {fan_changed}"
        )
        _LOGGER.debug(
            f"[{self.device_name}]   - Temperature changed: {temp_changed}"
        )

        should_execute = current_state != desired_state
        _LOGGER.debug(
            f"[{self.device_name}] Actions should be executed: {should_execute}"
        )

        if should_execute:
            _LOGGER.debug(
                f"[{self.device_name}] Changes needed - will execute actions"
            )
        else:
            _LOGGER.debug(
                f"[{self.device_name}] No changes needed - skipping actions"
            )

        return should_execute

    

    def _is_system_event_context(self, context: Optional[Context]) -> bool:
        """Determine if a state change event context came from our own command."""
        is_match = is_system_event_context(self._last_system_command, context)
        try:
            event_ctx_id = str(context.id) if context else None
            last_ctx_id = (
                str(self._last_system_command.get("context_id"))
                if self._last_system_command
                else None
            )
            last_parent_id = (
                str(self._last_system_command.get("parent_id"))
                if self._last_system_command
                else None
            )
            _LOGGER.debug(
                f"[{self.device_name}] Checking event context against last command: "
                f"event_ctx={event_ctx_id}, last_ctx={last_ctx_id}, last_parent={last_parent_id}, match={is_match}"
            )
        except Exception:
            pass
        return is_match

    def _has_meaningful_user_change(self, new_state, old_state) -> bool:
        """Proxy to shared helper in utils."""
        return has_meaningful_user_change(new_state, old_state)

    async def _execute_all_actions(self, actions: Dict[str, Any]) -> None:
        """Execute all climate actions in one unified method."""
        _LOGGER.debug(f"[{self.device_name}] Starting action execution...")

        state = self.hass.states.get(self.climate_entity_id)
        if not state or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            _LOGGER.warning(
                f"[{self.device_name}] {self.climate_entity_id} unavailable - skipping actions"
            )
            return

        changes = []
        current_temp = state.attributes.get("temperature")
        current_hvac = state.state
        current_fan = state.attributes.get("fan_mode")
        threshold = self.config.get("temperature_change_threshold", 0.5)

        _LOGGER.debug(
            f"[{self.device_name}] Current state: temp={current_temp}°C, hvac={current_hvac}, fan={current_fan}"
        )

        # Create context for this command chain (always, not just when there are changes)
        context = create_command_context(self.device_name)

        # Temperature
        target_temp = int(actions.get("set_temperature", 0))
        _LOGGER.debug(
            f"[{self.device_name}] Evaluating temperature change: current={current_temp}°C, target={target_temp}°C (integer), threshold={threshold}°C"
        )

        if (
            target_temp is not None
            and (
                current_temp is None
                or abs(target_temp - current_temp) >= threshold
            )
        ):

            _LOGGER.debug(
                f"[{self.device_name}] Setting temperature: {target_temp}°C (integer for AC)"
            )
            await self._call_service(
                CLIMATE_DOMAIN,
                "set_temperature",
                {
                    "entity_id": self.climate_entity_id,
                    "temperature": int(target_temp),  # Ensure integer for AC
                },
                context=context,
            )
            changes.append(
                f"Temperature: {current_temp}°C → {int(target_temp)}°C"
            )
            _LOGGER.debug(
                f"[{self.device_name}] Temperature command sent: {int(target_temp)}°C"
            )
        else:
            _LOGGER.debug(
                f"[{self.device_name}] Temperature change not needed (difference: {abs(target_temp - current_temp) if current_temp else 'N/A'}°C)"
            )

        # Fan mode
        target_fan = actions.get("set_fan_mode")
        supported_fan_modes = state.attributes.get("fan_modes", [])
        _LOGGER.debug(
            f"[{self.device_name}] Evaluating fan mode change: current={current_fan}, target={target_fan}, supported={supported_fan_modes}"
        )

        if target_fan != current_fan and target_fan in supported_fan_modes:
            _LOGGER.debug(
                f"[{self.device_name}] Setting fan mode: {target_fan}"
            )
            await self._call_service(
                CLIMATE_DOMAIN,
                "set_fan_mode",
                {
                    "entity_id": self.climate_entity_id,
                    "fan_mode": target_fan,
                },
                context=context,
            )
            changes.append("fan")
            _LOGGER.debug(
                f"[{self.device_name}] Fan mode updated successfully"
            )
        else:
            _LOGGER.debug(
                f"[{self.device_name}] Fan mode change not needed (same mode or not supported)"
            )

        # HVAC mode
        target_hvac = actions.get("set_hvac_mode")
        supported_hvac_modes = state.attributes.get("hvac_modes", [])
        _LOGGER.debug(
            f"[{self.device_name}] Evaluating HVAC mode change: current={current_hvac}, target={target_hvac}, supported={supported_hvac_modes}"
        )

        if target_hvac != current_hvac and target_hvac in supported_hvac_modes:
            _LOGGER.debug(
                f"[{self.device_name}] Setting HVAC mode: {target_hvac}"
            )
            await self._call_service(
                CLIMATE_DOMAIN,
                "set_hvac_mode",
                {
                    "entity_id": self.climate_entity_id,
                    "hvac_mode": target_hvac,
                },
                context=context,
            )
            changes.append("hvac")
            _LOGGER.debug(
                f"[{self.device_name}] HVAC mode updated successfully"
            )
        else:
            _LOGGER.debug(
                f"[{self.device_name}] HVAC mode change not needed (same mode or not supported)"
            )

        if changes:
            _LOGGER.debug(
                f"[{self.device_name}] Updating last command and persisting data..."
            )
            self._update_last_command(actions, context)
            await self._persist_data()

            # Create concise log message for AC changes
            change_messages = []
            if "temperature" in changes:
                change_messages.append(f"temp: {target_temp}°C")
            if "hvac" in changes:
                change_messages.append(f"mode: {target_hvac}")
            if "fan" in changes:
                change_messages.append(f"fan: {target_fan}")

            if change_messages:
                self.log_event(
                    f"Automatic adjustment: {', '.join(change_messages)}"
                )

            _LOGGER.debug(
                f"[{self.device_name}] Action execution completed successfully - Changes: {changes}"
            )
        # Control secondary fans at the end of cycle regardless of changes
        try:
            if bool(self.config.get("control_secondary_fans", True)):
                await self._control_secondary_fans()
        except Exception as e:
            _LOGGER.debug(f"[{self.device_name}] Secondary fan control skipped due to error: {e}")
        else:
            _LOGGER.debug(
                f"[{self.device_name}] No changes were made - system already in desired state"
            )
            # Still update the last command with context for consistency
            self._update_last_command(actions, context)

    def _update_last_command(
        self, actions: Dict[str, Any], context: Optional[Context] = None
    ) -> None:
        """Update the last system command with context-based signature."""
        _LOGGER.debug(f"[{self.device_name}] Updating last system command...")

        # Use context for command identification
        context_id = context.id if context else None
        parent_id = context.parent_id if context else None
        user_id = context.user_id if context else None

        # If no parent_id is provided, create one that follows our pattern
        if not parent_id:
            parent_id = f"adaptive_climate_{self.device_name}_{int(dt_util.utcnow().timestamp())}"
            _LOGGER.debug(
                f"[{self.device_name}] Created parent_id: {parent_id}"
            )

        self._last_system_command = {
            "hvac_mode": str(actions.get("set_hvac_mode")),
            "fan_mode": str(actions.get("set_fan_mode")),
            "temperature": int(actions.get("set_temperature")),
            "context_id": context_id,  # Home Assistant context ID
            "parent_id": parent_id,  # Parent context ID for command chain
            "user_id": user_id,  # User ID if available
            "source": "adaptive_climate",  # Source identification
            "system_id": self._system_id,  # Device name as system identifier
        }
        self._last_command_timestamp = dt_util.utcnow()
        _LOGGER.debug(
            f"[{self.device_name}] Last command updated: {self._last_system_command}"
        )
        _LOGGER.debug(
            f"[{self.device_name}] Context: {context_id}, Parent: {parent_id}, User: {user_id}, System ID: {self._system_id}"
        )

    def _build_result_params(
        self, sensor_data: Dict[str, Any], comfort: Dict[str, Any], actions: Dict[str, Any]
    ) -> Dict[str, Any]:
        from custom_components.adaptive_climate.utils import build_result_params

        return build_result_params(sensor_data, comfort, actions, self._running_mean_temp)

    async def _control_secondary_fans(self) -> None:
        """Turn secondary fans on/off based on indoor vs comfort temperature.

        Logic:
        - If indoor temperature <= ashrae comfort temperature: turn off all selected secondary fans.
        - If indoor temperature > comfort temperature: turn on secondary fans with graded speed
          relative to the delta: 25% → low, 50% → mid, 75% → high, 100% → highest (if available).
        """
        try:
            params = getattr(self, "_current_comfort_params", None) or {}
            indoor = params.get("indoor_temperature")
            comfort_tc = params.get("ashrae_comfort_temperature") or params.get("comfort_temp")
            user_fans: list[str] = self.config.get("secondary_fans", []) or []
            if not user_fans:
                return
            if indoor is None or comfort_tc is None:
                return
            # Determine action
            if float(indoor) <= float(comfort_tc):
                # turn off all
                for fan_entity in user_fans:
                    await self._call_service(
                        domain="fan",
                        service="turn_off",
                        service_data={"entity_id": fan_entity},
                        context=create_command_context(self.device_name),
                    )
                _LOGGER.debug(f"[{self.device_name}] Secondary fans turned off (indoor<=comfort)")
                return

            # Above comfort: graded speeds
            delta = max(0.0, float(indoor) - float(comfort_tc))
            # Normalize delta into 0..1 scale using user band width as reference
            band = max(0.5, float(self.config.get("max_comfort_temp", 26)) - float(self.config.get("min_comfort_temp", 21)))
            ratio = min(1.0, delta / band)
            # Choose speed level
            if ratio < 0.25:
                speed_alias = "low"
            elif ratio < 0.5:
                speed_alias = "mid"
            elif ratio < 0.75:
                speed_alias = "high"
            else:
                speed_alias = "highest"

            for fan_entity in user_fans:
                # Try to set speed if supported; else just turn_on
                state = self.hass.states.get(fan_entity)
                if state and "percentage" in state.attributes:
                    # Map aliases to percentage
                    alias_to_pct = {"low": 25, "mid": 50, "high": 75, "highest": 100}
                    pct = alias_to_pct.get(speed_alias, 50)
                    await self._call_service(
                        domain="fan",
                        service="turn_on",
                        service_data={"entity_id": fan_entity, "percentage": pct},
                        context=create_command_context(self.device_name),
                    )
                elif state and "preset_modes" in state.attributes:
                    # Some fans expose presets; try to map
                    presets = [str(p).lower() for p in (state.attributes.get("preset_modes") or [])]
                    candidate = next((p for p in ["highest", "high", "medium", "mid", "low", "auto"] if p in presets), None)
                    await self._call_service(
                        domain="fan",
                        service="turn_on",
                        service_data={"entity_id": fan_entity, "preset_mode": candidate or "auto"},
                        context=create_command_context(self.device_name),
                    )
                else:
                    await self._call_service(
                        domain="fan",
                        service="turn_on",
                        service_data={"entity_id": fan_entity},
                        context=create_command_context(self.device_name),
                    )
            _LOGGER.debug(f"[{self.device_name}] Secondary fans set to {speed_alias} (ratio={ratio:.2f})")
        except Exception as e:
            _LOGGER.debug(f"[{self.device_name}] Secondary fan control error: {e}")

    def _get_default_params(self, status: str) -> Dict[str, Any]:
        """Get default parameters."""
        _LOGGER.debug(
            f"[{self.device_name}] Returning default parameters for status: {status}"
        )
        return {
            "adaptive_comfort_temp": 22.0,
            "comfort_temp_min": 20.0,
            "comfort_temp_max": 24.0,
            "status": status,
        }

    def _get_value(
        self, entity_id: Optional[str], sensor_type: Optional[str] = None
    ) -> Optional[float]:
        """Get sensor value with improved error handling."""
        if not entity_id:
            _LOGGER.debug(
                f"[{self.device_name}] No entity ID provided for {sensor_type}"
            )
            return None

        state = self.hass.states.get(entity_id)
        if not state:
            _LOGGER.debug(
                f"[{self.device_name}] No state available for entity {entity_id}"
            )
            return None

        try:
            # Treat common non-numeric states gracefully
            if str(state.state).lower() in (
                "unknown",
                "unavailable",
                "none",
                "nan",
                "inf",
                "-inf",
                "state_unknown",
            ):
                _LOGGER.debug(
                    f"[{self.device_name}] {sensor_type} state for {entity_id} is '{state.state}' (non-numeric), returning None"
                )
                return None
            value = float(state.state)
            # Update last valid value
            last_valid_attr_map = {
                "indoor_temp": "_last_valid_indoor_temp",
                "outdoor_temp": "_last_valid_outdoor_temp",
                "indoor_humidity": "_last_valid_indoor_humidity",
                "outdoor_humidity": "_last_valid_outdoor_humidity",
            }
            if sensor_type in last_valid_attr_map:
                setattr(self, last_valid_attr_map[sensor_type], value)

            _LOGGER.debug(
                f"[{self.device_name}] {sensor_type} value: {value} from {entity_id}"
            )
            return value
        except (ValueError, TypeError):
            _LOGGER.warning(
                f"[{self.device_name}] Failed to convert state '{state.state}' of {entity_id} to float."
            )
            return None

    def _determine_actions(self, comfort: Dict[str, Any]) -> Dict[str, Any]:
        from custom_components.adaptive_climate.utils import determine_actions

        state = self.hass.states.get(self.climate_entity_id)
        supported_hvac_modes: List[str] = []
        supported_fan_modes: List[str] = []
        if state:
            supported_hvac_modes = [str(m) for m in state.attributes.get("hvac_modes", [])]
            supported_fan_modes = [str(m) for m in state.attributes.get("fan_modes", [])]

        actions = determine_actions(
            comfort,
            self.device_name,
            supported_hvac_modes,
            supported_fan_modes,
            self.config,
        )
        _LOGGER.debug(
            f"[{self.device_name}] Final actions: temp={actions['set_temperature']}°C, "
            f"hvac={actions['set_hvac_mode']}, fan={actions['set_fan_mode']}"
        )
        return actions

    async def update_config(
        self, config: Optional[Dict[str, Any]] = None, **kwargs
    ) -> None:
        """Unified config update method with improved auto_mode handling."""
        _LOGGER.debug(f"[{self.device_name}] Updating configuration...")

        # Store previous auto_mode state
        previous_auto_mode = self.config.get("auto_mode_enable", False)

        if config:
            self.config.update(config)
            _LOGGER.debug(
                f"[{self.device_name}] Updated config with: {config}"
            )
        if kwargs:
            self.config.update(kwargs)
            _LOGGER.debug(
                f"[{self.device_name}] Updated config with kwargs: {kwargs}"
            )

        current_auto_mode = self.config.get("auto_mode_enable", False)

        # Handle auto_mode_enable changes
        if "auto_mode_enable" in kwargs:
            if kwargs["auto_mode_enable"] is True and not previous_auto_mode:
                # Auto mode enabled - calculate and apply new settings
                _LOGGER.debug(
                    f"[{self.device_name}] Auto mode enabled - calculating and applying new settings"
                )

                # Reset flags when auto mode is enabled
                self._override_logged = False
                self._auto_mode_logged = False

                # Auto mode enabled - context system will handle override detection automatically

                # Calculate new comfort parameters and apply them (skip override check during activation)
                # Get sensor data and calculate comfort parameters directly
                state = self.hass.states.get(self.climate_entity_id)
                if state:
                    sensor_data = self._get_sensor_data(state)
                    if sensor_data:
                        comfort_params = self._calculate_comfort(sensor_data)
                        if comfort_params:
                            actions = self._determine_actions(comfort_params)
                            self._update_last_command(actions)
                            await self._execute_all_actions(actions)
                            _LOGGER.debug(
                                f"[{self.device_name}] Auto mode settings applied successfully"
                            )
                        else:
                            _LOGGER.error(
                                f"[{self.device_name}] Failed to calculate comfort parameters"
                            )
                    else:
                        _LOGGER.error(
                            f"[{self.device_name}] Failed to get sensor data"
                        )
                else:
                    _LOGGER.error(
                        f"[{self.device_name}] Climate entity not available"
                    )

            elif kwargs["auto_mode_enable"] is False and previous_auto_mode:
                # Auto mode disabled - just log the change
                _LOGGER.debug(
                    f"[{self.device_name}] Auto mode disabled by user"
                )

        # Persist configuration including auto_mode state
        await self._persist_data(params_only=True)

        # Adjust update interval based on auto mode status
        self._adjust_update_interval()

        await self.async_request_refresh()
        _LOGGER.debug(
            f"[{self.device_name}] Configuration update completed - Auto mode: {current_auto_mode}"
        )

    async def _load_outdoor_temp_history(self, days: int = 7) -> None:
        """Load outdoor temperature history."""
        _LOGGER.debug(
            f"[{self.device_name}] Loading outdoor temperature history for {days} days..."
        )
        try:
            start_time = dt_util.now() - timedelta(days=days)
            entity_id = self.outdoor_temp_sensor_id
            if not entity_id:
                _LOGGER.debug(
                    f"[{self.device_name}] No outdoor temperature sensor configured"
                )
                return

            states = await recorder.get_instance(
                self.hass
            ).async_add_executor_job(
                get_significant_states,
                self.hass,
                start_time,
                dt_util.now(),
                [entity_id],
            )

            outdoor_history = []
            for state in states.get(entity_id, []):
                try:
                    temp = float(state.state)
                    outdoor_history.append((state.last_updated, temp))
                except (ValueError, TypeError):
                    continue

            self._outdoor_temp_history = outdoor_history
            self._running_mean_temp = self._calculate_exponential_running_mean(
                self._outdoor_temp_history
            )

            _LOGGER.debug(
                f"[{self.device_name}] Loaded {len(outdoor_history)} temperature records"
            )
            _LOGGER.debug(
                f"[{self.device_name}] Running mean temperature: {self._running_mean_temp:.1f}°C"
                if self._running_mean_temp is not None
                else f"[{self.device_name}] Running mean temperature: None"
            )
        except Exception as e:
            _LOGGER.error(
                f"[{self.device_name}] Failed to load outdoor temperature history: {e}"
            )

    def _calculate_exponential_running_mean(self, history: List[Tuple[datetime, float]], alpha: float = 0.8) -> Optional[float]:
        from custom_components.adaptive_climate.utils import calculate_exponential_running_mean

        return calculate_exponential_running_mean(history, alpha)

    def _check_service_support(
        self, domain: str, service: str, entity_id: str
    ) -> bool:
        """Check if a service is supported by the entity."""
        try:
            # Get the entity state
            state = self.hass.states.get(entity_id)
            if not state:
                _LOGGER.warning(
                    f"[{self.device_name}] Entity {entity_id} not found"
                )
                return False

            # For climate entities, check specific service support
            if domain == CLIMATE_DOMAIN:
                if service == "set_temperature":
                    # Check if the entity has temperature-related attributes
                    has_temp_attr = (
                        state.attributes.get("temperature") is not None
                    )
                    has_target_temp_attr = (
                        state.attributes.get("target_temp") is not None
                    )
                    return has_temp_attr or has_target_temp_attr
                elif service == "set_hvac_mode":
                    # Check if the entity supports HVAC modes
                    hvac_modes = state.attributes.get("hvac_modes", [])
                    return len(hvac_modes) > 0
                elif service == "set_fan_mode":
                    # Check if the entity supports fan modes
                    fan_modes = state.attributes.get("fan_modes", [])
                    return len(fan_modes) > 0

            # For other domains, assume support (can be enhanced later)
            return True

        except Exception as e:
            _LOGGER.warning(
                f"[{self.device_name}] Error checking service support for {domain}.{service}: {e}"
            )
            return False

    async def _call_service(
        self,
        domain: str,
        service: str,
        data: Dict[str, Any],
        context: Optional[Context] = None,
    ) -> None:
        """Call Home Assistant service with context and service support check."""
        entity_id = data.get("entity_id")

        # Check if service is supported
        if entity_id and not self._check_service_support(
            domain, service, entity_id
        ):
            _LOGGER.warning(
                f"[{self.device_name}] Service {domain}.{service} not supported by {entity_id} - skipping"
            )
            return

        _LOGGER.debug(
            f"[{self.device_name}] Calling service {domain}.{service} with data: {data}"
        )
        try:
            await self.hass.services.async_call(
                domain, service, data, context=context
            )
            _LOGGER.debug(
                f"[{self.device_name}] Service {domain}.{service} called successfully"
            )
        except Exception as e:
            _LOGGER.error(
                f"[{self.device_name}] Error calling service {domain}.{service}: {e}"
            )
            # Don't raise the exception to prevent crashes

    async def run_control_cycle(self) -> None:
        """Run a complete control cycle."""
        _LOGGER.debug(f"[{self.device_name}] Starting control cycle...")
        comfort = await self._async_update_data()
        if isinstance(comfort, dict):
            actions = self._determine_actions(comfort)
            await self._execute_all_actions(actions)
        _LOGGER.debug(f"[{self.device_name}] Control cycle completed")

    @callback
    def _handle_state_change(self, event) -> None:
        """Handle state changes of monitored entities."""
        entity_id = event.data.get("entity_id")
        if entity_id != self.climate_entity_id:
            return

        # Get the new and old states
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")

        # Check if this state change came from a manual user action (not from our system command)
        context = event.context
        if context and not self._is_system_event_context(context):
            # Only treat as manual if triggered by a real user (avoid integrations/automations)
            if not getattr(context, "user_id", None):
                _LOGGER.debug(
                    f"[{self.device_name}] Non-user context detected (likely integration/automation) - ignoring for manual pause"
                )
                # Still refresh to pick up changes, but don't apply manual pause
                self.hass.async_create_task(self.async_request_refresh())
                return
            # NEW: Check for duplicate context IDs to avoid multiple resets for the same user action
            if context.id == self._last_manual_context_id:
                _LOGGER.debug(
                    f"[{self.device_name}] Duplicate context ID {context.id} - ignoring to avoid multiple resets"
                )
                return

            _LOGGER.debug(
                f"[{self.device_name}] Manual state change detected for {entity_id} - context: {context.id}"
            )

            # Store this context ID to detect duplicates
            self._last_manual_context_id = context.id

            # NEW: Check if user turned off the climate (power-off detection)
            if new_state and old_state:
                new_hvac_mode = new_state.state
                old_hvac_mode = old_state.state

                # User turned off the climate - pause indefinitely until user turns it back on
                if old_hvac_mode != "off" and new_hvac_mode == "off":
                    _LOGGER.debug(
                        f"[{self.device_name}] User turned off climate ({old_hvac_mode} -> {new_hvac_mode})"
                    )
                    self._user_power_off_detected = True
                    # Clear any existing manual pause since power-off takes priority
                    self._manual_pause_until = None
                    self.log_event(
                        "User turned off climate - automatic control paused until turned back on"
                    )

                # User turned on the climate
                elif old_hvac_mode == "off" and new_hvac_mode != "off":
                    _LOGGER.debug(
                        f"[{self.device_name}] User turned on climate ({old_hvac_mode} -> {new_hvac_mode})"
                    )
                    if self._user_power_off_detected:
                        self._user_power_off_detected = False
                        self.log_event(
                            "User turned climate back on - resuming automatic control"
                        )

                # User made other manual changes (not power-off) - pause for configured duration
                elif (
                    not self._user_power_off_detected
                    and self._has_meaningful_user_change(new_state, old_state)
                ):
                    pause_duration_minutes = self.config.get(
                        "manual_pause_duration", 30
                    )

                    # Check if we were already in a manual pause period
                    was_already_paused = self._manual_pause_until is not None
                    if was_already_paused:
                        remaining_time = (
                            self._manual_pause_until - dt_util.utcnow()
                        ).total_seconds() / 60
                        _LOGGER.debug(
                            f"[{self.device_name}] New manual change while already in pause period (had {remaining_time:.1f}m remaining)"
                        )

                    # Prefer event timestamp for accuracy; fallback to now
                    user_action_time = getattr(event, "time_fired", None)

                    if user_action_time:
                        # Calculate pause end time from the actual user action timestamp (RESET timer)
                        self._manual_pause_until = (
                            user_action_time
                            + timedelta(minutes=pause_duration_minutes)
                        )
                        time_diff = (
                            dt_util.utcnow() - user_action_time
                        ).total_seconds()
                        if was_already_paused:
                            _LOGGER.debug(
                                f"[{self.device_name}] RESET: User made new manual change at {user_action_time} ({time_diff:.1f}s ago) - timer reset, pausing until {self._manual_pause_until}"
                            )
                        else:
                            _LOGGER.debug(
                                f"[{self.device_name}] User made manual change at {user_action_time} ({time_diff:.1f}s ago) - pausing until {self._manual_pause_until}"
                            )
                    else:
                        # Fallback to current time if Context timestamp not available (RESET timer)
                        self._manual_pause_until = (
                            dt_util.utcnow()
                            + timedelta(minutes=pause_duration_minutes)
                        )
                        if was_already_paused:
                            _LOGGER.debug(
                                f"[{self.device_name}] RESET: User made new manual change (no context timestamp) - timer reset, pausing for {pause_duration_minutes} minutes from now"
                            )
                        else:
                            _LOGGER.debug(
                                f"[{self.device_name}] User made manual change (no context timestamp) - pausing for {pause_duration_minutes} minutes from now"
                            )

                    # Log appropriate message based on whether this is a timer reset or new pause
                    if was_already_paused:
                        self.log_event(
                            f"New manual change detected - pause timer reset for {pause_duration_minutes} minutes"
                        )
                    else:
                        self.log_event(
                            f"Manual change detected - automatic control paused for {pause_duration_minutes} minutes"
                        )

            # This is likely a user action - trigger immediate refresh
            self.hass.async_create_task(self.async_request_refresh())
        else:
            _LOGGER.debug(
                f"[{self.device_name}] System state change detected for {entity_id} - requesting refresh (no manual pause applied)"
            )
            self.hass.async_create_task(self.async_request_refresh())

    async def update_comfort_category(self, category: str) -> None:
        """Update comfort category setting."""
        _LOGGER.debug(
            f"[{self.device_name}] Updating comfort category to: {category}"
        )

        if category not in ["I", "II"]:
            _LOGGER.error(
                f"[{self.device_name}] Invalid comfort category: {category}"
            )
            return

        self.config["comfort_category"] = category
        await self._persist_data(params_only=True)

        _LOGGER.debug(
            f"[{self.device_name}] Comfort category updated successfully"
        )

    async def redetect_device_capabilities(self) -> Dict[str, bool]:
        """Force re-detection of device capabilities."""
        _LOGGER.info(
            f"[{self.device_name}] Forcing re-detection of device capabilities..."
        )

        # Detect capabilities
        capabilities = self._detect_device_capabilities()

        # Update configuration with detected capabilities
        self._update_config_with_capabilities(capabilities)

        # Persist the updated configuration
        await self._persist_data(params_only=True)

        _LOGGER.info(
            f"[{self.device_name}] Device capabilities re-detection completed"
        )
        return capabilities

    def get_device_capabilities(self) -> Dict[str, bool]:
        """Get current device capabilities."""
        return {
            "is_cool": self.config.get("enable_cool_mode", True),
            "is_heat": self.config.get("enable_heat_mode", True),
            "is_fan": self.config.get("enable_fan_mode", True),
            "is_dry": self.config.get("enable_dry_mode", True),
            "supports_set_temperature": self._check_service_support(
                CLIMATE_DOMAIN, "set_temperature", self.climate_entity_id
            ),
            "supports_set_hvac_mode": self._check_service_support(
                CLIMATE_DOMAIN, "set_hvac_mode", self.climate_entity_id
            ),
            "supports_set_fan_mode": self._check_service_support(
                CLIMATE_DOMAIN, "set_fan_mode", self.climate_entity_id
            ),
        }
