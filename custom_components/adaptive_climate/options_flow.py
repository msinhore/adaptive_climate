"""Options flow for Adaptive Climate integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    DEFAULT_COMFORT_CATEGORY,
    DEFAULT_MIN_COMFORT_TEMP,
    DEFAULT_MAX_COMFORT_TEMP,
    DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
    DEFAULT_OVERRIDE_TEMPERATURE,
    DEFAULT_AGGRESSIVE_COOLING_THRESHOLD,
    DEFAULT_AGGRESSIVE_HEATING_THRESHOLD,
    COMFORT_CATEGORIES,
)

_LOGGER = logging.getLogger(__name__)


class AdaptiveClimateOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Adaptive Climate options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options step."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        data = self.config_entry.data

        def get_value(key):
            return options.get(key) or data.get(key)

        # Define the options form schema
        schema = vol.Schema({
            # Step 1: Comfort Category and Modes
            vol.Required(
                "comfort_category",
                default=get_value("comfort_category") or DEFAULT_COMFORT_CATEGORY
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "I", "label": f"Category I - {COMFORT_CATEGORIES['I']['description']}"},
                        {"value": "II", "label": f"Category II - {COMFORT_CATEGORIES['II']['description']}"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional("energy_save_mode", default=get_value("energy_save_mode") or True): bool,
            vol.Optional("auto_mode_enabled", default=get_value("auto_mode_enabled") or True): bool,

            # Step 2: Cooling Devices
            vol.Required(
                "cooling_devices_primary",
                default=get_value("cooling_devices_primary") or []
            ): selector.selector({
                "entity": {"multiple": True, "domain": ["climate", "fan"]}
            }),
            vol.Optional(
                "cooling_devices_secondary",
                default=get_value("cooling_devices_secondary") or []
            ): selector.selector({
                "entity": {"multiple": True, "domain": ["fan", "switch"]}
            }),

            # Step 2: Heating Devices
            vol.Optional(
                "heating_devices_primary",
                default=get_value("heating_devices_primary") or []
            ): selector.selector({
                "entity": {"multiple": True, "domain": ["climate", "switch"]}
            }),
            vol.Optional(
                "heating_devices_secondary",
                default=get_value("heating_devices_secondary") or []
            ): selector.selector({
                "entity": {"multiple": True, "domain": ["climate", "switch"]}
            }),

            # Step 3: Sensors
            vol.Required(
                "indoor_temp_sensor",
                default=get_value("indoor_temp_sensor")
            ): selector.selector({"entity": {"device_class": "temperature"}}),

            vol.Required(
                "outdoor_temp_sensor",
                default=get_value("outdoor_temp_sensor")
            ): selector.selector({"entity": {"device_class": "temperature"}}),

            vol.Optional(
                "indoor_humidity_sensor",
                default=get_value("indoor_humidity_sensor")
            ): selector.selector({"entity": {"device_class": "humidity"}}),

            vol.Optional(
                "outdoor_humidity_sensor",
                default=get_value("outdoor_humidity_sensor")
            ): selector.selector({"entity": {"device_class": "humidity"}}),

            # Step 4: Advanced Configuration
            vol.Optional(
                "min_comfort_temp",
                default=get_value("min_comfort_temp") or DEFAULT_MIN_COMFORT_TEMP
            ): vol.All(vol.Coerce(float), vol.Range(min=10.0, max=30.0)),

            vol.Optional(
                "max_comfort_temp",
                default=get_value("max_comfort_temp") or DEFAULT_MAX_COMFORT_TEMP
            ): vol.All(vol.Coerce(float), vol.Range(min=15.0, max=35.0)),

            vol.Optional(
                "temperature_change_threshold",
                default=get_value("temperature_change_threshold") or DEFAULT_TEMPERATURE_CHANGE_THRESHOLD
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=5.0)),

            vol.Optional(
                "override_temperature",
                default=get_value("override_temperature") or DEFAULT_OVERRIDE_TEMPERATURE
            ): vol.All(vol.Coerce(float), vol.Range(min=-2, max=2)),

            vol.Optional(
                "aggressive_cooling_threshold",
                default=get_value("aggressive_cooling_threshold") or DEFAULT_AGGRESSIVE_COOLING_THRESHOLD
            ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),

            vol.Optional(
                "aggressive_heating_threshold",
                default=get_value("aggressive_heating_threshold") or DEFAULT_AGGRESSIVE_HEATING_THRESHOLD
            ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )


@callback
def async_get_options_flow(
    config_entry: config_entries.ConfigEntry,
) -> AdaptiveClimateOptionsFlowHandler:
    """Get the options flow handler."""
    return AdaptiveClimateOptionsFlowHandler(config_entry)