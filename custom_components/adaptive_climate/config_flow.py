"""Config flow for Adaptive Climate integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import (
    DOMAIN,
    DEFAULT_COMFORT_CATEGORY,
    COMFORT_CATEGORIES,
    DEFAULT_ENABLE_FAN_MODE,
    DEFAULT_ENABLE_COOL_MODE,
    DEFAULT_ENABLE_HEAT_MODE,
    DEFAULT_ENABLE_DRY_MODE,
    DEFAULT_MAX_FAN_SPEED,
    DEFAULT_MIN_FAN_SPEED,
    HVAC_MODE_OPTIONS,
    FAN_SPEED_OPTIONS,
)
from .options_flow import async_get_options_flow

_LOGGER = logging.getLogger(__name__)

# Config Schema for initial setup - only essential entities
CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="Adaptive Climate"): str,
        vol.Required("climate_entities"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="climate",
                multiple=True  # Support multiple devices
            )
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
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional(
            "min_comfort_temp",
            default=21
        ): vol.All(vol.Coerce(float), vol.Range(min=10.0, max=30.0)),

        vol.Optional(
            "max_comfort_temp",
            default=27
        ): vol.All(vol.Coerce(float), vol.Range(min=15.0, max=35.0)),

        vol.Optional(
            "temperature_change_threshold",
            default=0.5
        ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=5.0)),

        vol.Optional(
            "override_temperature",
            default=0
        ): vol.All(vol.Coerce(float), vol.Range(min=-2, max=2)),

        vol.Optional(
            "energy_save_mode",
            default=True
        ): bool,

        vol.Optional(
            "auto_mode_enable",
            default=True
        ): bool,

        vol.Optional(
            "aggressive_cooling_threshold",
            default=2.0
        ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),

        vol.Optional(
            "aggressive_heating_threshold",
            default=2.0
        ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),

        # === HVAC and Fan Control ===
        vol.Optional(
            "enable_fan_mode",
            default=DEFAULT_ENABLE_FAN_MODE
        ): bool,

        vol.Optional(
            "enable_cool_mode",
            default=DEFAULT_ENABLE_COOL_MODE
        ): bool,

        vol.Optional(
            "enable_heat_mode",
            default=DEFAULT_ENABLE_HEAT_MODE
        ): bool,

        vol.Optional(
            "enable_dry_mode",
            default=DEFAULT_ENABLE_DRY_MODE
        ): bool,

        vol.Optional(
            "max_fan_speed",
            default=DEFAULT_MAX_FAN_SPEED
        ): vol.In(list(FAN_SPEED_OPTIONS.keys())),

        vol.Optional(
            "min_fan_speed",
            default=DEFAULT_MIN_FAN_SPEED
        ): vol.In(list(FAN_SPEED_OPTIONS.keys())),
    }
)

# Optional sensors schema for second step
OPTIONAL_SENSORS_SCHEMA = vol.Schema(
    {
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


class AdaptiveClimateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Adaptive Climate."""

    VERSION = 1
    
    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return async_get_options_flow(config_entry)
    MINOR_VERSION = 0

    def __init__(self):
        """Initialize config flow."""
        self.config_data = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=CONFIG_SCHEMA)

        errors = {}

        # Validate that entities exist
        for field in ["indoor_temp_sensor", "outdoor_temp_sensor"]:
            entity_id = user_input[field]
            if entity_id not in self.hass.states.async_entity_ids():
                errors[field] = "entity_not_found"
        
        # Validate climate entities
        climate_entities = user_input.get("climate_entities", [])
        if not climate_entities:
            errors["climate_entities"] = "no_climate_entities"
        else:
            for entity_id in climate_entities:
                if entity_id not in self.hass.states.async_entity_ids():
                    errors["climate_entities"] = "entity_not_found"
                    break

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

        # Create unique ID based on first climate entity to prevent duplicates
        climate_entities = self.config_data["climate_entities"]
        first_entity = climate_entities[0] if climate_entities else "unknown"
        unique_id = f"adaptive_climate_{first_entity.replace('.', '_')}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(
            updates={CONF_NAME: self.config_data[CONF_NAME]}
        )

        # Create dynamic title based on climate entities
        if len(climate_entities) == 1:
            # Single device - use its name
            climate_entity = climate_entities[0]
            climate_state = self.hass.states.get(climate_entity)
            
            if climate_state and hasattr(climate_state, 'attributes'):
                friendly_name = climate_state.attributes.get("friendly_name", "")
                if friendly_name:
                    title = f"Adaptive Climate - {friendly_name}"
                else:
                    title = f"Adaptive Climate - {climate_entity.split('.')[-1].replace('_', ' ').title()}"
            else:
                title = self.config_data[CONF_NAME]
        else:
            # Multiple devices - use area name
            title = f"Adaptive Climate - {self.config_data[CONF_NAME]} ({len(climate_entities)} devices)"

        return self.async_create_entry(title=title, data=self.config_data)