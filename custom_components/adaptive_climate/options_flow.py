"""Options flow for Adaptive Climate integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    # Default values
    DEFAULT_AIR_VELOCITY,
    DEFAULT_COMFORT_CATEGORY,
    DEFAULT_MIN_COMFORT_TEMP,
    DEFAULT_MAX_COMFORT_TEMP,
    DEFAULT_NATURAL_VENTILATION_THRESHOLD,
    DEFAULT_SETBACK_TEMPERATURE_OFFSET,
    DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
    DEFAULT_AUTO_SHUTDOWN_MINUTES,
    DEFAULT_AUTO_START_MINUTES,
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

        schema = vol.Schema({
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
                "air_velocity",
                default=options.get("air_velocity", DEFAULT_AIR_VELOCITY)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),

            vol.Optional(
                "temperature_change_threshold",
                default=options.get("temperature_change_threshold", DEFAULT_TEMPERATURE_CHANGE_THRESHOLD)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=5.0)),

            # === Energy Save ===
            vol.Optional(
                "energy_save_mode",
                default=options.get("energy_save_mode", True)
            ): bool,

            vol.Optional(
                "setback_temperature_offset",
                default=options.get("setback_temperature_offset", DEFAULT_SETBACK_TEMPERATURE_OFFSET)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),

            # === Auto Shutdown ===
            vol.Optional(
                "auto_shutdown_enable",
                default=options.get("auto_shutdown_enable", False)
            ): bool,

            vol.Optional(
                "auto_shutdown_minutes",
                default=options.get("auto_shutdown_minutes", DEFAULT_AUTO_SHUTDOWN_MINUTES)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=240)),

            # === Auto Start on Presence ===
            vol.Optional(
                "auto_start_enable",
                default=options.get("auto_start_enable", False)
            ): bool,

            vol.Optional(
                "auto_start_minutes",
                default=options.get("auto_start_minutes", DEFAULT_AUTO_START_MINUTES)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),

            # === Fan Mode Velocities ===
            vol.Optional(
                "fan_mode_low_velocity",
                default=options.get("fan_mode_low_velocity", 0.15)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),

            vol.Optional(
                "fan_mode_mid_velocity",
                default=options.get("fan_mode_mid_velocity", 0.25)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),

            vol.Optional(
                "fan_mode_high_velocity",
                default=options.get("fan_mode_high_velocity", 0.4)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),
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
