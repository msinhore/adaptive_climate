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


class AdaptiveClimateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Adaptive Climate."""

    VERSION = 1
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