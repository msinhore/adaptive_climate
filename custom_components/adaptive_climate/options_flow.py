"""Options flow for Adaptive Climate integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from custom_components.adaptive_climate.const import (  # Default values; HVAC and Fan Control; Categories
    COMFORT_CATEGORIES,
    DEFAULT_AGGRESSIVE_COOLING_THRESHOLD,
    DEFAULT_AGGRESSIVE_HEATING_THRESHOLD,
    DEFAULT_COMFORT_CATEGORY,
    DEFAULT_ENABLE_COOL_MODE,
    DEFAULT_ENABLE_DRY_MODE,
    DEFAULT_ENABLE_FAN_MODE,
    DEFAULT_ENABLE_HEAT_MODE,
    DEFAULT_ENABLE_OFF_MODE,
    DEFAULT_MANUAL_PAUSE_DURATION,
    DEFAULT_MAX_COMFORT_TEMP,
    DEFAULT_MAX_FAN_SPEED,
    DEFAULT_MIN_COMFORT_TEMP,
    DEFAULT_MIN_FAN_SPEED,
    DEFAULT_OVERRIDE_TEMPERATURE,
    DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
    DOMAIN,
    FAN_SPEED_OPTIONS,
    HVAC_MODE_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)


class AdaptiveClimateOptionsFlowHandler(config_entries.OptionsFlow):
    """Single, consolidated form without area selector (area locked by entry)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        options = self.config_entry.options
        data = self.config_entry.data

        area_id = data.get("area_id")  # Area is fixed; do not allow changing

        def get_value(key: str):
            return options.get(key) if key in options else data.get(key)

        # Helper to build entity selector with optional area restriction
        def entity_selector(domain: str, device_class: str | None = None, multiple: bool = False):
            cfg: dict[str, Any] = {"domain": domain}
            if device_class:
                cfg["device_class"] = device_class
            if multiple:
                cfg["multiple"] = True
            return selector.selector({"entity": cfg})

        # Helper to build entity selector that supports both sensor and weather entities
        def temp_humidity_entity_selector(device_class: str, multiple: bool = False):
            cfg: dict[str, Any] = {"domain": ["sensor", "weather"]}
            if device_class:
                cfg["device_class"] = device_class
            if multiple:
                cfg["multiple"] = True
            return selector.selector({"entity": cfg})

        # Discover supported HVAC modes from the configured climate entity (if available)
        climate_entity_id = options.get("climate_entity") or data.get("climate_entity") or data.get("entity")
        supported_hvac_modes: list[str] = []
        if climate_entity_id and hasattr(self, "hass") and self.hass is not None:
            state = self.hass.states.get(climate_entity_id)
            if state:
                try:
                    supported_hvac_modes = list(state.attributes.get("hvac_modes", []))
                except Exception:
                    supported_hvac_modes = []

        # Build select options for user overrides
        def build_hvac_override_select(default_key: str):
            choices = [{"value": "disable", "label": "Disable"}] + [
                {"value": m, "label": m} for m in supported_hvac_modes
            ]
            return selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=choices,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        schema = vol.Schema(
            {
                # === Sensors ===
                vol.Required(
                    "indoor_temp_sensor",
                    default=get_value("indoor_temp_sensor"),
                ): temp_humidity_entity_selector("temperature"),
                vol.Required(
                    "outdoor_temp_sensor",
                    default=get_value("outdoor_temp_sensor"),
                ): temp_humidity_entity_selector("temperature"),
                vol.Optional(
                    "indoor_humidity_sensor",
                    default=get_value("indoor_humidity_sensor"),
                ): temp_humidity_entity_selector("humidity"),
                vol.Optional(
                    "outdoor_humidity_sensor",
                    default=get_value("outdoor_humidity_sensor"),
                ): temp_humidity_entity_selector("humidity"),
                # === Comfort Category ===
                vol.Optional(
                    "comfort_category",
                    default=options.get(
                        "comfort_category", DEFAULT_COMFORT_CATEGORY
                    ),
                ): vol.In(list(COMFORT_CATEGORIES.keys())),
                # === Energy Save ===
                vol.Optional(
                    "energy_save_mode",
                    default=options.get("energy_save_mode", True),
                ): bool,
                # === Adaptive Climate Auto Mode ===
                vol.Optional(
                    "auto_mode_enable",
                    default=options.get("auto_mode_enable", True),
                ): bool,
                # === Auto-Pause Settings ===
                vol.Optional(
                    "manual_pause_duration",
                    default=options.get(
                        "manual_pause_duration", DEFAULT_MANUAL_PAUSE_DURATION
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=480)),
                # === Temperature Configuration ===
                vol.Optional(
                    "min_comfort_temp",
                    default=options.get(
                        "min_comfort_temp", DEFAULT_MIN_COMFORT_TEMP
                    ),
                ): vol.All(vol.Coerce(float), vol.Range(min=10.0, max=30.0)),
                vol.Optional(
                    "max_comfort_temp",
                    default=options.get(
                        "max_comfort_temp", DEFAULT_MAX_COMFORT_TEMP
                    ),
                ): vol.All(vol.Coerce(float), vol.Range(min=15.0, max=35.0)),
                vol.Optional(
                    "temperature_change_threshold",
                    default=options.get(
                        "temperature_change_threshold",
                        DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
                    ),
                ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=5.0)),
                vol.Optional(
                    "override_temperature",
                    default=options.get(
                        "override_temperature", DEFAULT_OVERRIDE_TEMPERATURE
                    ),
                ): vol.All(vol.Coerce(float), vol.Range(min=-2, max=2)),
                # === Aggressive Cooling / Heating ===
                vol.Optional(
                    "aggressive_cooling_threshold",
                    default=options.get(
                        "aggressive_cooling_threshold",
                        DEFAULT_AGGRESSIVE_COOLING_THRESHOLD,
                    ),
                ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),
                vol.Optional(
                    "aggressive_heating_threshold",
                    default=options.get(
                        "aggressive_heating_threshold",
                        DEFAULT_AGGRESSIVE_HEATING_THRESHOLD,
                    ),
                ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),
                # === HVAC and Fan Control ===
                vol.Optional(
                    "control_secondary_fans",
                    default=options.get("control_secondary_fans", True),
                ): bool,
                vol.Optional(
                    "enable_fan_mode",
                    default=options.get(
                        "enable_fan_mode", DEFAULT_ENABLE_FAN_MODE
                    ),
                ): bool,
                vol.Optional(
                    "enable_cool_mode",
                    default=options.get(
                        "enable_cool_mode", DEFAULT_ENABLE_COOL_MODE
                    ),
                ): bool,
                vol.Optional(
                    "enable_heat_mode",
                    default=options.get(
                        "enable_heat_mode", DEFAULT_ENABLE_HEAT_MODE
                    ),
                ): bool,
                vol.Optional(
                    "enable_dry_mode",
                    default=options.get(
                        "enable_dry_mode", DEFAULT_ENABLE_DRY_MODE
                    ),
                ): bool,
                vol.Optional(
                    "enable_off_mode",
                    default=options.get(
                        "enable_off_mode", DEFAULT_ENABLE_OFF_MODE
                    ),
                ): bool,
                vol.Optional(
                    "max_fan_speed",
                    default=options.get(
                        "max_fan_speed", DEFAULT_MAX_FAN_SPEED
                    ),
                ): vol.In(list(FAN_SPEED_OPTIONS.keys())),
                vol.Optional(
                    "min_fan_speed",
                    default=options.get(
                        "min_fan_speed", DEFAULT_MIN_FAN_SPEED
                    ),
                ): vol.In(list(FAN_SPEED_OPTIONS.keys())),
                # === HVAC intent overrides (use specific device mode or disable) ===
                vol.Optional("hvac_mode_for_cooling"): build_hvac_override_select(
                    "hvac_mode_for_cooling"
                ),
                vol.Optional("hvac_mode_for_heating"): build_hvac_override_select(
                    "hvac_mode_for_heating"
                ),
                vol.Optional("hvac_mode_for_drying"): build_hvac_override_select(
                    "hvac_mode_for_drying"
                ),
                vol.Optional("hvac_mode_for_fan_only"): build_hvac_override_select(
                    "hvac_mode_for_fan_only"
                ),
                # === Manual role configuration (multi-entity selectors) ===
                vol.Optional(
                    "primary_climates",
                    default=options.get("primary_climates", []),
                ): entity_selector("climate", multiple=True),
                vol.Optional(
                    "secondary_climates",
                    default=options.get("secondary_climates", []),
                ): entity_selector("climate", multiple=True),
                vol.Optional(
                    "secondary_fans",
                    default=options.get("secondary_fans", []),
                ): entity_selector("fan", multiple=True),
            }
        )

        if user_input is None:
            # Inject field descriptions from translations (if available)
            descriptions = self.hass.data.get(
                DOMAIN, {}
            )  # not strictly necessary; kept simple to avoid extra lookups
            return self.async_show_form(step_id="init", data_schema=schema)

        to_save = dict(user_input)
        # Re-save the locked area for reference (unchanged)
        if area_id:
            to_save["area_last_used"] = area_id
        return self.async_create_entry(title="", data=to_save)


@callback
def async_get_options_flow(
    config_entry: config_entries.ConfigEntry,
) -> AdaptiveClimateOptionsFlowHandler:
    """Get the options flow for this handler."""
    return AdaptiveClimateOptionsFlowHandler()
