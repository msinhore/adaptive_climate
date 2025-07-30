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
    # HVAC and Fan Control
    DEFAULT_ENABLE_FAN_MODE,
    DEFAULT_ENABLE_COOL_MODE,
    DEFAULT_ENABLE_HEAT_MODE,
    DEFAULT_ENABLE_DRY_MODE,
    DEFAULT_MAX_FAN_SPEED,
    DEFAULT_MIN_FAN_SPEED,
    HVAC_MODE_OPTIONS,
    FAN_SPEED_OPTIONS,
    # Categories
    COMFORT_CATEGORIES,
)

_LOGGER = logging.getLogger(__name__)

class AdaptiveClimateOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Adaptive Climate options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            _LOGGER.debug(f"Options flow user input: {user_input}")
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        data = self.config_entry.data

        _LOGGER.debug(f"Options flow - options: {options}")
        _LOGGER.debug(f"Options flow - data: {data}")

        def get_value(key):
            return options.get(key) if key in options else data.get(key)

        # Get climate entities from options or data
        climate_entities = options.get("climate_entities")
        if climate_entities is None:
            # Try to get from data (for backward compatibility)
            climate_entities = data.get("climate_entities")
            if climate_entities is None:
                # Try to get from old format
                if "climate_entity" in data:
                    climate_entities = [data["climate_entity"]]
                elif "entity" in data:
                    climate_entities = [data["entity"]]
                else:
                    climate_entities = []
        
        _LOGGER.debug(f"Options flow - climate_entities: {climate_entities}")
        
        # Create base schema
        base_schema = vol.Schema({
            # === Climate Entities ===
            vol.Optional(
                "climate_entities",
                default=climate_entities
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="climate",
                    multiple=True  # Support multiple devices
                )
            ),
            
            # === Comfort Category ===
            vol.Optional(
                "comfort_category",
                default=options.get("comfort_category", DEFAULT_COMFORT_CATEGORY)
            ): vol.In(list(COMFORT_CATEGORIES.keys())),

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

            # === Temperature Configuration ===
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

            # === Aggressive Cooling / Heating ===
            vol.Optional(
                "aggressive_cooling_threshold",
                default=options.get("aggressive_cooling_threshold", DEFAULT_AGGRESSIVE_COOLING_THRESHOLD)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),

            vol.Optional(
                "aggressive_heating_threshold",
                default=options.get("aggressive_heating_threshold", DEFAULT_AGGRESSIVE_HEATING_THRESHOLD)
            ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),

            # === HVAC and Fan Control ===
            vol.Optional(
                "enable_fan_mode",
                default=options.get("enable_fan_mode", DEFAULT_ENABLE_FAN_MODE)
            ): bool,
            vol.Optional(
                "enable_cool_mode",
                default=options.get("enable_cool_mode", DEFAULT_ENABLE_COOL_MODE)
            ): bool,
            vol.Optional(
                "enable_heat_mode",
                default=options.get("enable_heat_mode", DEFAULT_ENABLE_HEAT_MODE)
            ): bool,
            vol.Optional(
                "enable_dry_mode",
                default=options.get("enable_dry_mode", DEFAULT_ENABLE_DRY_MODE)
            ): bool,
            vol.Optional(
                "max_fan_speed",
                default=options.get("max_fan_speed", DEFAULT_MAX_FAN_SPEED)
            ): vol.In(list(FAN_SPEED_OPTIONS.keys())),
            vol.Optional(
                "min_fan_speed",
                default=options.get("min_fan_speed", DEFAULT_MIN_FAN_SPEED)
            ): vol.In(list(FAN_SPEED_OPTIONS.keys())),

        })

        # Use add_suggested_values_to_schema as recommended in documentation
        schema = self.add_suggested_values_to_schema(base_schema, self.config_entry.options)

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )

@callback
def async_get_options_flow(
    config_entry: config_entries.ConfigEntry,
) -> AdaptiveClimateOptionsFlowHandler:
    """Get the options flow for this handler."""
    return AdaptiveClimateOptionsFlowHandler()
