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
    # Default values
    DEFAULT_COMFORT_CATEGORY,
    DEFAULT_MIN_COMFORT_TEMP,
    DEFAULT_MAX_COMFORT_TEMP,
    DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
    DEFAULT_OVERRIDE_TEMPERATURE,
    DEFAULT_AGGRESSIVE_COOLING_THRESHOLD,
    DEFAULT_AGGRESSIVE_HEATING_THRESHOLD,
    # Categories
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
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        data = self.config_entry.data  # <-- importante

        def get_value(key):
            return options.get(key) or data.get(key)

        schema = vol.Schema({
            # === Entity Configuration ===
            vol.Required(
                "climate_entity",
                default=get_value("climate_entity")
            ): selector.selector({"entity": {"domain": "climate"}}),

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

            # === Comfort Category ===
            vol.Optional(
                "comfort_category",
                default=options.get("comfort_category", DEFAULT_COMFORT_CATEGORY)
            ): vol.In(list(COMFORT_CATEGORIES.keys())),

            # === Globais ===
            vol.Optional(
                "min_comfort_temp",
                default=options.get("min_comfort_temp", DEFAULT_MIN_COMFORT_TEMP)
            ): vol.All(vol.Coerce(float), vol.Range(min=10.0, max=30.0)),

            vol.Optional(
                "max_comfort_temp", 
                default=options.get("max_comfort_temp", DEFAULT_MAX_COMFORT_TEMP)
            ): vol.All(vol.Coerce(float), vol.Range(min=15.0, max=35.0)),

            vol.Optional(
                "temperature_change_threshold",
                default=options.get("temperature_change_threshold", DEFAULT_TEMPERATURE_CHANGE_THRESHOLD)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=5.0)),

            vol.Optional(
                "override_temperature",
                default=options.get("override_temperature", DEFAULT_OVERRIDE_TEMPERATURE)
            ): vol.All(vol.Coerce(float), vol.Range(min=-2, max=2)),

            # === Energy Save ===
            vol.Optional(
                "energy_save_mode",
                default=options.get("energy_save_mode", True)
            ): bool,

            # === Adaptive Climate Auto Mode ===
            vol.Optional(
                "auto_mode_enable",
                default=options.get("auto_mode_enable", True)
            ): bool,

            # === Aggressive Cooling / Heating ===
            vol.Optional(
                "aggressive_cooling_threshold",
                default=options.get("aggressive_cooling_threshold", DEFAULT_AGGRESSIVE_COOLING_THRESHOLD)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),

            vol.Optional(
                "aggressive_heating_threshold",
                default=options.get("aggressive_heating_threshold", DEFAULT_AGGRESSIVE_HEATING_THRESHOLD)
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
    """Get the options flow for this handler."""
    return AdaptiveClimateOptionsFlowHandler(config_entry)
