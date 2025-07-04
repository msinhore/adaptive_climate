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

from .const import (
    DOMAIN,
    DEFAULT_COMFORT_CATEGORY,
    COMFORT_CATEGORIES,
    DEFAULT_MIN_COMFORT_TEMP,
    DEFAULT_MAX_COMFORT_TEMP,
    DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
    DEFAULT_AIR_VELOCITY,
    DEFAULT_NATURAL_VENTILATION_THRESHOLD,
    DEFAULT_SETBACK_TEMPERATURE_OFFSET,
    DEFAULT_PROLONGED_ABSENCE_MINUTES,
    DEFAULT_AUTO_SHUTDOWN_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

# Config Schema for initial setup - only essential entities
CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="Adaptive Climate"): str,
        vol.Required("climate_entity"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="climate")
        ),
        vol.Required("indoor_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"],
                device_class=["temperature"]
            )
        ),
        vol.Required("outdoor_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"],
                device_class=["temperature", "weather"]
            )
        ),
        vol.Optional("comfort_category", default=DEFAULT_COMFORT_CATEGORY): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": "I", "label": f"Category I - {COMFORT_CATEGORIES['I']['description']}"},
                    {"value": "II", "label": f"Category II - {COMFORT_CATEGORIES['II']['description']}"},
                    {"value": "III", "label": f"Category III - {COMFORT_CATEGORIES['III']['description']}"},
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)

# Optional sensors schema for second step
OPTIONAL_SENSORS_SCHEMA = vol.Schema(
    {
        vol.Optional("occupancy_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="binary_sensor",
                device_class=["motion", "occupancy", "presence"]
            )
        ),
        vol.Optional("mean_radiant_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number"],
                device_class=["temperature"]
            )
        ),
        vol.Optional("indoor_humidity_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number"],
                device_class=["humidity"]
            )
        ),
        vol.Optional("outdoor_humidity_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"],
                device_class=["humidity"]
            )
        ),
    }
)

# Configuration parameters schema for third step
CONFIGURATION_SCHEMA = vol.Schema(
    {
        # Temperature Limits
        vol.Optional("min_comfort_temp", default=DEFAULT_MIN_COMFORT_TEMP): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=10, max=30, step=0.5, unit_of_measurement="°C",
                mode=selector.NumberSelectorMode.SLIDER
            )
        ),
        vol.Optional("max_comfort_temp", default=DEFAULT_MAX_COMFORT_TEMP): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=20, max=40, step=0.5, unit_of_measurement="°C",
                mode=selector.NumberSelectorMode.SLIDER
            )
        ),
        vol.Optional("temperature_change_threshold", default=DEFAULT_TEMPERATURE_CHANGE_THRESHOLD): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.1, max=5.0, step=0.1, unit_of_measurement="°C",
                mode=selector.NumberSelectorMode.BOX
            )
        ),
        
        # Air Velocity & Natural Ventilation
        vol.Optional("air_velocity", default=DEFAULT_AIR_VELOCITY): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.0, max=2.0, step=0.1, unit_of_measurement="m/s",
                mode=selector.NumberSelectorMode.SLIDER
            )
        ),
        vol.Optional("adaptive_air_velocity", default=False): selector.BooleanSelector(),
        vol.Optional("natural_ventilation_enable", default=True): selector.BooleanSelector(),
        vol.Optional("natural_ventilation_threshold", default=DEFAULT_NATURAL_VENTILATION_THRESHOLD): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.5, max=10.0, step=0.5, unit_of_measurement="°C",
                mode=selector.NumberSelectorMode.SLIDER
            )
        ),
        
        # Occupancy & Energy Settings
        vol.Optional("use_occupancy_features", default=True): selector.BooleanSelector(),
        vol.Optional("energy_save_mode", default=True): selector.BooleanSelector(),
        vol.Optional("setback_temperature_offset", default=DEFAULT_SETBACK_TEMPERATURE_OFFSET): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=-5.0, max=5.0, step=0.5, unit_of_measurement="°C",
                mode=selector.NumberSelectorMode.SLIDER
            )
        ),
        vol.Optional("prolonged_absence_minutes", default=DEFAULT_PROLONGED_ABSENCE_MINUTES): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=5, max=480, step=5, unit_of_measurement="min",
                mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Optional("auto_shutdown_enable", default=False): selector.BooleanSelector(),
        vol.Optional("auto_shutdown_minutes", default=DEFAULT_AUTO_SHUTDOWN_MINUTES): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=30, max=1440, step=30, unit_of_measurement="min",
                mode=selector.NumberSelectorMode.BOX
            )
        ),
        
        # Advanced Settings
        vol.Optional("comfort_precision_mode", default=False): selector.BooleanSelector(),
        vol.Optional("use_operative_temperature", default=False): selector.BooleanSelector(),
        vol.Optional("humidity_comfort_enable", default=True): selector.BooleanSelector(),
    }
)


class AdaptiveClimateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Adaptive Climate."""

    VERSION = 1
    MINOR_VERSION = 0

    def __init__(self):
        """Initialize config flow."""
        self.config_data = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow for reconfiguration."""
        return AdaptiveClimateOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=CONFIG_SCHEMA)

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
                step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
            )

        # Update config data with user inputs
        self.config_data.update(user_input)
        return await self.async_step_optional_sensors()

    async def async_step_optional_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle optional sensors step."""
        if user_input is None:
            return self.async_show_form(
                step_id="optional_sensors", 
                data_schema=OPTIONAL_SENSORS_SCHEMA
            )

        # Update config data with optional sensors
        self.config_data.update(user_input)
        return await self.async_step_configuration()

    async def async_step_configuration(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle configuration parameters step."""
        if user_input is None:
            return self.async_show_form(
                step_id="configuration", 
                data_schema=CONFIGURATION_SCHEMA,
                description_placeholders={
                    "device_name": self.config_data.get(CONF_NAME, "Adaptive Climate")
                }
            )

        # Update config data with configuration parameters
        self.config_data.update(user_input)

        # Create unique ID based on climate entity to prevent duplicates
        unique_id = f"adaptive_climate_{self.config_data['climate_entity'].replace('.', '_')}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(
            updates={CONF_NAME: self.config_data[CONF_NAME]}
        )

        # Create dynamic title based on climate entity
        climate_entity = self.config_data["climate_entity"]
        climate_state = self.hass.states.get(climate_entity)
        
        if climate_state and hasattr(climate_state, 'attributes'):
            friendly_name = climate_state.attributes.get("friendly_name", "")
            if friendly_name:
                title = f"Adaptive Climate - {friendly_name}"
            else:
                title = f"Adaptive Climate - {climate_entity.split('.')[-1].replace('_', ' ').title()}"
        else:
            title = self.config_data[CONF_NAME]

        return self.async_create_entry(title=title, data=self.config_data)


class AdaptiveClimateOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Adaptive Climate reconfiguration."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options - main menu."""
        if user_input is not None:
            if user_input.get("section") == "controls":
                return await self.async_step_controls()
            elif user_input.get("section") == "configuration":
                return await self.async_step_configuration()
            elif user_input.get("section") == "diagnostics":
                return await self.async_step_diagnostics()
            else:
                return await self.async_step_entities()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("section", default="controls"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "controls", "label": "Controls (Main Settings)"},
                            {"value": "configuration", "label": "Configuration (Advanced)"},
                            {"value": "diagnostics", "label": "Diagnostics (View Only)"},
                            {"value": "entities", "label": "Entity Configuration"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }),
            description_placeholders={
                "name": self.config_entry.data.get(CONF_NAME, "Adaptive Climate"),
            },
        )

    async def async_step_controls(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle Controls configuration step."""
        errors = {}
        
        if user_input is not None:
            # Validate that min < max
            if user_input["min_comfort_temp"] >= user_input["max_comfort_temp"]:
                errors["base"] = "min_temp_greater_than_max"
            else:
                # Update config entry
                new_data = {**self.config_entry.data, **user_input}
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data
                )
                return self.async_create_entry(title="", data={})

        # Get current values with defaults
        current_data = self.config_entry.data
        
        return self.async_show_form(
            step_id="controls",
            data_schema=vol.Schema({
                vol.Required(
                    "comfort_category", 
                    default=current_data.get("comfort_category", DEFAULT_COMFORT_CATEGORY)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": "I", "label": "Category I (±2°C - High expectation)"},
                            {"value": "II", "label": "Category II (±3°C - Normal expectation)"},
                            {"value": "III", "label": "Category III (±4°C - Moderate expectation)"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    "min_comfort_temp", 
                    default=current_data.get("min_comfort_temp", DEFAULT_MIN_COMFORT_TEMP)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=10, max=30, step=0.5, unit_of_measurement="°C",
                        mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
                vol.Required(
                    "max_comfort_temp", 
                    default=current_data.get("max_comfort_temp", DEFAULT_MAX_COMFORT_TEMP)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=20, max=40, step=0.5, unit_of_measurement="°C",
                        mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
            }),
            errors=errors,
            description_placeholders={
                "name": self.config_entry.data.get(CONF_NAME, "Adaptive Climate"),
            },
        )

    async def async_step_configuration(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle Configuration (Advanced) step."""
        if user_input is not None:
            # Update config entry
            new_data = {**self.config_entry.data, **user_input}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            return self.async_create_entry(title="", data={})

        # Get current values with defaults
        current_data = self.config_entry.data
        
        return self.async_show_form(
            step_id="configuration",
            data_schema=vol.Schema({
                # Basic toggles
                vol.Optional(
                    "use_operative_temperature", 
                    default=current_data.get("use_operative_temperature", False)
                ): selector.BooleanSelector(),
                vol.Optional(
                    "energy_save_mode", 
                    default=current_data.get("energy_save_mode", True)
                ): selector.BooleanSelector(),
                
                # Comfort precision mode and sub-settings
                vol.Optional(
                    "comfort_precision_mode", 
                    default=current_data.get("comfort_precision_mode", False)
                ): selector.BooleanSelector(),
                vol.Optional(
                    "temperature_change_threshold", 
                    default=current_data.get("temperature_change_threshold", DEFAULT_TEMPERATURE_CHANGE_THRESHOLD)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.1, max=5.0, step=0.1, unit_of_measurement="°C",
                        mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    "comfort_temp_min_offset", 
                    default=current_data.get("comfort_range_min_offset", DEFAULT_COMFORT_TEMP_MIN_OFFSET)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-5.0, max=5.0, step=0.5, unit_of_measurement="°C",
                        mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
                vol.Optional(
                    "comfort_temp_max_offset", 
                    default=current_data.get("comfort_range_max_offset", DEFAULT_COMFORT_TEMP_MAX_OFFSET)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-5.0, max=5.0, step=0.5, unit_of_measurement="°C",
                        mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
                
                # Adaptive air velocity and sub-settings
                vol.Optional(
                    "adaptive_air_velocity", 
                    default=current_data.get("adaptive_air_velocity", False)
                ): selector.BooleanSelector(),
                vol.Optional(
                    "air_velocity", 
                    default=current_data.get("air_velocity", DEFAULT_AIR_VELOCITY)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0, max=2.0, step=0.1, unit_of_measurement="m/s",
                        mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
                
                # Natural ventilation and sub-settings
                vol.Optional(
                    "natural_ventilation_enable", 
                    default=current_data.get("natural_ventilation_enable", True)
                ): selector.BooleanSelector(),
                vol.Optional(
                    "natural_ventilation_threshold", 
                    default=current_data.get("natural_ventilation_threshold", DEFAULT_NATURAL_VENTILATION_THRESHOLD)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.5, max=10.0, step=0.5, unit_of_measurement="°C",
                        mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
                
                # Setback
                vol.Optional(
                    "setback_temperature_offset", 
                    default=current_data.get("setback_temperature_offset", DEFAULT_SETBACK_TEMPERATURE_OFFSET)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-5.0, max=5.0, step=0.5, unit_of_measurement="°C",
                        mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
                
                # Occupancy features
                vol.Optional(
                    "use_occupancy_features", 
                    default=current_data.get("use_occupancy_features", True)
                ): selector.BooleanSelector(),
                
                # Auto shutdown and sub-settings
                vol.Optional(
                    "auto_shutdown_enable", 
                    default=current_data.get("auto_shutdown_enable", False)
                ): selector.BooleanSelector(),
                vol.Optional(
                    "prolonged_absence_minutes", 
                    default=current_data.get("prolonged_absence_minutes", DEFAULT_PROLONGED_ABSENCE_MINUTES)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5, max=480, step=5, unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    "auto_shutdown_minutes", 
                    default=current_data.get("auto_shutdown_minutes", DEFAULT_AUTO_SHUTDOWN_MINUTES)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=30, max=1440, step=30, unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX
                    )
                ),
                
                # Humidity comfort
                vol.Optional(
                    "humidity_comfort_enable", 
                    default=current_data.get("humidity_comfort_enable", True)
                ): selector.BooleanSelector(),
            }),
            description_placeholders={
                "name": self.config_entry.data.get(CONF_NAME, "Adaptive Climate"),
            },
        )

    async def async_step_diagnostics(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show diagnostics (read-only information)."""
        if user_input is not None:
            return self.async_create_entry(title="", data={})

        # Get coordinator data to show current diagnostics
        try:
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
            data = coordinator.data or {}
            
            # Format diagnostics information
            diagnostics_info = f"""Current Status:
• Compliance: {data.get('compliance_calculation', 'N/A')}
• Occupancy: {data.get('occupancy', 'N/A')}
• Natural Ventilation: {'Active' if data.get('natural_ventilation_active', False) else 'Inactive'}

Measurements:
• Indoor Temperature: {data.get('indoor_temperature', 'N/A')}°C
• Outdoor Temperature: {data.get('outdoor_temperature', 'N/A')}°C
• Outdoor Running Mean: {data.get('outdoor_running_mean', 0):.1f}°C

ASHRAE Calculations:
• Adaptive Comfort Temp: {data.get('adaptive_comfort_temp', 'N/A')}°C
• Comfort Range: {data.get('comfort_temp_min', 'N/A')}°C - {data.get('comfort_temp_max', 'N/A')}°C
• Effective Range: {data.get('effective_comfort_min', 'N/A')}°C - {data.get('effective_comfort_max', 'N/A')}°C"""
        
        except Exception:
            diagnostics_info = "Unable to load diagnostic information. Please ensure the integration is running properly."

        return self.async_show_form(
            step_id="diagnostics",
            data_schema=vol.Schema({}),
            description_placeholders={
                "name": self.config_entry.data.get(CONF_NAME, "Adaptive Climate"),
                "diagnostics": diagnostics_info,
            },
        )

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle entity configuration step."""
        errors = {}
        
        if user_input is not None:
            # Validate that required entities exist
            registry = async_get_entity_registry(self.hass)
            for field in ["climate_entity", "indoor_temp_sensor", "outdoor_temp_sensor"]:
                entity_id = user_input.get(field)
                if entity_id and not registry.async_is_registered(entity_id):
                    if entity_id not in self.hass.states.async_entity_ids():
                        errors[field] = "entity_not_found"
            
            if not errors:
                # Clean up empty optional fields
                cleaned_data = {k: v for k, v in user_input.items() if v}
                
                # Update config entry
                new_data = {**self.config_entry.data, **cleaned_data}
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data
                )
                return self.async_create_entry(title="", data={})

        # Get current values
        current_data = self.config_entry.data
        
        return self.async_show_form(
            step_id="entities",
            data_schema=vol.Schema({
                vol.Required(
                    "climate_entity", 
                    default=current_data.get("climate_entity", "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="climate")
                ),
                vol.Required(
                    "indoor_temp_sensor", 
                    default=current_data.get("indoor_temp_sensor", "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number", "weather"],
                        device_class=["temperature"]
                    )
                ),
                vol.Required(
                    "outdoor_temp_sensor", 
                    default=current_data.get("outdoor_temp_sensor", "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number", "weather"],
                        device_class=["temperature", "weather"]
                    )
                ),
                vol.Optional(
                    "occupancy_sensor", 
                    default=current_data.get("occupancy_sensor", "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["binary_sensor", "input_boolean"],
                        device_class=["occupancy", "motion", "presence"]
                    )
                ),
                vol.Optional(
                    "indoor_humidity_sensor", 
                    default=current_data.get("indoor_humidity_sensor", "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number"],
                        device_class=["humidity"]
                    )
                ),
                vol.Optional(
                    "mean_radiant_temp_sensor", 
                    default=current_data.get("mean_radiant_temp_sensor", "")
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number"],
                        device_class=["temperature"]
                    )
                ),
            }),
            errors=errors,
            description_placeholders={
                "name": self.config_entry.data.get(CONF_NAME, "Adaptive Climate"),
            },
        )