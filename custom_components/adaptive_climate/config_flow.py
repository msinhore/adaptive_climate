"""Config flow for Adaptive Climate integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers import area_registry

from .const import (
    DOMAIN,
    DEFAULT_COMFORT_CATEGORY,
    DEFAULT_MIN_COMFORT_TEMP,
    DEFAULT_MAX_COMFORT_TEMP,
    DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
    DEFAULT_AIR_VELOCITY,
    DEFAULT_NATURAL_VENTILATION_THRESHOLD,
    DEFAULT_SETBACK_TEMPERATURE_OFFSET,
    DEFAULT_PROLONGED_ABSENCE_MINUTES,
    DEFAULT_AUTO_SHUTDOWN_MINUTES,
    COMFORT_CATEGORIES,
)
from .area_helper import AreaBasedConfigHelper

_LOGGER = logging.getLogger(__name__)

# Enhanced logging for debugging entity selection issues
_LOGGER.setLevel(logging.DEBUG)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="Adaptive Climate"): str,
        vol.Optional("area"): selector.AreaSelector(),
        vol.Required("climate_entity"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="climate")
        ),
        vol.Required("indoor_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"]
            )
        ),
        vol.Required("outdoor_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"]
            )
        ),
        vol.Optional("comfort_category", default=DEFAULT_COMFORT_CATEGORY): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": "I", "label": f"Category I {COMFORT_CATEGORIES['I']['description']}"},
                    {"value": "II", "label": f"Category II {COMFORT_CATEGORIES['II']['description']}"},
                    {"value": "III", "label": f"Category III {COMFORT_CATEGORIES['III']['description']}"},
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)

STEP_ADVANCED_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional("occupancy_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="binary_sensor",
                device_class=["motion", "occupancy", "presence"],
            )
        ),
        vol.Optional("mean_radiant_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        vol.Optional("indoor_humidity_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        vol.Optional("outdoor_humidity_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"]
            )
        ),
        vol.Optional("use_operative_temperature", default=False): bool,
        vol.Optional("energy_save_mode", default=True): bool,
        vol.Optional("comfort_precision_mode", default=False): bool,
        vol.Optional("use_occupancy_features", default=False): bool,
        vol.Optional("natural_ventilation_enable", default=True): bool,
        vol.Optional("adaptive_air_velocity", default=True): bool,
        vol.Optional("humidity_comfort_enable", default=True): bool,
        vol.Optional("auto_shutdown_enable", default=False): bool,
    }
)

STEP_THRESHOLDS_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional("min_comfort_temp", default=DEFAULT_MIN_COMFORT_TEMP): vol.All(
            vol.Coerce(float), vol.Range(min=15.0, max=22.0)
        ),
        vol.Optional("max_comfort_temp", default=DEFAULT_MAX_COMFORT_TEMP): vol.All(
            vol.Coerce(float), vol.Range(min=25.0, max=32.0)
        ),
        vol.Optional("temperature_change_threshold", default=DEFAULT_TEMPERATURE_CHANGE_THRESHOLD): vol.All(
            vol.Coerce(float), vol.Range(min=0.5, max=2.0)
        ),
        vol.Optional("air_velocity", default=DEFAULT_AIR_VELOCITY): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=2.0)
        ),
        vol.Optional("natural_ventilation_threshold", default=DEFAULT_NATURAL_VENTILATION_THRESHOLD): vol.All(
            vol.Coerce(float), vol.Range(min=0.5, max=5.0)
        ),
        vol.Optional("setback_temperature_offset", default=DEFAULT_SETBACK_TEMPERATURE_OFFSET): vol.All(
            vol.Coerce(float), vol.Range(min=1.0, max=5.0)
        ),
        vol.Optional("prolonged_absence_minutes", default=DEFAULT_PROLONGED_ABSENCE_MINUTES): vol.All(
            vol.Coerce(int), vol.Range(min=10, max=240)
        ),
        vol.Optional("auto_shutdown_minutes", default=DEFAULT_AUTO_SHUTDOWN_MINUTES): vol.All(
            vol.Coerce(int), vol.Range(min=15, max=480)
        ),
    }
)

class AdaptiveClimateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Adaptive Climate."""

    VERSION = 1
    MINOR_VERSION = 0

    def __init__(self):
        """Initialize config flow."""
        self.config_data = {}
        self._reauth_entry = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        # Debug info about all entities in the registry
        entity_reg = async_get_entity_registry(self.hass)
        area_reg = area_registry.async_get(self.hass)

        # Log all areas in registry
        _LOGGER.debug("All areas in registry:")
        for area_id, area in area_reg.areas.items():
            _LOGGER.debug("Area: %s (ID: %s)", area.name, area_id)

        # Count entities by domain and area
        domain_counts = {}
        area_entity_counts = {}
        climate_entities_by_area = {}
        sensor_entities_by_area = {}
        
        # Debug log for all climate and sensor entities
        _LOGGER.debug("Examining all climate and sensor entities:")
        
        for entity_id, entity in entity_reg.entities.items():
            # Skip disabled entities
            if entity.disabled:
                continue
                
            # Count by domain
            domain = entity.domain
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
            # Count by area
            if entity.area_id:
                area_entity_counts[entity.area_id] = area_entity_counts.get(entity.area_id, 0) + 1
                
                # Track climate entities by area
                if domain == "climate":
                    if entity.area_id not in climate_entities_by_area:
                        climate_entities_by_area[entity.area_id] = []
                    climate_entities_by_area[entity.area_id].append(entity.entity_id)
                    _LOGGER.debug("Found climate entity: %s in area: %s", 
                                entity.entity_id, area_reg.async_get_area(entity.area_id).name)
                
                # Track sensor entities by area
                if domain == "sensor":
                    if entity.area_id not in sensor_entities_by_area:
                        sensor_entities_by_area[entity.area_id] = []
                    sensor_entities_by_area[entity.area_id].append(entity.entity_id)
                    state = self.hass.states.get(entity.entity_id)
                    if state:
                        unit = state.attributes.get("unit_of_measurement")
                        device_class = state.attributes.get("device_class")
                        _LOGGER.debug("Found sensor entity: %s in area: %s (unit: %s, device_class: %s)", 
                                   entity.entity_id, area_reg.async_get_area(entity.area_id).name,
                                   unit, device_class)
        
        _LOGGER.debug("Entity counts by domain: %s", domain_counts)
        _LOGGER.debug("Entity counts by area: %s", 
                     {area_reg.async_get_area(a_id).name: count 
                      for a_id, count in area_entity_counts.items()})
        
        # Build data schema with area filter if needed
        selected_area = None
        climate_entities = []
        indoor_temp_sensors = []
        
        if user_input is not None:
            selected_area = user_input.get("area")
            if selected_area:
                _LOGGER.debug("Selected area: %s", selected_area)
                area_helper = AreaBasedConfigHelper(self.hass)
                
                # Check direct area entity registry first
                _LOGGER.debug("Entities directly assigned to area %s:", selected_area)
                area_entities = []
                for entity_id, entity in entity_reg.entities.items():
                    if entity.area_id == selected_area and not entity.disabled:
                        area_entities.append(entity_id)
                _LOGGER.debug("Direct area entities: %s", area_entities)
                
                # Now use the helper method
                entities_by_type = area_helper.get_entities_by_type_in_area(selected_area)
                climate_entities = entities_by_type["climate"]
                indoor_temp_sensors = entities_by_type["temperature_sensors"]
                _LOGGER.debug("Climate entities in area from helper: %s", climate_entities)
                _LOGGER.debug("Temperature sensors in area from helper: %s", indoor_temp_sensors)
                
                # If no entities found but we know they exist, try to find them without area filtering
                if not climate_entities and selected_area in climate_entities_by_area:
                    _LOGGER.warning("Found climate entities in registry but not via helper: %s",
                                 climate_entities_by_area[selected_area])
                
                # Try to find all entities in the area regardless of our helper
                all_entities_in_area = []
                for entity in entity_reg.entities.values():
                    if entity.area_id == selected_area and not entity.disabled:
                        all_entities_in_area.append(entity.entity_id)
                
                _LOGGER.debug("All entities in selected area from registry: %s", all_entities_in_area)
        
        # Diagnóstico de problemas de áreas e entidades
        area_helper = AreaBasedConfigHelper(self.hass)
        issues = area_helper.diagnose_area_entity_issues()
        if issues:
            _LOGGER.warning(
                "Diagnóstico de problemas com áreas e entidades: %s. "
                "Isso pode causar problemas ao filtrar entidades por área.", 
                issues
            )
        
        # If we're still not finding entities in areas, try without area filtering
        if selected_area and not climate_entities:
            _LOGGER.warning("No climate entities found in area %s, showing all climate entities instead", selected_area)
            # Get all climate entities
            climate_entities = [e.entity_id for e in entity_reg.entities.values() 
                              if e.domain == "climate" and not e.disabled]
        
        if selected_area and not indoor_temp_sensors:
            _LOGGER.warning("No temperature sensors found in area %s, showing all temperature sensors instead", selected_area)
            # Get all potential temperature sensors
            temp_sensors = []
            for entity in entity_reg.entities.values():
                if entity.domain == "sensor" and not entity.disabled:
                    state = self.hass.states.get(entity.entity_id)
                    if state and (state.attributes.get("unit_of_measurement") in ["°C", "°F"] or 
                               state.attributes.get("device_class") == "temperature"):
                        temp_sensors.append(entity.entity_id)
            indoor_temp_sensors = temp_sensors
        
        # Create schema with optional area filter
        # Use empty list instead of None for include_entities
        # Home Assistant's API expects [] when no entities should be included, not None
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Adaptive Climate" if user_input is None else user_input.get(CONF_NAME, "Adaptive Climate")): str,
                vol.Optional("area", default=selected_area): selector.AreaSelector(),
                vol.Required("climate_entity", default="" if user_input is None else user_input.get("climate_entity", "")): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="climate",
                        # First try with include_entities if we have filtered entities
                        include_entities=climate_entities if climate_entities else [],
                        # If no filtered entities or filtering is causing issues, 
                        # don't set any other restrictions so all climate entities show
                    )
                ),
                vol.Required("indoor_temp_sensor", default="" if user_input is None else user_input.get("indoor_temp_sensor", "")): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number", "weather"],
                        # Add multiple ways to match temperature sensors
                        device_class=["temperature"],
                        # We've seen that include_entities can sometimes cause issues with
                        # empty dropdowns, so provide it only when we have entities to include
                        include_entities=indoor_temp_sensors if indoor_temp_sensors else []
                    )
                ),
                vol.Required("outdoor_temp_sensor", default="" if user_input is None else user_input.get("outdoor_temp_sensor", "")): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number", "weather"],
                        # Add device_class for outdoor temperature sensors too
                        device_class=["temperature", "weather"]
                    )
                ),
                vol.Optional("comfort_category", default=DEFAULT_COMFORT_CATEGORY if user_input is None else user_input.get("comfort_category", DEFAULT_COMFORT_CATEGORY)): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "I", "label": f"Category I {COMFORT_CATEGORIES['I']['description']}"},
                            {"value": "II", "label": f"Category II {COMFORT_CATEGORIES['II']['description']}"},
                            {"value": "III", "label": f"Category III {COMFORT_CATEGORIES['III']['description']}"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=schema)

        errors = {}

        # Validate that entities exist
        registry = async_get_entity_registry(self.hass)
        for field in ["climate_entity", "indoor_temp_sensor", "outdoor_temp_sensor"]:
            entity_id = user_input[field]
            if not registry.async_is_registered(entity_id):
                if entity_id not in self.hass.states.async_entity_ids():
                    errors[field] = "entity_not_found"

        if errors:
            return self.async_show_form(
                step_id="user", data_schema=schema, errors=errors
            )

        # Store selected area in config data if provided
        if selected_area:
            self.config_data["area"] = selected_area
            
        # Update config data with all user inputs
        self.config_data.update(user_input)
        return await self.async_step_advanced()

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle advanced options step.""" 
        if user_input is None:
            # Create dynamic schema based on selected area
            selected_area = self.config_data.get("area")
            
            # Get entities for the selected area if applicable
            occupancy_sensors = []
            temperature_sensors = []
            humidity_sensors = []
            
            if selected_area:
                _LOGGER.debug("Filtering advanced entities for area: %s", selected_area)
                area_helper = AreaBasedConfigHelper(self.hass)
                
                # Get all entities by type in this area
                entities_by_type = area_helper.get_entities_by_type_in_area(selected_area)
                
                # Get the specific entity types we need
                occupancy_sensors = entities_by_type["occupancy_sensors"]
                temperature_sensors = entities_by_type["temperature_sensors"]
                humidity_sensors = entities_by_type["humidity_sensors"]
                
                _LOGGER.debug("Found occupancy sensors: %s", occupancy_sensors)
                _LOGGER.debug("Found temperature sensors: %s", temperature_sensors)
                _LOGGER.debug("Found humidity sensors: %s", humidity_sensors)
                
                # Verificar se há entidades encontradas na área selecionada, mas sempre aplicar o filtro
                # com lista vazia caso não tenha entidades para evitar "No matching entities found"
                has_occupancy_in_area = len(occupancy_sensors) > 0
                has_temperature_in_area = len(temperature_sensors) > 0
                has_humidity_in_area = len(humidity_sensors) > 0
                
                _LOGGER.debug("Has occupancy sensors in area: %s", has_occupancy_in_area)
                _LOGGER.debug("Has temperature sensors in area: %s", has_temperature_in_area)
                _LOGGER.debug("Has humidity sensors in area: %s", has_humidity_in_area)
            
            advanced_schema = vol.Schema(
                {
                    vol.Optional("occupancy_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="binary_sensor",
                            device_class=["motion", "occupancy", "presence"],
                            include_entities=occupancy_sensors if has_occupancy_in_area else []
                        )
                    ),
                    vol.Optional("mean_radiant_temp_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor", "input_number"],
                            include_entities=temperature_sensors if has_temperature_in_area else []
                        )
                    ),
                    vol.Optional("indoor_humidity_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor", "input_number"],
                            include_entities=humidity_sensors if has_humidity_in_area else []
                        )
                    ),
                    vol.Optional("outdoor_humidity_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor", "input_number", "weather"]
                        )
                    ),
                    vol.Optional("use_operative_temperature", default=False): bool,
                    vol.Optional("energy_save_mode", default=True): bool,
                    vol.Optional("comfort_precision_mode", default=False): bool,
                    vol.Optional("use_occupancy_features", default=False): bool,
                    vol.Optional("natural_ventilation_enable", default=True): bool,
                    vol.Optional("adaptive_air_velocity", default=True): bool,
                    vol.Optional("humidity_comfort_enable", default=True): bool,
                    vol.Optional("auto_shutdown_enable", default=False): bool,
                }
            )
            
            return self.async_show_form(
                step_id="advanced", data_schema=advanced_schema
            )

        self.config_data.update(user_input)
        return await self.async_step_thresholds()

    async def async_step_thresholds(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle thresholds configuration step."""
        if user_input is None:
            return self.async_show_form(
                step_id="thresholds", data_schema=STEP_THRESHOLDS_DATA_SCHEMA
            )

        self.config_data.update(user_input)

        # Check if entry already exists
        await self.async_set_unique_id(self.config_data[CONF_NAME])
        self._abort_if_unique_id_configured()

        # Log area configuration if present
        if "area" in self.config_data:
            _LOGGER.debug("Saving area '%s' in configuration for %s", 
                         self.config_data["area"], self.config_data[CONF_NAME])

        return self.async_create_entry(
            title=self.config_data[CONF_NAME], data=self.config_data
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Adaptive Climate."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle unified configuration panel with modern UI components."""
        if user_input is not None:
            # Handle reset actions first
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
            
            if user_input.get("reset_outdoor_history", False):
                await coordinator.reset_outdoor_history()
                # Remove reset flag before saving
                user_input = {k: v for k, v in user_input.items() if k != "reset_outdoor_history"}
            
            if user_input.get("reset_to_defaults", False):
                # Reset to default values, mas apenas para valores que não são gerenciados pelos number helpers
                default_config = {
                    "comfort_category": DEFAULT_COMFORT_CATEGORY,
                    # Removidos os campos numéricos que são gerenciados pelos number helpers:
                    # "air_velocity", "temperature_change_threshold", "natural_ventilation_threshold",
                    # "setback_temperature_offset", "min_comfort_temp", "max_comfort_temp",
                    # "prolonged_absence_minutes", "auto_shutdown_minutes"
                    "adaptive_air_velocity": True,
                    "natural_ventilation_enable": True,
                    "humidity_comfort_enable": True,
                    "comfort_precision_mode": False,
                    "use_occupancy_features": False,
                    "auto_shutdown_enable": False,
                    "energy_save_mode": True,
                    "use_operative_temperature": False,
                }
                await coordinator.update_config(default_config)
                return self.async_create_entry(title="", data=default_config)
            
            # Filter out reset actions and None values
            config_update = {
                k: v for k, v in user_input.items() 
                if not k.startswith("reset_") and v is not None
            }
            
            # Remover campos numéricos que são gerenciados exclusivamente pelos number helpers
            number_fields = [
                "min_comfort_temp", "max_comfort_temp", "temperature_change_threshold", 
                "air_velocity", "natural_ventilation_threshold", "setback_temperature_offset", 
                "prolonged_absence_minutes", "auto_shutdown_minutes"
            ]
            config_update = {k: v for k, v in config_update.items() if k not in number_fields}
            
            if config_update:
                # Log area changes if present
                if "area" in config_update:
                    _LOGGER.debug("Updating area to '%s' in configuration", config_update["area"])
                
                # Update coordinator with new configuration
                await coordinator.update_config(config_update)
                
                # Merge with existing options and data for entities
                new_options = {**self.config_entry.options, **config_update}
                
                # Update config entry data if entity selections or area changed
                entity_keys = ["climate_entity", "indoor_temp_sensor", "outdoor_temp_sensor", 
                              "occupancy_sensor", "mean_radiant_temp_sensor", 
                              "indoor_humidity_sensor", "outdoor_humidity_sensor", "area"]
                
                entity_updates = {k: v for k, v in config_update.items() if k in entity_keys}
                if entity_updates:
                    # Update the config entry data as well
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, 
                        data={**self.config_entry.data, **entity_updates}
                    )
                
                return self.async_create_entry(title="", data=new_options)
            
            return self.async_create_entry(title="", data=self.config_entry.options)

        # Get current values from coordinator and config entry
        try:
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
            current_config = coordinator.config
        except KeyError:
            # Fallback if coordinator not available
            current_config = {**self.config_entry.data, **self.config_entry.options}
        
        current_data = self.config_entry.data

        # Get entities for the selected area if applicable
        selected_area = current_data.get("area")
        climate_entities = []
        indoor_temp_sensors = []
        outdoor_temp_sensors = []
        occupancy_sensors = []
        mean_radiant_temp_sensors = []
        indoor_humidity_sensors = []
        outdoor_humidity_sensors = []
        
        # Inicializar área helper
        area_helper = AreaBasedConfigHelper(self.hass)
        
        # Diagnóstico de problemas de áreas e entidades
        issues = area_helper.diagnose_area_entity_issues()
        if issues:
            _LOGGER.warning(
                "Diagnóstico de problemas com áreas e entidades: %s. "
                "Isso pode causar problemas ao filtrar entidades por área.", 
                issues
            )
            
        if selected_area:
            _LOGGER.debug("Filtering options entities for area: %s", selected_area)
            
            # Get all entities by type in this area using our improved helper
            entities_by_type = area_helper.get_entities_by_type_in_area(selected_area)
            
            # Get the entities we need for each selector
            climate_entities = entities_by_type["climate"]
            indoor_temp_sensors = entities_by_type["temperature_sensors"]
            mean_radiant_temp_sensors = entities_by_type["temperature_sensors"]  # Same as temperature sensors
            indoor_humidity_sensors = entities_by_type["humidity_sensors"]
            occupancy_sensors = entities_by_type["occupancy_sensors"]
            
            _LOGGER.debug("Found climate entities: %s", climate_entities)
            _LOGGER.debug("Found temperature sensors: %s", indoor_temp_sensors)
            _LOGGER.debug("Found humidity sensors: %s", indoor_humidity_sensors)
            _LOGGER.debug("Found occupancy sensors: %s", occupancy_sensors)
        
        # Verificar se há entidades encontradas na área selecionada, mas sempre aplicar o filtro
        # com lista vazia caso não tenha entidades para evitar "No matching entities found"
        has_climate_in_area = len(climate_entities) > 0
        has_temp_sensors_in_area = len(indoor_temp_sensors) > 0
        has_mean_radiant_temp_in_area = len(mean_radiant_temp_sensors) > 0
        has_humidity_in_area = len(indoor_humidity_sensors) > 0
        has_occupancy_in_area = len(occupancy_sensors) > 0
        
        _LOGGER.debug("Has climate entities in area: %s", has_climate_in_area)
        _LOGGER.debug("Has temperature sensors in area: %s", has_temp_sensors_in_area)
        _LOGGER.debug("Has humidity sensors in area: %s", has_humidity_in_area)
        _LOGGER.debug("Has occupancy sensors in area: %s", has_occupancy_in_area)

        # Create unified configuration schema with modern selectors
        unified_schema = vol.Schema({
            # === FEATURE TOGGLES (Using BooleanSelector for modern toggle switches) ===
            vol.Optional(
                "energy_save_mode",
                default=current_config.get("energy_save_mode", True)
            ): selector.BooleanSelector(),
            
            vol.Optional(
                "natural_ventilation_enable",
                default=current_config.get("natural_ventilation_enable", True)
            ): selector.BooleanSelector(),
            
            vol.Optional(
                "adaptive_air_velocity",
                default=current_config.get("adaptive_air_velocity", True)
            ): selector.BooleanSelector(),
            
            vol.Optional(
                "humidity_comfort_enable",
                default=current_config.get("humidity_comfort_enable", True)
            ): selector.BooleanSelector(),
            
            vol.Optional(
                "comfort_precision_mode",
                default=current_config.get("comfort_precision_mode", False)
            ): selector.BooleanSelector(),
            
            vol.Optional(
                "use_occupancy_features",
                default=current_config.get("use_occupancy_features", False)
            ): selector.BooleanSelector(),
            
            vol.Optional(
                "auto_shutdown_enable",
                default=current_config.get("auto_shutdown_enable", False)
            ): selector.BooleanSelector(),
            
            vol.Optional(
                "use_operative_temperature",
                default=current_config.get("use_operative_temperature", False)
            ): selector.BooleanSelector(            ),
            
            # === AREA SELECTOR (if previously configured) ===
            vol.Optional(
                "area",
                default=current_data.get("area")
            ): selector.AreaSelector(),

            # === COMFORT CATEGORY DROPDOWN ===
            vol.Optional(
                "comfort_category", 
                default=current_config.get("comfort_category", DEFAULT_COMFORT_CATEGORY)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "I", "label": f"Category I - {COMFORT_CATEGORIES['I']['description']}"},
                        {"value": "II", "label": f"Category II - {COMFORT_CATEGORIES['II']['description']}"},
                        {"value": "III", "label": f"Category III - {COMFORT_CATEGORIES['III']['description']}"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),

            # === ENTITY SELECTORS ===
            vol.Optional(
                "climate_entity",
                default=current_data.get("climate_entity")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="climate",
                    include_entities=climate_entities if climate_entities else []
                )
            ),

            vol.Optional(
                "indoor_temp_sensor",
                default=current_data.get("indoor_temp_sensor")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor", "input_number", "weather"],
                    include_entities=indoor_temp_sensors if indoor_temp_sensors else []
                )
            ),

            vol.Optional(
                "outdoor_temp_sensor", 
                default=current_data.get("outdoor_temp_sensor")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor", "input_number", "weather"]
                )
            ),

            vol.Optional(
                "occupancy_sensor",
                default=current_data.get("occupancy_sensor")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="binary_sensor",
                    device_class=["motion", "occupancy", "presence"],
                    include_entities=occupancy_sensors if occupancy_sensors else []
                )
            ),

            vol.Optional(
                "mean_radiant_temp_sensor",
                default=current_data.get("mean_radiant_temp_sensor")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    include_entities=mean_radiant_temp_sensors if mean_radiant_temp_sensors else []
                )
            ),

            vol.Optional(
                "indoor_humidity_sensor",
                default=current_data.get("indoor_humidity_sensor")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    include_entities=indoor_humidity_sensors if indoor_humidity_sensors else []
                )
            ),

            vol.Optional(
                "outdoor_humidity_sensor",
                default=current_data.get("outdoor_humidity_sensor")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor", "input_number", "weather"]
                )
            ),

            # === RESET ACTIONS ===
            vol.Optional("reset_outdoor_history", default=False): selector.BooleanSelector(),
            vol.Optional("reset_to_defaults", default=False): selector.BooleanSelector(),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=unified_schema,
            description_placeholders={
                "warning": "Reset operations cannot be undone!"
            }
        )


