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

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration flow."""
        # Check if we have backup data
        previous_entry_id = self.context.get("previous_entry_id")
        if previous_entry_id and "adaptive_climate_backup" in self.hass.data:
            backup_data = self.hass.data["adaptive_climate_backup"].get(previous_entry_id)
            if backup_data:
                # Pre-populate with backup data
                self.config_data = backup_data["data"].copy()
        
        if user_input is None:
            # Create schema with previous values as defaults if available
            schema = vol.Schema(
                {
                    vol.Required(CONF_NAME, default=self.config_data.get(CONF_NAME, "Adaptive Climate")): str,
                    vol.Required("climate_entity", default=self.config_data.get("climate_entity", "")): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="climate")
                    ),
                    vol.Required("indoor_temp_sensor", default=self.config_data.get("indoor_temp_sensor", "")): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor", "input_number", "weather"],
                            device_class=["temperature"]
                        )
                    ),
                    vol.Required("outdoor_temp_sensor", default=self.config_data.get("outdoor_temp_sensor", "")): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor", "input_number", "weather"],
                            device_class=["temperature", "weather"]
                        )
                    ),
                    vol.Optional("comfort_category", default=self.config_data.get("comfort_category", DEFAULT_COMFORT_CATEGORY)): selector.SelectSelector(
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
            return self.async_show_form(step_id="reconfigure", data_schema=schema)

        errors = {}

        # Validate that entities exist
        registry = async_get_entity_registry(self.hass)
        for field in ["climate_entity", "indoor_temp_sensor", "outdoor_temp_sensor"]:
            entity_id = user_input[field]
            if not registry.async_is_registered(entity_id):
                if entity_id not in self.hass.states.async_entity_ids():
                    errors[field] = "entity_not_found"

        if errors:
            schema = vol.Schema(
                {
                    vol.Required(CONF_NAME, default=user_input.get(CONF_NAME, "Adaptive Climate")): str,
                    vol.Required("climate_entity", default=user_input.get("climate_entity", "")): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="climate")
                    ),
                    vol.Required("indoor_temp_sensor", default=user_input.get("indoor_temp_sensor", "")): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor", "input_number", "weather"],
                            device_class=["temperature"]
                        )
                    ),
                    vol.Required("outdoor_temp_sensor", default=user_input.get("outdoor_temp_sensor", "")): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor", "input_number", "weather"],
                            device_class=["temperature", "weather"]
                        )
                    ),
                    vol.Optional("comfort_category", default=user_input.get("comfort_category", DEFAULT_COMFORT_CATEGORY)): selector.SelectSelector(
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
            return self.async_show_form(
                step_id="reconfigure", data_schema=schema, errors=errors
            )

        # Update config data with user inputs
        self.config_data.update(user_input)
        
        # Restore previous options if available
        previous_entry_id = self.context.get("previous_entry_id")
        if previous_entry_id and "adaptive_climate_backup" in self.hass.data:
            backup_data = self.hass.data["adaptive_climate_backup"].get(previous_entry_id)
            if backup_data:
                # Use previous options
                previous_options = backup_data.get("options", {})
            else:
                previous_options = {}
        else:
            previous_options = {}
        
        return await self.async_step_optional_sensors_reconfigure(previous_options)

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

    async def async_step_optional_sensors_reconfigure(
        self, user_input: dict[str, Any] | None = None, previous_options: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle optional sensors step during reconfiguration."""
        if user_input is None:
            # Create schema with previous optional sensors as defaults if available
            current_data = self.config_data
            schema = vol.Schema({
                vol.Optional("occupancy_sensor", default=current_data.get("occupancy_sensor", "")): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="binary_sensor",
                        device_class=["motion", "occupancy", "presence"]
                    )
                ),
                vol.Optional("mean_radiant_temp_sensor", default=current_data.get("mean_radiant_temp_sensor", "")): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number"],
                        device_class=["temperature"]
                    )
                ),
                vol.Optional("indoor_humidity_sensor", default=current_data.get("indoor_humidity_sensor", "")): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number"],
                        device_class=["humidity"]
                    )
                ),
                vol.Optional("outdoor_humidity_sensor", default=current_data.get("outdoor_humidity_sensor", "")): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number", "weather"],
                        device_class=["humidity"]
                    )
                ),
            })
            return self.async_show_form(step_id="optional_sensors_reconfigure", data_schema=schema)

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

        # Create entry with restored options
        return self.async_create_entry(
            title=title, 
            data=self.config_data,
            options=previous_options or {}
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an option flow for Adaptive Climate."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options - simplified to avoid duplication with config entities."""
        if user_input is not None:
            # Handle reconfigure entities action
            if user_input.get("action") == "reconfigure_entities":
                # Store current config as backup
                if "adaptive_climate_backup" not in self.hass.data:
                    self.hass.data["adaptive_climate_backup"] = {}
                
                self.hass.data["adaptive_climate_backup"][self.config_entry.entry_id] = {
                    "data": dict(self.config_entry.data),
                    "options": dict(self.config_entry.options),
                }
                
                # Remove current entry and start reconfiguration
                await self.hass.config_entries.async_remove(self.config_entry.entry_id)
                
                # Trigger new config flow with previous entry context
                return self.async_external_step_done(
                    next_step_id="reconfigure",
                    extra_context={"previous_entry_id": self.config_entry.entry_id}
                )
            
            return self.async_create_entry(title="", data={})

        # Show only reconfiguration option to avoid duplication with config entities
        data_schema = vol.Schema({
            vol.Optional("action"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "reconfigure_entities", "label": "Reconfigure Entities (Climate, Sensors)"}
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            description_placeholders={
                "note": "All other settings can be adjusted using the configuration entities in the Controls tab of this device page."
            }
        )