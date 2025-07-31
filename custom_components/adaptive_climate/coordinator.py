# --- Future Imports ---
from __future__ import annotations

# --- Standard Library ---
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Tuple
import asyncio

# --- Home Assistant Imports ---
from homeassistant.components import recorder
from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback, Context
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util, slugify

# --- Custom Component Imports ---
from .calculator import ComfortCalculator
from .const import DOMAIN, UPDATE_INTERVAL_MEDIUM, UPDATE_INTERVAL_SHORT, UPDATE_INTERVAL_LONG
from .mode_mapper import map_fan_mode, map_hvac_mode, detect_device_capabilities, validate_mode_compatibility
from .multi_device_manager import MultiDeviceManager
from .season_detector import get_season

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
        config_entry_options: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize the coordinator with simplified setup."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_SHORT),  # Start with shorter interval for faster response
        )

        # Setup configuration
        self._setup_config(config_entry_data, config_entry_options)
        self._setup_entities()
        self._setup_storage()
        self._setup_listeners()
        
        _LOGGER.debug(f"[{self.device_name}] Coordinator initialized successfully")

    @property
    def device_name(self) -> str:
        """Get device name for logging."""
        return self.config.get("name", "Adaptive Climate")
    
    @property
    def climate_entity_id(self) -> str:
        """Get first climate entity for backward compatibility."""
        return self.climate_entities[0] if self.climate_entities else ""

    def _setup_config(self, config_entry_data: Dict[str, Any], config_entry_options: Optional[Dict[str, Any]]) -> None:
        """Setup configuration and primary entity ID."""
        self.config: Dict[str, Any] = dict(config_entry_data)
        if config_entry_options:
            self.config.update(config_entry_options)

        # Get first climate entity for primary entity ID
        climate_entities = self._get_climate_entities()
        first_entity = climate_entities[0] if climate_entities else ""
        
        name_slug = slugify(
            first_entity.split(".")[-1] if first_entity else self.device_name
        ).replace("-", "_")
        self.primary_entity_id = (
            f"{first_entity}_ashrae_compliance"
            if first_entity else f"binary_sensor.{name_slug}_ashrae_compliance"
        )

        _LOGGER.debug(f"[{self.device_name}] Configuration setup completed - Primary entity: {self.primary_entity_id}")

    def _setup_entities(self) -> None:
        """Setup and validate monitored entities."""
        # Support both v1.x (single device) and v2.x (multiple devices)
        self.climate_entities = self._get_climate_entities()
        if not self.climate_entities:
            raise ValueError(
                f"[{self.device_name}] Missing required climate entities definition."
            )
        
        # Validate all climate entities
        for entity_id in self.climate_entities:
            if entity_id in GLOBAL_CLIMATE_ENTITIES:
                raise ValueError(f"Entity {entity_id} already linked to another device.")
            GLOBAL_CLIMATE_ENTITIES.add(entity_id)

        # Setup multi-device manager
        self.device_manager = MultiDeviceManager(self.climate_entities, self.device_name)
        self.device_manager.set_hass(self.hass)

        # Setup sensor entities
        self.indoor_temp_sensor_id = self.config.get("indoor_temp_sensor")
        self.outdoor_temp_sensor_id = self.config.get("outdoor_temp_sensor")
        self.indoor_humidity_sensor_id = self.config.get("indoor_humidity_sensor")
        self.outdoor_humidity_sensor_id = self.config.get("outdoor_humidity_sensor")

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
        self._startup_completed: bool = False  # Flag to track startup completion
        
        # Track important events for logbook (only log once)
        self._override_logged: bool = False
        self._auto_mode_logged: bool = False
        
        # Use normalized device name as system identifier (simple and persistent)
        normalized_name = self._normalize_device_name(self.device_name)
        self._system_id = normalized_name
        self._context_prefix = f"adaptive_climate_{self._system_id}"
        _LOGGER.debug(f"[{self.device_name}] Using normalized device name as system ID: {self._system_id}")
        _LOGGER.debug(f"[{self.device_name}] Context prefix: {self._context_prefix}")

        # Setup calculator
        self._calculator = ComfortCalculator()

        _LOGGER.debug(f"[{self.device_name}] Entities setup completed:")
        _LOGGER.debug(f"[{self.device_name}]   - Climate entities: {self.climate_entities}")
        _LOGGER.debug(f"[{self.device_name}]   - Indoor temp sensor: {self.indoor_temp_sensor_id}")
        _LOGGER.debug(f"[{self.device_name}]   - Outdoor temp sensor: {self.outdoor_temp_sensor_id}")
        _LOGGER.debug(f"[{self.device_name}]   - Indoor humidity sensor: {self.indoor_humidity_sensor_id}")
        _LOGGER.debug(f"[{self.device_name}]   - Outdoor humidity sensor: {self.outdoor_humidity_sensor_id}")

    def _get_climate_entities(self) -> List[str]:
        """Get climate entities - support both v1.x and v2.x formats."""
        # v2.x format: multiple entities
        if "climate_entities" in self.config:
            return self.config["climate_entities"]
        
        # v1.x format: single entity (backward compatibility)
        elif "climate_entity" in self.config:
            return [self.config["climate_entity"]]
        
        elif "entity" in self.config:
            return [self.config["entity"]]
        
        return []

    def _detect_device_capabilities(self) -> Dict[str, bool]:
        """Detect device capabilities automatically from climate entity state."""
        _LOGGER.debug(f"[{self.device_name}] Detecting device capabilities...")
        
        # Use first climate entity for backward compatibility
        if not self.climate_entities:
            _LOGGER.warning(f"[{self.device_name}] No climate entities available for capability detection")
            return {
                "is_cool": self.config.get("enable_cool_mode", True),
                "is_heat": self.config.get("enable_heat_mode", True),
                "is_fan": self.config.get("enable_fan_mode", True),
                "is_dry": self.config.get("enable_dry_mode", True),
            }
        
        state = self.hass.states.get(self.climate_entity_id)
        if not state:
            _LOGGER.warning(f"[{self.device_name}] Climate entity not available for capability detection")
            return {
                "is_cool": self.config.get("enable_cool_mode", True),
                "is_heat": self.config.get("enable_heat_mode", True),
                "is_fan": self.config.get("enable_fan_mode", True),
                "is_dry": self.config.get("enable_dry_mode", True),
            }
        
        # Get supported HVAC modes
        supported_hvac_modes = state.attributes.get("hvac_modes", [])
        supported_fan_modes = state.attributes.get("fan_modes", [])
        
        _LOGGER.debug(f"[{self.device_name}] Device capabilities detected:")
        _LOGGER.debug(f"[{self.device_name}]   - Supported HVAC modes: {supported_hvac_modes}")
        _LOGGER.debug(f"[{self.device_name}]   - Supported fan modes: {supported_fan_modes}")
        
        # Use mode_mapper to detect capabilities
        capabilities = detect_device_capabilities(
            supported_hvac_modes, 
            supported_fan_modes, 
            self.device_name
        )
        
        return capabilities

    def _update_config_with_capabilities(self, capabilities: Dict[str, bool]) -> None:
        """Update configuration with detected capabilities."""
        _LOGGER.debug(f"[{self.device_name}] Updating configuration with detected capabilities...")
        
        # Update config with detected capabilities
        self.config["enable_cool_mode"] = capabilities["is_cool"]
        self.config["enable_heat_mode"] = capabilities["is_heat"]
        self.config["enable_fan_mode"] = capabilities["is_fan"]
        self.config["enable_dry_mode"] = capabilities["is_dry"]
        
        _LOGGER.debug(f"[{self.device_name}] Configuration updated with capabilities:")
        _LOGGER.debug(f"[{self.device_name}]   - enable_cool_mode: {self.config['enable_cool_mode']}")
        _LOGGER.debug(f"[{self.device_name}]   - enable_heat_mode: {self.config['enable_heat_mode']}")
        _LOGGER.debug(f"[{self.device_name}]   - enable_fan_mode: {self.config['enable_fan_mode']}")
        _LOGGER.debug(f"[{self.device_name}]   - enable_dry_mode: {self.config['enable_dry_mode']}")
        
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
        
        _LOGGER.info(f"[{self.device_name}] Device type detected: {device_type}")

    async def _setup_device_capabilities(self) -> None:
        """Setup device capabilities detection."""
        _LOGGER.debug(f"[{self.device_name}] Setting up device capabilities detection...")
        
        # Wait a moment for entities to be available
        await asyncio.sleep(1)
        
        # Analyze all devices
        self.device_manager.analyze_all_devices()
        
        # Update configuration with detected capabilities (for backward compatibility)
        if len(self.climate_entities) == 1:
            # Single device - use first device capabilities
            device_id = self.climate_entities[0]
            capabilities = self.device_manager.device_capabilities.get(device_id, {})
            self._update_config_with_capabilities(capabilities)
        
        _LOGGER.debug(f"[{self.device_name}] Device capabilities setup completed")

    def _normalize_device_name(self, device_name: str) -> str:
        """Normalize device name for use as system identifier."""
        import unicodedata
        
        # Remove accents and convert to lowercase
        normalized = unicodedata.normalize('NFD', device_name)
        normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
        
        # Replace spaces and special characters with underscores
        normalized = normalized.replace(' ', '_').replace('-', '_').replace('.', '_')
        
        # Remove any remaining special characters except alphanumeric and underscores
        normalized = ''.join(c for c in normalized if c.isalnum() or c == '_')
        
        # Convert to lowercase
        normalized = normalized.lower()
        
        # Remove leading/trailing underscores
        normalized = normalized.strip('_')
        
        return normalized

    def _setup_storage(self) -> None:
        """Setup storage for persisting data."""
        self._store = Store(
            self.hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}_{self.device_name}"
        )
        _LOGGER.debug(f"[{self.device_name}] Storage setup completed")

    def _setup_listeners(self) -> None:
        """Register state change listener and startup tasks."""
        entities = self.climate_entities
        async_track_state_change_event(self.hass, entities, self._handle_state_change)
        
        # Execute startup immediately for faster response
        self.hass.async_create_task(self._startup())
        _LOGGER.debug(f"[{self.device_name}] Listeners setup completed - monitoring: {entities}")

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
            _LOGGER.debug(f"[{self.device_name}] Auto mode enabled - executing immediate control cycle")
            
            # Execute control cycle immediately
            await self._execute_immediate_control_cycle()
        else:
            _LOGGER.debug(f"[{self.device_name}] Auto mode disabled - skipping initial control cycle")
        
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
            _LOGGER.debug(f"[{self.device_name}] Update interval adjusted to {UPDATE_INTERVAL_MEDIUM} minutes for normal operation")
        else:
            # Use longer interval when auto mode is disabled
            self.update_interval = timedelta(minutes=UPDATE_INTERVAL_LONG)
            _LOGGER.debug(f"[{self.device_name}] Update interval adjusted to {UPDATE_INTERVAL_LONG} minutes (auto mode disabled)")

    async def _execute_immediate_control_cycle(self) -> None:
        """Execute an immediate control cycle with optimized timing."""
        _LOGGER.debug(f"[{self.device_name}] Executing immediate control cycle...")
        
        try:
            # Wait a short moment for sensors to be available
            await asyncio.sleep(2)
            
            # Check if climate entity is available
            state = self.hass.states.get(self.climate_entity_id)
            if not state or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                _LOGGER.warning(f"[{self.device_name}] Climate entity not available during startup - will retry on next update")
                return
            
            # Get sensor data
            sensor_data = self._get_sensor_data(state)
            if not sensor_data:
                _LOGGER.warning(f"[{self.device_name}] Sensor data unavailable during startup - will retry on next update")
                return
            
            # Calculate comfort parameters
            comfort_params = self._calculate_comfort(sensor_data)
            if not comfort_params:
                _LOGGER.warning(f"[{self.device_name}] Comfort calculation failed during startup - will retry on next update")
                return
            
            # Determine and execute actions
            actions = self._determine_actions(comfort_params)
            
            if self._should_execute_actions(actions):
                _LOGGER.debug(f"[{self.device_name}] Startup actions will be executed")
                await self._execute_all_actions(actions)
            else:
                _LOGGER.debug(f"[{self.device_name}] No startup actions needed - system already in desired state")
            
            _LOGGER.debug(f"[{self.device_name}] Immediate control cycle completed successfully")
            
        except Exception as e:
            _LOGGER.error(f"[{self.device_name}] Failed to execute immediate control cycle: {e}")
            # Don't fail startup, just log the error

    async def _load_persisted_data(self) -> None:
        """Load persisted data from storage."""
        try:
            data = await self._store.async_load()
            if data:
                _LOGGER.debug(f"[{self.device_name}] Loading persisted data...")
                
                # Load last system command
                if "last_system_command" in data and data["last_system_command"]:
                    self._last_system_command = data["last_system_command"]
                    _LOGGER.debug(f"[{self.device_name}] Loaded last system command: {self._last_system_command}")
                
                # Load last command timestamp
                if "last_command_timestamp" in data and data["last_command_timestamp"]:
                    try:
                        self._last_command_timestamp = dt_util.parse_datetime(data["last_command_timestamp"])
                        _LOGGER.debug(f"[{self.device_name}] Loaded last command timestamp: {self._last_command_timestamp}")
                    except Exception as e:
                        _LOGGER.warning(f"[{self.device_name}] Failed to parse last command timestamp: {e}")
                
                # Load config parameters
                if "config_parameters" in data and data["config_parameters"]:
                    config_params = data["config_parameters"]
                    for key, value in config_params.items():
                        if key in self.config:
                            self.config[key] = value
                    _LOGGER.debug(f"[{self.device_name}] Loaded config parameters: {config_params}")
                
                _LOGGER.debug(f"[{self.device_name}] Persisted data loaded successfully")
            else:
                _LOGGER.debug(f"[{self.device_name}] No persisted data found")
        except Exception as e:
            _LOGGER.error(f"[{self.device_name}] Failed to load persisted data: {e}")

    def log_event(self, message: str) -> None:
        """Log important message to Home Assistant logbook."""
        formatted_message = f"[{self.device_name}] {message}"
        self.hass.async_create_task(
            self.hass.services.async_call(
                "logbook", "log", {
                    "name": self.device_name,
                    "message": message,
                    "entity_id": self.primary_entity_id,
                }
            )
        )
        _LOGGER.info(formatted_message)


    async def _persist_data(self, data: Optional[Dict[str, Any]] = None, params_only: bool = False) -> None:
        """Unified method for data persistence."""
        try:
            if params_only:
                data_to_save = {"config_parameters": self._get_config_params()}
                _LOGGER.debug(f"[{self.device_name}] Persisting configuration parameters only")
            else:
                data_to_save = {
                    "last_system_command": self._last_system_command,
                    "last_command_timestamp": self._last_command_timestamp.isoformat() if self._last_command_timestamp else None,
                    "last_sensor_data": data,
                    "config_parameters": self._get_config_params(),
                    "last_updated": dt_util.now().isoformat(),
                }
                _LOGGER.debug(f"[{self.device_name}] Persisting full data with sensor data")
                if self._last_system_command and self._last_system_command.get("command_id"):
                    _LOGGER.debug(f"[{self.device_name}] Including command signature: {self._last_system_command.get('command_id')}")
            await self._store.async_save(data_to_save)
            _LOGGER.debug(f"[{self.device_name}] Data persisted successfully")
        except Exception as e:
            _LOGGER.error(f"[{self.device_name}] Failed to persist data: {e}")

    def _get_config_params(self) -> Dict[str, Any]:
        """Get configuration parameters for storage."""
        return {
            "min_comfort_temp": self.config.get("min_comfort_temp"),
            "max_comfort_temp": self.config.get("max_comfort_temp"),
            "temperature_change_threshold": self.config.get("temperature_change_threshold"),
            "override_temperature": self.config.get("override_temperature"),
            "aggressive_cooling_threshold": self.config.get("aggressive_cooling_threshold"),
            "aggressive_heating_threshold": self.config.get("aggressive_heating_threshold"),
            "energy_save_mode": self.config.get("energy_save_mode", False),
            "auto_mode_enable": self.config.get("auto_mode_enable", False),
            # New HVAC and Fan Control parameters
            "enable_fan_mode": self.config.get("enable_fan_mode", True),
            "enable_cool_mode": self.config.get("enable_cool_mode", True),
            "enable_heat_mode": self.config.get("enable_heat_mode", True),
            "enable_dry_mode": self.config.get("enable_dry_mode", True),
            "max_fan_speed": self.config.get("max_fan_speed", "high"),
            "min_fan_speed": self.config.get("min_fan_speed", "low"),
        }

    async def _async_update_data(self, skip_override_check: bool = False) -> Dict[str, Any]:
        """Main update method with simplified logic."""
        _LOGGER.debug(f"[{self.device_name}] Starting data update cycle")

        if not self.hass.is_running:
            _LOGGER.debug(f"[{self.device_name}] Home Assistant not running - returning default params")
            return self._get_default_params("ha_starting")
        
        # Check if primary climate entity is available
        primary_entity_id = self.climate_entity_id  # First entity in the list
        primary_state = self.hass.states.get(primary_entity_id)
        if not primary_state or primary_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.debug(f"[{self.device_name}] Primary climate entity unavailable - returning default params")
            return self._get_default_params("entity_disabled")

        # Check for manual override first (unless skipped for auto mode activation)
        if not skip_override_check:
            _LOGGER.debug(f"[{self.device_name}] Checking for manual override...")
            
            # For manual override detection, we need to check if this is triggered by a state change event
            # If this is a regular update cycle, we can't detect manual override
            if hasattr(self, '_last_state_change_context'):
                _LOGGER.debug(f"[{self.device_name}]   - State change context available: {self._last_state_change_context}")
                if self._detect_manual_override(primary_state):
                    _LOGGER.debug(f"[{self.device_name}] Manual override detected - disabling auto mode")
                    self.config["auto_mode_enable"] = False
                    
                    # Log first manual override detection
                    if not self._override_logged:
                        self.log_event("Manual override detected - auto mode disabled")
                        self._override_logged = True
                    
                    await self._persist_data(params_only=True)
                    return self._get_default_params("manual_override")
                else:
                    _LOGGER.debug(f"[{self.device_name}] No manual override detected")
            else:
                _LOGGER.debug(f"[{self.device_name}] No state change context available - skipping manual override check")
        else:
            _LOGGER.debug(f"[{self.device_name}] Skipping manual override check for auto mode activation")

        if not self.config.get("auto_mode_enable", True):
            _LOGGER.debug(f"[{self.device_name}] Auto mode disabled - no actions will be taken")
            return self._get_default_params("manual_mode")
        else:
            # Log first auto mode activation
            if not self._auto_mode_logged:
                self.log_event("Auto mode activated")
                self._auto_mode_logged = True

        # Get sensor data
        _LOGGER.debug(f"[{self.device_name}] Collecting sensor data...")
        sensor_data = self._get_sensor_data(primary_state)
        if not sensor_data:
            _LOGGER.debug(f"[{self.device_name}] Sensor data unavailable - returning default params")
            return self._get_default_params("entities_unavailable")

        _LOGGER.debug(f"[{self.device_name}] Sensor data collected successfully:")
        _LOGGER.debug(f"[{self.device_name}]   - Indoor temp: {sensor_data['indoor_temp']:.1f}°C" if sensor_data['indoor_temp'] is not None else f"[{self.device_name}]   - Indoor temp: None")
        _LOGGER.debug(f"[{self.device_name}]   - Outdoor temp: {sensor_data['outdoor_temp']:.1f}°C" if sensor_data['outdoor_temp'] is not None else f"[{self.device_name}]   - Outdoor temp: None")
        _LOGGER.debug(f"[{self.device_name}]   - Indoor humidity: {sensor_data['indoor_humidity']:.1f}%" if sensor_data['indoor_humidity'] is not None else f"[{self.device_name}]   - Indoor humidity: None")
        _LOGGER.debug(f"[{self.device_name}]   - Outdoor humidity: {sensor_data['outdoor_humidity']:.1f}%" if sensor_data['outdoor_humidity'] is not None else f"[{self.device_name}]   - Outdoor humidity: None")

        # Calculate comfort parameters
        _LOGGER.debug(f"[{self.device_name}] Calculating comfort parameters...")
        comfort_params = self._calculate_comfort(sensor_data)
        if not comfort_params:
            _LOGGER.debug(f"[{self.device_name}] Comfort calculation failed - returning default params")
            return self._get_default_params("calculation_failed")

        _LOGGER.debug(f"[{self.device_name}] Comfort parameters calculated:")
        _LOGGER.debug(f"[{self.device_name}]   - ASHRAE compliant: {comfort_params.get('ashrae_compliant')}")
        _LOGGER.debug(f"[{self.device_name}]   - Season: {comfort_params.get('season')}")
        _LOGGER.debug(f"[{self.device_name}]   - Category: {comfort_params.get('category')}")
        
        # Safe formatting for comfort parameters
        comfort_temp = comfort_params.get('comfort_temp')
        comfort_min = comfort_params.get('comfort_min_ashrae')
        comfort_max = comfort_params.get('comfort_max_ashrae')
        
        _LOGGER.debug(f"[{self.device_name}]   - Comfort temp: {comfort_temp:.2f}°C" if comfort_temp is not None else f"[{self.device_name}]   - Comfort temp: None")
        _LOGGER.debug(f"[{self.device_name}]   - Comfort range: {comfort_min:.2f}°C - {comfort_max:.2f}°C" if comfort_min is not None and comfort_max is not None else f"[{self.device_name}]   - Comfort range: None")
        _LOGGER.debug(f"[{self.device_name}]   - HVAC mode: {comfort_params.get('hvac_mode')}")
        _LOGGER.debug(f"[{self.device_name}]   - Fan mode: {comfort_params.get('fan_mode')}")

        # Determine and execute actions
        _LOGGER.debug(f"[{self.device_name}] Determining control actions...")
        actions = self._determine_actions(comfort_params)
        
        _LOGGER.debug(f"[{self.device_name}] Control actions determined:")
        _LOGGER.debug(f"[{self.device_name}]   - Set temperature: {actions.get('set_temperature')}°C (integer for AC)")
        _LOGGER.debug(f"[{self.device_name}]   - Set HVAC mode: {actions.get('set_hvac_mode')}")
        _LOGGER.debug(f"[{self.device_name}]   - Set fan mode: {actions.get('set_fan_mode')}")
        _LOGGER.debug(f"[{self.device_name}]   - Reason: {actions.get('reason')}")

        if self._should_execute_actions(actions):
            _LOGGER.debug(f"[{self.device_name}] Actions will be executed")
            await self._execute_all_actions(actions)
        else:
            _LOGGER.debug(f"[{self.device_name}] No actions needed - system already in desired state")

        # Build and save result
        _LOGGER.debug(f"[{self.device_name}] Building result parameters...")
        result_params = self._build_result_params(sensor_data, comfort_params, actions)
        self._last_valid_params = result_params.copy()
        await self._persist_data(result_params)
        
        _LOGGER.debug(f"[{self.device_name}] Data update cycle completed successfully")
        return result_params

    def _get_sensor_data(self, state) -> Optional[Dict[str, Any]]:
        """Get all sensor data in one method."""
        _LOGGER.debug(f"[{self.device_name}] Collecting sensor data from entities...")
        
        indoor_temp = self._get_value(self.indoor_temp_sensor_id, "indoor_temp")
        outdoor_temp = self._get_value(self.outdoor_temp_sensor_id, "outdoor_temp")
        indoor_humidity = self._get_value(self.indoor_humidity_sensor_id, "indoor_humidity")
        outdoor_humidity = self._get_value(self.outdoor_humidity_sensor_id, "outdoor_humidity")

        if indoor_temp is None or outdoor_temp is None:
            _LOGGER.warning(f"[{self.device_name}] Indoor or outdoor temperature unavailable.")
            return None
        
        sensor_data = {
            "indoor_temp": indoor_temp,
            "outdoor_temp": outdoor_temp,
            "indoor_humidity": indoor_humidity,
            "outdoor_humidity": outdoor_humidity,
            "current_fan_mode": state.attributes.get("fan_mode") if state else None,
        }
        
        _LOGGER.debug(f"[{self.device_name}] Sensor data collection completed:")
        _LOGGER.debug(f"[{self.device_name}]   - Indoor temperature: {indoor_temp:.2f}°C" if indoor_temp is not None else f"[{self.device_name}]   - Indoor temperature: None")
        _LOGGER.debug(f"[{self.device_name}]   - Outdoor temperature: {outdoor_temp:.2f}°C" if outdoor_temp is not None else f"[{self.device_name}]   - Outdoor temperature: None")
        _LOGGER.debug(f"[{self.device_name}]   - Indoor humidity: {indoor_humidity:.2f}%" if indoor_humidity is not None else f"[{self.device_name}]   - Indoor humidity: None")
        _LOGGER.debug(f"[{self.device_name}]   - Outdoor humidity: {outdoor_humidity:.2f}%" if outdoor_humidity is not None else f"[{self.device_name}]   - Outdoor humidity: None")
        _LOGGER.debug(f"[{self.device_name}]   - Current fan mode: {sensor_data['current_fan_mode']}")
        
        return sensor_data

    def _calculate_comfort(self, sensor_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calculate comfort parameters with error handling."""
        _LOGGER.debug(f"[{self.device_name}] Starting comfort calculation...")
        try:
            season = get_season(self.hass.config.latitude)
            _LOGGER.debug(f"[{self.device_name}] Detected season: {season}")

            # Log input parameters
            _LOGGER.debug(f"[{self.device_name}] Comfort calculation inputs:")
            _LOGGER.debug(f"[{self.device_name}]   - Indoor temp: {sensor_data['indoor_temp']:.2f}°C" if sensor_data['indoor_temp'] is not None else f"[{self.device_name}]   - Indoor temp: None")
            _LOGGER.debug(f"[{self.device_name}]   - Outdoor temp: {sensor_data['outdoor_temp']:.2f}°C" if sensor_data['outdoor_temp'] is not None else f"[{self.device_name}]   - Outdoor temp: None")
            _LOGGER.debug(f"[{self.device_name}]   - Indoor humidity: {sensor_data['indoor_humidity']:.2f}%" if sensor_data['indoor_humidity'] is not None else f"[{self.device_name}]   - Indoor humidity: None")
            _LOGGER.debug(f"[{self.device_name}]   - Outdoor humidity: {sensor_data['outdoor_humidity']:.2f}%" if sensor_data['outdoor_humidity'] is not None else f"[{self.device_name}]   - Outdoor humidity: None")
            _LOGGER.debug(f"[{self.device_name}]   - Running mean temp: {self._running_mean_temp:.2f}°C" if self._running_mean_temp is not None else f"[{self.device_name}]   - Running mean temp: None")
            _LOGGER.debug(f"[{self.device_name}]   - Fan mode: {sensor_data['current_fan_mode']}")
            _LOGGER.debug(f"[{self.device_name}]   - Energy save mode: {self.config.get('energy_save_mode', False)}")
            _LOGGER.debug(f"[{self.device_name}]   - Comfort category: {self.config.get('comfort_category', 'I')}")
            _LOGGER.debug(f"[{self.device_name}]   - Min comfort temp: {self.config.get('min_comfort_temp', 21)}°C")
            _LOGGER.debug(f"[{self.device_name}]   - Max comfort temp: {self.config.get('max_comfort_temp', 27)}°C")
            _LOGGER.debug(f"[{self.device_name}]   - Aggressive cooling threshold: {self.config.get('aggressive_cooling_threshold', 2.0)}°C")
            _LOGGER.debug(f"[{self.device_name}]   - Aggressive heating threshold: {self.config.get('aggressive_heating_threshold', 2.0)}°C")

            comfort_params = self._calculator.calculate(
                indoor_temp=sensor_data["indoor_temp"],
                outdoor_temp=sensor_data["outdoor_temp"],
                min_temp=self.config.get("min_comfort_temp", 21),
                max_temp=self.config.get("max_comfort_temp", 27),
                season=season,
                category=self.config.get("comfort_category", "I"),
                air_velocity=sensor_data["current_fan_mode"] or "low",
                indoor_humidity=sensor_data["indoor_humidity"],
                outdoor_humidity=sensor_data["outdoor_humidity"],
                running_mean_temp=self._running_mean_temp,
                energy_save_mode=self.config.get("energy_save_mode", False),
                device_name=self.device_name,
                aggressive_cooling_threshold=self.config.get("aggressive_cooling_threshold", 2.0),
                aggressive_heating_threshold=self.config.get("aggressive_heating_threshold", 2.0),
                # New HVAC and Fan Control parameters
                enable_fan_mode=self.config.get("enable_fan_mode", True),
                enable_cool_mode=self.config.get("enable_cool_mode", True),
                enable_heat_mode=self.config.get("enable_heat_mode", True),
                enable_dry_mode=self.config.get("enable_dry_mode", True),
                max_fan_speed=self.config.get("max_fan_speed", "high"),
                min_fan_speed=self.config.get("min_fan_speed", "low"),
                # Temperature override parameter
                override_temperature=self.config.get("override_temperature", 0),
            )

            # Log calculation results
            _LOGGER.debug(f"[{self.device_name}] Comfort calculation results:")
            _LOGGER.debug(f"[{self.device_name}]   - ASHRAE compliant: {comfort_params.get('ashrae_compliant')}")
            _LOGGER.debug(f"[{self.device_name}]   - Season: {comfort_params.get('season')}")
            _LOGGER.debug(f"[{self.device_name}]   - Category: {comfort_params.get('category')}")
            
            # Safe formatting for numeric values that might be None
            comfort_temp = comfort_params.get('comfort_temp')
            comfort_min = comfort_params.get('comfort_min_ashrae')
            comfort_max = comfort_params.get('comfort_max_ashrae')
            target_temp = comfort_params.get('target_temp')
            
            _LOGGER.debug(f"[{self.device_name}]   - Comfort temp: {comfort_temp:.1f}°C" if comfort_temp is not None else f"[{self.device_name}]   - Comfort temp: None")
            _LOGGER.debug(f"[{self.device_name}]   - Comfort range: {comfort_min:.1f}°C - {comfort_max:.1f}°C" if comfort_min is not None and comfort_max is not None else f"[{self.device_name}]   - Comfort range: None")
            _LOGGER.debug(f"[{self.device_name}]   - Target temp: {target_temp:.1f}°C" if target_temp is not None else f"[{self.device_name}]   - Target temp: None")
            _LOGGER.debug(f"[{self.device_name}]   - HVAC mode: {comfort_params.get('hvac_mode')}")
            _LOGGER.debug(f"[{self.device_name}]   - Fan mode: {comfort_params.get('fan_mode')}")
            _LOGGER.debug(f"[{self.device_name}]   - Decision reason: {comfort_params.get('reason', 'No reason provided')}")

            _LOGGER.debug(f"[{self.device_name}] Comfort calculation completed successfully")
            return comfort_params
        except Exception as e:
            _LOGGER.error(f"[{self.device_name}] Failed to calculate comfort parameters: {e}")
            return None

    def _should_execute_actions(self, actions: Dict[str, Any]) -> bool:
        """Determine if actions should be executed."""
        _LOGGER.debug(f"[{self.device_name}] Evaluating if actions should be executed...")
        
        state = self.hass.states.get(self.climate_entity_id)
        if not state:
            _LOGGER.debug(f"[{self.device_name}] No climate state available - no actions")
            return False

        current_state = {
            "hvac_mode": str(state.state),
            "fan_mode": str(state.attributes.get("fan_mode")),
            "temperature": (
            float(state.attributes.get("temperature"))
            if state.attributes.get("temperature") is not None
            else None
        )
        }

        desired_state = {
            "hvac_mode": actions.get("set_hvac_mode"),
            "fan_mode": actions.get("set_fan_mode"),
            "temperature": actions.get("set_temperature")
        }

        _LOGGER.debug(f"[{self.device_name}] State comparison:")
        _LOGGER.debug(f"[{self.device_name}]   - Current HVAC: {current_state['hvac_mode']}")
        _LOGGER.debug(f"[{self.device_name}]   - Desired HVAC: {desired_state['hvac_mode']}")
        _LOGGER.debug(f"[{self.device_name}]   - Current fan: {current_state['fan_mode']}")
        _LOGGER.debug(f"[{self.device_name}]   - Desired fan: {desired_state['fan_mode']}")
        _LOGGER.debug(f"[{self.device_name}]   - Current temp: {current_state['temperature']}°C")
        _LOGGER.debug(f"[{self.device_name}]   - Desired temp: {desired_state['temperature']}°C")

        # Check each component individually
        hvac_changed = current_state["hvac_mode"] != desired_state["hvac_mode"]
        fan_changed = current_state["fan_mode"] != desired_state["fan_mode"]
        temp_changed = (
            current_state["temperature"] is not None and
            desired_state["temperature"] is not None and
            abs(current_state["temperature"] - desired_state["temperature"]) >= 0.5
        )

        _LOGGER.debug(f"[{self.device_name}] Change detection:")
        _LOGGER.debug(f"[{self.device_name}]   - HVAC mode changed: {hvac_changed}")
        _LOGGER.debug(f"[{self.device_name}]   - Fan mode changed: {fan_changed}")
        _LOGGER.debug(f"[{self.device_name}]   - Temperature changed: {temp_changed}")

        should_execute = current_state != desired_state
        _LOGGER.debug(f"[{self.device_name}] Actions should be executed: {should_execute}")
        
        if should_execute:
            _LOGGER.debug(f"[{self.device_name}] Changes needed - will execute actions")
        else:
            _LOGGER.debug(f"[{self.device_name}] No changes needed - skipping actions")
            
        return should_execute

    def _is_system_command(self, command_data: Dict[str, Any]) -> bool:
        """Verify if a command is legitimate from the adaptive climate system using device name."""
        if not command_data:
            return False
        
        # Check for required signature fields
        system_id = command_data.get("system_id")
        source = command_data.get("source")
        
        # Must have source
        if source != "adaptive_climate":
            return False
        
        # Check if system_id matches our device name
        if system_id and system_id == self._system_id:
            return True
        
        # Fallback: check if parent_id indicates our system (for backward compatibility)
        parent_id = command_data.get("parent_id")
        if parent_id and str(parent_id).startswith("adaptive_climate"):
            return True
        
        # Fallback: check if context_id starts with our pattern (for older commands)
        context_id = command_data.get("context_id")
        if context_id and str(context_id).startswith("adaptive_climate"):
            return True
        
        return False

    def _detect_manual_override(self, state) -> bool:
        """Detect if user has manually overridden the system using Home Assistant Context."""
        
        # Get the context from the stored state change event
        context = getattr(self, '_last_state_change_context', None)
        if not context:
            _LOGGER.debug(f"[{self.device_name}] No context available for manual override detection")
            return False
            
        _LOGGER.debug(f"[{self.device_name}] Checking for manual override using HA Context:")
        _LOGGER.debug(f"[{self.device_name}]   - Context ID: {context.id}")
        _LOGGER.debug(f"[{self.device_name}]   - Parent ID: {context.parent_id}")
        _LOGGER.debug(f"[{self.device_name}]   - User ID: {context.user_id}")
        
        # Check if this is a recent system command (within last 10 seconds)
        # If so, don't detect override yet - wait for state to settle
        if hasattr(self, '_last_command_timestamp') and self._last_command_timestamp:
            time_since_command = (dt_util.utcnow() - self._last_command_timestamp).total_seconds()
            if time_since_command < 10.0:  # 10 second grace period
                _LOGGER.debug(f"[{self.device_name}]   - Recent system command ({time_since_command:.1f}s ago) - waiting for state to settle")
                return False
        
        # Rule 1: Check if context indicates this is from our system
        # Our system commands have specific context patterns
        is_system_command = False
        
        # Check if context ID starts with our pattern
        if context.id and str(context.id).startswith("adaptive_climate"):
            is_system_command = True
            _LOGGER.debug(f"[{self.device_name}]   - Context ID indicates system command")
        
        # Check if parent ID starts with our pattern
        elif context.parent_id and str(context.parent_id).startswith("adaptive_climate"):
            is_system_command = True
            _LOGGER.debug(f"[{self.device_name}]   - Parent ID indicates system command")
        
        # Check if this is a service call from our system
        elif context.id and "service" in str(context.id).lower():
            # Check if it's our service call
            if self._system_id in str(context.id):
                is_system_command = True
                _LOGGER.debug(f"[{self.device_name}]   - Service call indicates system command")
        
        if is_system_command:
            _LOGGER.debug(f"[{self.device_name}]   - This is a system command - no manual override")
            return False
        else:
            _LOGGER.debug(f"[{self.device_name}]   - This appears to be a manual user action")
            return True

    async def _execute_all_actions(self, actions: Dict[str, Any]) -> None:
        """Execute all climate actions for multiple devices."""
        _LOGGER.debug(f"[{self.device_name}] Starting action execution for {len(actions)} devices...")
        
        # Create context for this command chain
        context = Context(parent_id=f"{self._context_prefix}_{int(dt_util.utcnow().timestamp())}")
        
        all_changes = []
        threshold = self.config.get("temperature_change_threshold", 0.5)
        
        for device_id, action in actions.items():
            _LOGGER.debug(f"[{self.device_name}] Executing action for device {device_id}: {action}")
            
            # Check if device is available
            state = self.hass.states.get(device_id)
            if not state or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                _LOGGER.warning(f"[{self.device_name}] Device {device_id} unavailable - skipping action")
                continue
            
            device_changes = []
            current_temp = state.attributes.get('temperature')
            current_hvac = state.state
            current_fan = state.attributes.get('fan_mode')
            
            _LOGGER.debug(f"[{self.device_name}] Device {device_id} current state:")
            _LOGGER.debug(f"[{self.device_name}]   - Temperature: {current_temp}°C")
            _LOGGER.debug(f"[{self.device_name}]   - HVAC mode: {current_hvac}")
            _LOGGER.debug(f"[{self.device_name}]   - Fan mode: {current_fan}")
            
            # Temperature
            target_temp = int(action.get("set_temperature", 0))
            if (target_temp is not None and 
                (current_temp is None or abs(target_temp - current_temp) >= threshold) and
                action.get("set_hvac_mode") != "fan_only"):
                
                _LOGGER.debug(f"[{self.device_name}] Setting temperature for {device_id}: {target_temp}°C")
                await self.hass.services.async_call(
                    CLIMATE_DOMAIN, "set_temperature", {
                        "entity_id": device_id,
                        "temperature": int(target_temp),
                    }, blocking=False, context=context
                )
                device_changes.append(f"temp: {target_temp}°C")
            
            # Fan mode
            target_fan = action.get("set_fan_mode")
            supported_fan_modes = state.attributes.get("fan_modes", [])
            if target_fan != current_fan and target_fan in supported_fan_modes:
                _LOGGER.debug(f"[{self.device_name}] Setting fan mode for {device_id}: {target_fan}")
                await self._call_service(CLIMATE_DOMAIN, "set_fan_mode", {
                    "entity_id": device_id,
                    "fan_mode": target_fan,
                }, context=context)
                device_changes.append(f"fan: {target_fan}")
            
            # HVAC mode
            target_hvac = action.get("set_hvac_mode")
            supported_hvac_modes = state.attributes.get("hvac_modes", [])
            if target_hvac != current_hvac and target_hvac in supported_hvac_modes:
                _LOGGER.debug(f"[{self.device_name}] Setting HVAC mode for {device_id}: {target_hvac}")
                await self._call_service(CLIMATE_DOMAIN, "set_hvac_mode", {
                    "entity_id": device_id,
                    "hvac_mode": target_hvac,
                }, context=context)
                device_changes.append(f"mode: {target_hvac}")
            
            if device_changes:
                all_changes.append(f"{device_id} ({action.get('priority', 'unknown')}): {', '.join(device_changes)}")
                _LOGGER.debug(f"[{self.device_name}] Device {device_id} changes: {device_changes}")
        
        if all_changes:
            _LOGGER.debug(f"[{self.device_name}] Updating last command and persisting data...")
            self._update_last_command(actions, context)
            await self._persist_data()
            
            # Create concise log message for all changes
            self.log_event(f"Multi-device adjustment: {'; '.join(all_changes)}")
            
            _LOGGER.debug(f"[{self.device_name}] Action execution completed successfully - Changes: {all_changes}")
        else:
            _LOGGER.debug(f"[{self.device_name}] No changes were made - all devices already in desired state")
            # Still update the last command with context for consistency
            self._update_last_command(actions, context)

    def _update_last_command(self, actions: Dict[str, Any], context: Optional[Context] = None) -> None:
        """Update the last system command with context-based signature."""
        _LOGGER.debug(f"[{self.device_name}] Updating last system command...")
        
        # Use context for command identification
        context_id = context.id if context else None
        parent_id = context.parent_id if context else None
        user_id = context.user_id if context else None
        
        # If no parent_id is provided, create one that follows our pattern
        if not parent_id:
            parent_id = f"{self._context_prefix}_{int(dt_util.utcnow().timestamp())}"
            _LOGGER.debug(f"[{self.device_name}] Created parent_id: {parent_id}")
        
        self._last_system_command = {
            "hvac_mode": str(actions.get("set_hvac_mode")),
            "fan_mode": str(actions.get("set_fan_mode")),
            "temperature": int(actions.get("set_temperature")),
            "context_id": context_id,  # Home Assistant context ID
            "parent_id": parent_id,    # Parent context ID for command chain
            "user_id": user_id,        # User ID if available
            "source": "adaptive_climate",  # Source identification
            "system_id": self._system_id,  # Device name as system identifier
        }
        self._last_command_timestamp = dt_util.utcnow()
        _LOGGER.debug(f"[{self.device_name}] Last command updated: {self._last_system_command}")
        _LOGGER.debug(f"[{self.device_name}] Context: {context_id}, Parent: {parent_id}, User: {user_id}, System ID: {self._system_id}")

    def _build_result_params(self, sensor_data: Dict[str, Any], comfort: Dict[str, Any], actions: Dict[str, Any]) -> Dict[str, Any]:
        """Build result parameters."""
        _LOGGER.debug(f"[{self.device_name}] Building result parameters...")
        
        # Format temperatures with 2 decimal places for display
        comfort_temp = comfort.get("comfort_temp")
        comfort_min = comfort.get("comfort_min_ashrae")
        comfort_max = comfort.get("comfort_max_ashrae")
        
        result = {
            "adaptive_comfort_temp": round(comfort_temp, 2) if comfort_temp is not None else None,
            "comfort_temp_min": round(comfort_min, 2) if comfort_min is not None else None,
            "comfort_temp_max": round(comfort_max, 2) if comfort_max is not None else None,
            "indoor_temperature": round(sensor_data["indoor_temp"], 2) if sensor_data["indoor_temp"] is not None else None,
            "outdoor_temperature": round(sensor_data["outdoor_temp"], 2) if sensor_data["outdoor_temp"] is not None else None,
            "indoor_humidity": round(sensor_data["indoor_humidity"], 2) if sensor_data["indoor_humidity"] is not None else None,
            "outdoor_humidity": round(sensor_data["outdoor_humidity"], 2) if sensor_data["outdoor_humidity"] is not None else None,
            "running_mean_temp": round(self._running_mean_temp, 2) if self._running_mean_temp is not None else None,
            "control_actions": actions,
            "ashrae_compliant": comfort.get("ashrae_compliant"),
            "last_updated": dt_util.now(),
        }
        
        _LOGGER.debug(f"[{self.device_name}] Result parameters built successfully:")
        _LOGGER.debug(f"[{self.device_name}]   - Adaptive comfort temp: {result['adaptive_comfort_temp']:.2f}°C" if result['adaptive_comfort_temp'] is not None else f"[{self.device_name}]   - Adaptive comfort temp: None")
        _LOGGER.debug(f"[{self.device_name}]   - Comfort range: {result['comfort_temp_min']:.2f}°C - {result['comfort_temp_max']:.2f}°C" if result['comfort_temp_min'] is not None and result['comfort_temp_max'] is not None else f"[{self.device_name}]   - Comfort range: None")
        _LOGGER.debug(f"[{self.device_name}]   - Indoor temperature: {result['indoor_temperature']:.2f}°C" if result['indoor_temperature'] is not None else f"[{self.device_name}]   - Indoor temperature: None")
        _LOGGER.debug(f"[{self.device_name}]   - Outdoor temperature: {result['outdoor_temperature']:.2f}°C" if result['outdoor_temperature'] is not None else f"[{self.device_name}]   - Outdoor temperature: None")
        _LOGGER.debug(f"[{self.device_name}]   - Running mean temp: {result['running_mean_temp']:.2f}°C" if result['running_mean_temp'] is not None else f"[{self.device_name}]   - Running mean temp: None")
        
        return result

    def _get_default_params(self, status: str) -> Dict[str, Any]:
        """Get default parameters."""
        _LOGGER.debug(f"[{self.device_name}] Returning default parameters for status: {status}")
        return {
            "adaptive_comfort_temp": 22.0,
            "comfort_temp_min": 20.0,
            "comfort_temp_max": 24.0,
            "status": status,
        }

    def _get_value(self, entity_id: Optional[str], sensor_type: Optional[str] = None) -> Optional[float]:
        """Get sensor value with improved error handling."""
        if not entity_id:
            _LOGGER.debug(f"[{self.device_name}] No entity ID provided for {sensor_type}")
            return None

        state = self.hass.states.get(entity_id)
        if not state:
            _LOGGER.debug(f"[{self.device_name}] No state available for entity {entity_id}")
            return None

        try:
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
            
            _LOGGER.debug(f"[{self.device_name}] {sensor_type} value: {value} from {entity_id}")
            return value
        except (ValueError, TypeError):
            _LOGGER.warning(f"[{self.device_name}] Failed to convert state '{state.state}' of {entity_id} to float.")
            return None

    def _determine_actions(self, comfort: Dict[str, Any]) -> Dict[str, Any]:
        """Determine control actions for multiple devices."""
        _LOGGER.debug(f"[{self.device_name}] Determining control actions from comfort parameters...")
        
        temperature = round(float(comfort.get("target_temp", 25)))
        hvac_mode = comfort.get("hvac_mode")
        fan_mode = comfort.get("fan_mode")

        _LOGGER.debug(f"[{self.device_name}] Initial comfort decisions:")
        _LOGGER.debug(f"[{self.device_name}]   - Target temperature: {temperature}°C (integer for AC)")
        _LOGGER.debug(f"[{self.device_name}]   - HVAC mode: {hvac_mode}")
        _LOGGER.debug(f"[{self.device_name}]   - Fan mode: {fan_mode}")

        if hvac_mode == "fan_only" and fan_mode in ["highest", "max"]:
            fan_mode = "high"
            _LOGGER.debug(f"[{self.device_name}] Adjusted fan mode from {comfort.get('fan_mode')} to {fan_mode} (HVAC is fan_only)")

        # Analyze needs based on comfort parameters
        needs = self._analyze_needs(comfort)
        _LOGGER.debug(f"[{self.device_name}] Analyzed needs: {needs}")
        
        # Get optimal devices for current needs (with availability check)
        optimal_devices = self.device_manager.get_available_devices(needs)
        
        # Generate actions for all devices
        all_actions = {}
        
        # Primary devices (most efficient for the need)
        for device_id in optimal_devices["primary"]:
            action = self._get_device_action(comfort, device_id, needs, "primary")
            if action:
                all_actions[device_id] = action
        
        # Auxiliary devices (for fine-tuning)
        for device_id in optimal_devices["auxiliary"]:
            action = self._get_device_action(comfort, device_id, needs, "auxiliary")
            if action:
                all_actions[device_id] = action
        
        # If no devices were selected, use the first device (backward compatibility)
        if not all_actions and len(self.climate_entities) == 1:
            device_id = self.climate_entities[0]
            action = self._get_device_action(comfort, device_id, needs, "primary")
            if action:
                all_actions[device_id] = action
        
        _LOGGER.debug(f"[{self.device_name}] Final control actions: {all_actions}")
        return all_actions
    
    def _analyze_needs(self, comfort: Dict[str, Any]) -> List[str]:
        """Analyze what capabilities are needed based on comfort parameters."""
        needs = []
        
        hvac_mode = comfort.get("hvac_mode", "")
        fan_mode = comfort.get("fan_mode", "")
        
        # Determine needs based on HVAC mode
        if hvac_mode == "cool":
            needs.append("cool")
        elif hvac_mode == "heat":
            needs.append("heat")
        elif hvac_mode == "dry":
            needs.append("dry")
        elif hvac_mode == "fan_only":
            needs.append("fan")
        
        # Add fan need if fan mode is specified (but only for cooling/dry modes)
        if fan_mode and fan_mode != "off" and hvac_mode in ["cool", "dry", "fan_only"]:
            if "fan" not in needs:
                needs.append("fan")
        
        return needs
    
    def _get_device_action(self, comfort: Dict[str, Any], device_id: str, needs: List[str], priority: str) -> Optional[Dict[str, Any]]:
        """Get action for a specific device."""
        temperature = round(float(comfort.get("target_temp", 25)))
        hvac_mode = comfort.get("hvac_mode")
        fan_mode = comfort.get("fan_mode")
        
        # Get device capabilities
        capabilities = self.device_manager.device_capabilities.get(device_id, {})
        
        # Check if device is eligible for the requested operation
        if not self._is_device_eligible_for_operation(device_id, capabilities, hvac_mode, needs):
            _LOGGER.debug(f"[{self.device_name}] Device {device_id} is not eligible for {hvac_mode} operation")
            return None
        
        # Get device state for validation
        state = self.hass.states.get(device_id)
        if not state:
            _LOGGER.warning(f"[{self.device_name}] Device {device_id} not available")
            return None
        
        supported_hvac_modes = [str(mode) for mode in state.attributes.get("hvac_modes", [])]
        supported_fan_modes = [str(mode) for mode in state.attributes.get("fan_modes", [])]
        
        # Validate mode compatibility
        validation = validate_mode_compatibility(
            hvac_mode, fan_mode, supported_hvac_modes, supported_fan_modes, device_id
        )
        
        if not validation["compatible"]:
            _LOGGER.warning(f"[{self.device_name}] Device {device_id} mode compatibility issues:")
            if not validation["hvac_valid"]:
                hvac_mode = validation["hvac_suggestion"]
            if not validation["fan_valid"]:
                fan_mode = validation["fan_suggestion"]
        
        # Map modes to supported ones
        mapped_hvac = map_hvac_mode(str(hvac_mode), supported_hvac_modes, device_id) if supported_hvac_modes else hvac_mode
        mapped_fan = map_fan_mode(str(fan_mode), supported_fan_modes, device_id) if supported_fan_modes else fan_mode
        
        # Adjust fan mode based on HVAC mode and device capabilities
        mapped_fan = self._adjust_fan_mode_for_hvac(mapped_hvac, mapped_fan, device_id, capabilities, supported_fan_modes)
        
        # Check if device can handle the mapped mode
        can_handle_hvac = capabilities.get(f"is_{mapped_hvac}", False) if mapped_hvac != "off" else True
        can_handle_fan = capabilities.get("is_fan", True) if mapped_fan != "off" else True
        
        if not can_handle_hvac and not can_handle_fan:
            _LOGGER.debug(f"[{self.device_name}] Device {device_id} cannot handle requested modes")
            return None
        
        action = {
            "set_temperature": temperature,
            "set_hvac_mode": mapped_hvac,
            "set_fan_mode": mapped_fan,
            "priority": priority,
            "reason": f"Device {device_id} ({priority}): {mapped_hvac}, {temperature}°C, {mapped_fan}",
        }
        
        _LOGGER.debug(f"[{self.device_name}] Action for {device_id}: {action}")
        return action
    
    def _adjust_fan_mode_for_hvac(self, hvac_mode: str, fan_mode: str, device_id: str, capabilities: Dict[str, bool], supported_fan_modes: List[str]) -> str:
        """Adjust fan mode based on HVAC mode and device capabilities."""
        _LOGGER.debug(f"[{self.device_name}] Adjusting fan mode for {device_id}: hvac={hvac_mode}, fan={fan_mode}")
        
        # If HVAC mode is cool, heat, or dry, fan should be on (not off)
        if hvac_mode in ["cool", "heat", "dry"] and fan_mode == "off":
            # Find the best available fan mode
            if "auto" in supported_fan_modes:
                fan_mode = "auto"
                _LOGGER.debug(f"[{self.device_name}] Adjusted fan mode to 'auto' for {hvac_mode} mode")
            elif "low" in supported_fan_modes:
                fan_mode = "low"
                _LOGGER.debug(f"[{self.device_name}] Adjusted fan mode to 'low' for {hvac_mode} mode")
            elif "mid" in supported_fan_modes:
                fan_mode = "mid"
                _LOGGER.debug(f"[{self.device_name}] Adjusted fan mode to 'mid' for {hvac_mode} mode")
            elif "high" in supported_fan_modes:
                fan_mode = "high"
                _LOGGER.debug(f"[{self.device_name}] Adjusted fan mode to 'high' for {hvac_mode} mode")
            elif len(supported_fan_modes) > 0:
                fan_mode = supported_fan_modes[0]  # Use first available
                _LOGGER.debug(f"[{self.device_name}] Adjusted fan mode to '{fan_mode}' for {hvac_mode} mode")
        
        # If HVAC mode is fan_only, ensure fan is not off
        elif hvac_mode == "fan_only" and fan_mode == "off":
            if "low" in supported_fan_modes:
                fan_mode = "low"
                _LOGGER.debug(f"[{self.device_name}] Adjusted fan mode to 'low' for fan_only mode")
            elif "mid" in supported_fan_modes:
                fan_mode = "mid"
                _LOGGER.debug(f"[{self.device_name}] Adjusted fan mode to 'mid' for fan_only mode")
            elif "high" in supported_fan_modes:
                fan_mode = "high"
                _LOGGER.debug(f"[{self.device_name}] Adjusted fan mode to 'high' for fan_only mode")
            elif len(supported_fan_modes) > 0:
                fan_mode = supported_fan_modes[0]
                _LOGGER.debug(f"[{self.device_name}] Adjusted fan mode to '{fan_mode}' for fan_only mode")
        
        # If HVAC mode is off, fan should be off
        elif hvac_mode == "off":
            fan_mode = "off"
            _LOGGER.debug(f"[{self.device_name}] Set fan mode to 'off' for off mode")
        
        return fan_mode
    
    def _is_device_eligible_for_operation(self, device_id: str, capabilities: Dict[str, bool], hvac_mode: str, needs: List[str]) -> bool:
        """Check if device is eligible for the requested operation."""
        _LOGGER.debug(f"[{self.device_name}] Checking eligibility for {device_id}: hvac={hvac_mode}, needs={needs}")
        
        # If calculator requests heat, exclude fan-only devices
        if hvac_mode == "heat":
            # Check if device is fan-only (has fan but no heat capability)
            if capabilities.get("is_fan", False) and not capabilities.get("is_heat", False):
                _LOGGER.debug(f"[{self.device_name}] Device {device_id} is fan-only and not eligible for heating")
                return False
        
        # If calculator requests cool, exclude heat-only devices
        elif hvac_mode == "cool":
            # Check if device is heat-only (has heat but no cool capability)
            if capabilities.get("is_heat", False) and not capabilities.get("is_cool", False):
                _LOGGER.debug(f"[{self.device_name}] Device {device_id} is heat-only and not eligible for cooling")
                return False
        
        # If calculator requests dry, exclude devices without dry capability
        elif hvac_mode == "dry":
            if not capabilities.get("is_dry", False):
                _LOGGER.debug(f"[{self.device_name}] Device {device_id} has no dry capability")
                return False
        
        # If calculator requests fan_only, exclude devices without fan capability
        elif hvac_mode == "fan_only":
            if not capabilities.get("is_fan", False):
                _LOGGER.debug(f"[{self.device_name}] Device {device_id} has no fan capability")
                return False
        
        # Check if device has the required capability for the HVAC mode
        if hvac_mode != "off":
            required_capability = f"is_{hvac_mode}"
            if not capabilities.get(required_capability, False):
                _LOGGER.debug(f"[{self.device_name}] Device {device_id} lacks required capability: {required_capability}")
                return False
        
        _LOGGER.debug(f"[{self.device_name}] Device {device_id} is eligible for {hvac_mode} operation")
        return True

    async def update_config(self, config: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Unified config update method with improved auto_mode handling."""
        _LOGGER.debug(f"[{self.device_name}] Updating configuration...")
        
        # Store previous auto_mode state
        previous_auto_mode = self.config.get("auto_mode_enable", False)
        
        if config:
            self.config.update(config)
            _LOGGER.debug(f"[{self.device_name}] Updated config with: {config}")
        if kwargs:
            self.config.update(kwargs)
            _LOGGER.debug(f"[{self.device_name}] Updated config with kwargs: {kwargs}")
        
        current_auto_mode = self.config.get("auto_mode_enable", False)
        
        # Handle auto_mode_enable changes
        if "auto_mode_enable" in kwargs:
            if kwargs["auto_mode_enable"] is True and not previous_auto_mode:
                # Auto mode enabled - calculate and apply new settings
                _LOGGER.debug(f"[{self.device_name}] Auto mode enabled - calculating and applying new settings")
                
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
                            _LOGGER.debug(f"[{self.device_name}] Auto mode settings applied successfully")
                        else:
                            _LOGGER.error(f"[{self.device_name}] Failed to calculate comfort parameters")
                    else:
                        _LOGGER.error(f"[{self.device_name}] Failed to get sensor data")
                else:
                    _LOGGER.error(f"[{self.device_name}] Climate entity not available")
                
            elif kwargs["auto_mode_enable"] is False and previous_auto_mode:
                # Auto mode disabled - just log the change
                _LOGGER.debug(f"[{self.device_name}] Auto mode disabled by user")
        
        # Persist configuration including auto_mode state
        await self._persist_data(params_only=True)
        
        # Adjust update interval based on auto mode status
        self._adjust_update_interval()
        
        await self.async_request_refresh()
        _LOGGER.debug(f"[{self.device_name}] Configuration update completed - Auto mode: {current_auto_mode}")

    async def _load_outdoor_temp_history(self, days: int = 7) -> None:
        """Load outdoor temperature history."""
        _LOGGER.debug(f"[{self.device_name}] Loading outdoor temperature history for {days} days...")
        try:
            start_time = dt_util.now() - timedelta(days=days)
            entity_id = self.outdoor_temp_sensor_id
            if not entity_id:
                _LOGGER.debug(f"[{self.device_name}] No outdoor temperature sensor configured")
                return

            states = await recorder.get_instance(self.hass).async_add_executor_job(
                get_significant_states, self.hass, start_time, dt_util.now(), [entity_id]
            )
            
            outdoor_history = []
            for state in states.get(entity_id, []):
                try:
                    temp = float(state.state)
                    outdoor_history.append((state.last_updated, temp))
                except (ValueError, TypeError):
                    continue
                    
            self._outdoor_temp_history = outdoor_history
            self._running_mean_temp = self._calculate_exponential_running_mean(self._outdoor_temp_history)
            
            _LOGGER.debug(f"[{self.device_name}] Loaded {len(outdoor_history)} temperature records")
            _LOGGER.debug(f"[{self.device_name}] Running mean temperature: {self._running_mean_temp:.1f}°C" if self._running_mean_temp is not None else f"[{self.device_name}] Running mean temperature: None")
        except Exception as e:
            _LOGGER.error(f"[{self.device_name}] Failed to load outdoor temperature history: {e}")

    def _calculate_exponential_running_mean(self, history: List[Tuple[datetime, float]], alpha: float = 0.8) -> Optional[float]:
        """Calculate exponential running mean for temperature history."""
        if not history:
            _LOGGER.debug(f"[{self.device_name}] No temperature history available for running mean calculation")
            return None
            
        temps = sorted(history, key=lambda x: x[0])
        running_mean = None
        for _, temp in temps:
            if running_mean is None:
                running_mean = temp
            else:
                running_mean = (1 - alpha) * temp + alpha * running_mean
        
        _LOGGER.debug(f"[{self.device_name}] Calculated exponential running mean: {running_mean:.1f}°C (alpha={alpha})" if running_mean is not None else f"[{self.device_name}] Calculated exponential running mean: None (alpha={alpha})")
        return running_mean

    async def _call_service(self, domain: str, service: str, data: Dict[str, Any], context: Optional[Context] = None) -> None:
        """Call Home Assistant service with context."""
        _LOGGER.debug(f"[{self.device_name}] Calling service {domain}.{service} with data: {data}")
        await self.hass.services.async_call(domain, service, data, context=context)
        _LOGGER.debug(f"[{self.device_name}] Service {domain}.{service} called successfully")

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
        if entity_id not in self.climate_entities:
            return
        
        # Store the context for manual override detection (only for primary entity)
        context = event.context
        
        # Only detect manual override for the primary entity
        if entity_id == self.climate_entity_id:
            self._last_state_change_context = context
            
            # Check if this state change came from a manual user action
            if context and not str(context.id).startswith("adaptive_climate"):
                _LOGGER.debug(f"[{self.device_name}] Manual state change detected for primary entity {entity_id} - context: {context.id}")
                # This is likely a manual override - trigger immediate refresh
                self.hass.async_create_task(self.async_request_refresh())
            else:
                _LOGGER.debug(f"[{self.device_name}] System state change detected for primary entity {entity_id} - requesting refresh")
                self.hass.async_create_task(self.async_request_refresh())
        else:
            # For secondary entities, just log the change but don't trigger manual override detection
            _LOGGER.debug(f"[{self.device_name}] State change detected for secondary entity {entity_id} - requesting refresh")
            self.hass.async_create_task(self.async_request_refresh())

    async def set_manual_override(self, temperature: float, duration_seconds: Optional[int] = None) -> None:
        """Set manual override with specific temperature and duration."""
        _LOGGER.debug(f"[{self.device_name}] Setting manual override: {temperature}°C for {duration_seconds}s")
        
        # Disable auto mode
        self.config["auto_mode_enable"] = False
        
        # Calculate override temperature as offset from current comfort temperature
        # Get current comfort temperature to calculate the offset
        state = self.hass.states.get(self.climate_entity_id)
        if state and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            current_temp = state.attributes.get("temperature")
            if current_temp is not None:
                # Calculate offset from current temperature
                override_offset = temperature - current_temp
                self.config["override_temperature"] = override_offset
                _LOGGER.debug(f"[{self.device_name}] Calculated override offset: {override_offset}°C (from {current_temp}°C to {temperature}°C)")
            else:
                # Fallback: use temperature as absolute value
                self.config["override_temperature"] = temperature
                _LOGGER.debug(f"[{self.device_name}] Using temperature as absolute override: {temperature}°C")
        else:
            # No current state available, use temperature as absolute value
            self.config["override_temperature"] = temperature
            _LOGGER.debug(f"[{self.device_name}] No current state, using temperature as absolute override: {temperature}°C")
        
        # Store override end time if duration provided
        if duration_seconds:
            override_end = dt_util.now() + timedelta(seconds=duration_seconds)
            self.config["override_end_time"] = override_end.isoformat()
            _LOGGER.debug(f"[{self.device_name}] Override will end at: {override_end}")
        else:
            self.config.pop("override_end_time", None)
        
        # Apply the override immediately
        context = Context(parent_id=f"{self._context_prefix}_manual_override_{int(dt_util.utcnow().timestamp())}")
        await self.hass.services.async_call(
            CLIMATE_DOMAIN, "set_temperature", {
                "entity_id": self.climate_entity_id,
                "temperature": temperature,
            }, blocking=True, context=context
        )
        
        # Persist configuration
        await self._persist_data(params_only=True)
        
        duration_text = f" for {duration_seconds}s" if duration_seconds else ""
        _LOGGER.debug(f"[{self.device_name}] Manual override applied successfully")

    async def clear_manual_override(self) -> None:
        """Clear manual override and restore auto mode."""
        _LOGGER.debug(f"[{self.device_name}] Clearing manual override")
        
        # Remove override settings
        self.config.pop("override_temperature", None)
        self.config.pop("override_end_time", None)
        
        # Re-enable auto mode
        self.config["auto_mode_enable"] = True
        
        # Reset flags when clearing manual override
        self._override_logged = False
        self._auto_mode_logged = False
        
        # Persist configuration
        await self._persist_data(params_only=True)
        
        # Run control cycle to apply new settings
        await self.run_control_cycle()
        
        _LOGGER.debug(f"[{self.device_name}] Manual override cleared successfully")

    async def async_reset_override(self) -> None:
        """Reset override settings (alias for clear_manual_override)."""
        await self.clear_manual_override()

    async def update_comfort_category(self, category: str) -> None:
        """Update comfort category setting."""
        _LOGGER.debug(f"[{self.device_name}] Updating comfort category to: {category}")
        
        if category not in ["I", "II"]:
            _LOGGER.error(f"[{self.device_name}] Invalid comfort category: {category}")
            return
        
        self.config["comfort_category"] = category
        await self._persist_data(params_only=True)
        
        _LOGGER.debug(f"[{self.device_name}] Comfort category updated successfully")

    async def redetect_device_capabilities(self) -> Dict[str, bool]:
        """Force re-detection of device capabilities."""
        _LOGGER.info(f"[{self.device_name}] Forcing re-detection of device capabilities...")
        
        # Detect capabilities
        capabilities = self._detect_device_capabilities()
        
        # Update configuration with detected capabilities
        self._update_config_with_capabilities(capabilities)
        
        # Persist the updated configuration
        await self._persist_data(params_only=True)
        
        _LOGGER.info(f"[{self.device_name}] Device capabilities re-detection completed")
        return capabilities

    def get_device_capabilities(self) -> Dict[str, bool]:
        """Get current device capabilities."""
        return {
            "is_cool": self.config.get("enable_cool_mode", True),
            "is_heat": self.config.get("enable_heat_mode", True),
            "is_fan": self.config.get("enable_fan_mode", True),
            "is_dry": self.config.get("enable_dry_mode", True),
        }
