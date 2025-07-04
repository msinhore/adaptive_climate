"""Options flow for Adaptive Climate integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    # Default values
    DEFAULT_AIR_VELOCITY,
    DEFAULT_COMFORT_CATEGORY,
    DEFAULT_COMFORT_TEMP_MIN_OFFSET,
    DEFAULT_COMFORT_TEMP_MAX_OFFSET,
    DEFAULT_MIN_COMFORT_TEMP,
    DEFAULT_MAX_COMFORT_TEMP,
    DEFAULT_NATURAL_VENTILATION_THRESHOLD,
    DEFAULT_SETBACK_TEMPERATURE_OFFSET,
    DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
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

        # Get current options with defaults
        options = self.config_entry.options
        
        schema = vol.Schema({
            # Temperature Range Settings
            vol.Optional(
                "min_comfort_temp",
                default=options.get("min_comfort_temp", DEFAULT_MIN_COMFORT_TEMP)
            ): vol.All(vol.Coerce(float), vol.Range(min=10.0, max=30.0)),
            
            vol.Optional(
                "max_comfort_temp", 
                default=options.get("max_comfort_temp", DEFAULT_MAX_COMFORT_TEMP)
            ): vol.All(vol.Coerce(float), vol.Range(min=15.0, max=35.0)),
            
            vol.Optional(
                "comfort_range_min_offset",
                default=options.get("comfort_range_min_offset", DEFAULT_COMFORT_TEMP_MIN_OFFSET)
            ): vol.All(vol.Coerce(float), vol.Range(min=-10.0, max=0.0)),
            
            vol.Optional(
                "comfort_range_max_offset",
                default=options.get("comfort_range_max_offset", DEFAULT_COMFORT_TEMP_MAX_OFFSET)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=10.0)),
            
            # Air Velocity Settings
            vol.Optional(
                "air_velocity",
                default=options.get("air_velocity", DEFAULT_AIR_VELOCITY)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),
            
            # Thresholds
            vol.Optional(
                "temperature_change_threshold",
                default=options.get("temperature_change_threshold", DEFAULT_TEMPERATURE_CHANGE_THRESHOLD)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=5.0)),
            
            vol.Optional(
                "natural_ventilation_threshold",
                default=options.get("natural_ventilation_threshold", DEFAULT_NATURAL_VENTILATION_THRESHOLD)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),
            
            vol.Optional(
                "setback_temperature_offset",
                default=options.get("setback_temperature_offset", DEFAULT_SETBACK_TEMPERATURE_OFFSET)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),
            
            # Comfort Category
            vol.Optional(
                "comfort_category",
                default=options.get("comfort_category", DEFAULT_COMFORT_CATEGORY)
            ): vol.In(list(COMFORT_CATEGORIES.keys())),
            
            # Feature Toggles
            vol.Optional(
                "energy_save_mode",
                default=options.get("energy_save_mode", True)
            ): bool,
            
            vol.Optional(
                "natural_ventilation_enable",
                default=options.get("natural_ventilation_enable", True)
            ): bool,
            
            vol.Optional(
                "adaptive_air_velocity",
                default=options.get("adaptive_air_velocity", True)
            ): bool,
            
            vol.Optional(
                "humidity_comfort_enable",
                default=options.get("humidity_comfort_enable", True)
            ): bool,
            
            vol.Optional(
                "comfort_precision_mode",
                default=options.get("comfort_precision_mode", False)
            ): bool,
            
            vol.Optional(
                "use_operative_temperature",
                default=options.get("use_operative_temperature", False)
            ): bool,
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
