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

# Options Schema for post-configuration changes
OPTIONS_SCHEMA = vol.Schema(
    {
        # Comfort Settings
        vol.Optional("comfort_category"): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": "I", "label": "Category I - High Standard"},
                    {"value": "II", "label": "Category II - Normal Standard"},
                    {"value": "III", "label": "Category III - Acceptable Standard"},
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        
        # Temperature Settings
        vol.Optional("min_comfort_temp"): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=15.0,
                max=22.0,
                step=0.1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="°C"
            )
        ),
        vol.Optional("max_comfort_temp"): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=25.0,
                max=32.0,
                step=0.1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="°C"
            )
        ),
        vol.Optional("temperature_change_threshold"): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.1,
                max=3.0,
                step=0.1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="°C"
            )
        ),
        
        # Environmental Settings
        vol.Optional("air_velocity"): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.0,
                max=2.0,
                step=0.1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="m/s"
            )
        ),
        vol.Optional("natural_ventilation_threshold"): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.5,
                max=5.0,
                step=0.1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="°C"
            )
        ),
        
        # Setback Settings
        vol.Optional("setback_temperature_offset"): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1.0,
                max=5.0,
                step=0.1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="°C"
            )
        ),
        vol.Optional("prolonged_absence_minutes"): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=10,
                max=240,
                step=1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="min"
            )
        ),
        vol.Optional("auto_shutdown_minutes"): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=15,
                max=480,
                step=1,
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="min"
            )
        ),
        
        # Feature Toggles
        vol.Optional("use_operative_temperature"): selector.BooleanSelector(),
        vol.Optional("energy_save_mode"): selector.BooleanSelector(),
        vol.Optional("comfort_precision_mode"): selector.BooleanSelector(),
        vol.Optional("use_occupancy_features"): selector.BooleanSelector(),
        vol.Optional("natural_ventilation_enable"): selector.BooleanSelector(),
        vol.Optional("adaptive_air_velocity"): selector.BooleanSelector(),
        vol.Optional("humidity_comfort_enable"): selector.BooleanSelector(),
        vol.Optional("auto_shutdown_enable"): selector.BooleanSelector(),
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
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return OptionsFlowHandler(config_entry)

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


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an option flow for Adaptive Climate."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate temperature ranges
            min_temp = user_input.get("min_comfort_temp")
            max_temp = user_input.get("max_comfort_temp")
            
            if min_temp is not None and max_temp is not None and min_temp >= max_temp:
                errors["min_comfort_temp"] = "min_greater_than_max"
                errors["max_comfort_temp"] = "min_greater_than_max"

            # Validate time values
            prolonged_absence = user_input.get("prolonged_absence_minutes")
            auto_shutdown = user_input.get("auto_shutdown_minutes")
            
            if prolonged_absence is not None and auto_shutdown is not None:
                if prolonged_absence >= auto_shutdown:
                    errors["prolonged_absence_minutes"] = "invalid_time_sequence"
                    errors["auto_shutdown_minutes"] = "invalid_time_sequence"

            # Additional validation for air velocity when adaptive is enabled
            air_velocity = user_input.get("air_velocity")
            adaptive_air_velocity = user_input.get("adaptive_air_velocity", False)
            
            if adaptive_air_velocity and air_velocity is not None and air_velocity > 1.5:
                errors["air_velocity"] = "high_air_velocity_warning"

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA,
                self.config_entry.options
            ),
            errors=errors,
        )