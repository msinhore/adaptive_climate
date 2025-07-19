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
from .options_flow import async_get_options_flow

_LOGGER = logging.getLogger(__name__)

# Config Schema for initial setup - only essential entities
CONFIG_SCHEMA = vol.Schema(
    {
        # Comfort Category
        vol.Required("comfort_category", default=DEFAULT_COMFORT_CATEGORY): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": "I", "label": f"Category I - {COMFORT_CATEGORIES['I']['description']}"},
                    {"value": "II", "label": f"Category II - {COMFORT_CATEGORIES['II']['description']}"},
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional("energy_save_mode", default=True): bool,
        vol.Optional("auto_mode_enabled", default=True): bool,

        # Cooling Devices
        vol.Required("cooling_devices_primary", default=[]): selector.selector({
            "entity": {"multiple": True, "domain": ["climate", "fan"]}
        }),
        vol.Optional("cooling_devices_secondary", default=[]): selector.selector({
            "entity": {"multiple": True, "domain": ["fan", "switch"]}
        }),

        # Heating Devices
        vol.Optional("heating_devices_primary", default=[]): selector.selector({
            "entity": {"multiple": True, "domain": ["climate", "switch"]}
        }),
        vol.Optional("heating_devices_secondary", default=[]): selector.selector({
            "entity": {"multiple": True, "domain": ["climate", "switch"]}
        }),

        # Sensors
        vol.Required("indoor_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number", "weather"], device_class=["temperature"])
        ),
        vol.Required("outdoor_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number", "weather"], device_class=["temperature", "weather"])
        ),
        vol.Optional("indoor_humidity_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"], device_class=["humidity"])
        ),
        vol.Optional("outdoor_humidity_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number", "weather"], device_class=["humidity"])
        ),

        # Advanced Configuration
        vol.Optional("min_comfort_temp", default=21): vol.All(vol.Coerce(float), vol.Range(min=10.0, max=30.0)),
        vol.Optional("max_comfort_temp", default=27): vol.All(vol.Coerce(float), vol.Range(min=15.0, max=35.0)),
        vol.Optional("temperature_change_threshold", default=0.5): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=5.0)),
        vol.Optional("override_temperature", default=0): vol.All(vol.Coerce(float), vol.Range(min=-2, max=2)),
        vol.Optional("aggressive_cooling_threshold", default=2.0): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),
        vol.Optional("aggressive_heating_threshold", default=2.0): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),

        # Instance Name
        vol.Required(CONF_NAME, default="Adaptive Climate"): str,
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

        # Validate only temperature sensors
        registry = async_get_entity_registry(self.hass)
        for field in ["indoor_temp_sensor", "outdoor_temp_sensor"]:
            entity_id = user_input[field]
            if not registry.async_is_registered(entity_id):
                if entity_id not in self.hass.states.async_entity_ids():
                    errors[field] = "entity_not_found"

        if errors:
            return self.async_show_form(
                step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
            )

        # Save config and create entry
        self.config_data.update(user_input)

        unique_id = f"adaptive_climate_{self.config_data[CONF_NAME].replace(' ', '_').lower()}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(updates={CONF_NAME: self.config_data[CONF_NAME]})

        return self.async_create_entry(
            title=self.config_data[CONF_NAME],
            data=self.config_data
        )