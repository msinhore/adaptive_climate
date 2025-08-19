"""Options flow for Adaptive Climate integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from custom_components.adaptive_climate.const import (
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
    FAN_SPEED_OPTIONS,
)
from custom_components.adaptive_climate.utils.area import (
    collect_area_devices,
    collect_area_fans,
)

_LOGGER = logging.getLogger(__name__)


## Removed: outdated single-step handler duplicate

def _auto_selected_entities(hass, config_entry) -> dict[str, list[str]]:
    """Return automatic selection for read-only display in options.

    - Primary: currently configured climate entity (this integration instance)
    - Secondary climates: other climate entities in the same area
    - Secondary fans: fan entities in the same area
    """
    try:
        climate_entity_id = config_entry.data.get("entity") or config_entry.data.get(
            "climate_entity"
        )
        primary = [climate_entity_id] if climate_entity_id else []

        # Collect peers in the same area
        secondary_climates: list[str] = []
        secondary_fans: list[str] = []
        if hass is not None and climate_entity_id:
            try:
                # Other climates in area (exclude primary)
                devices = collect_area_devices(hass, climate_entity_id)
                secondary_climates = [
                    d.entity_id for d in devices if d.entity_id != climate_entity_id
                ]
            except Exception:
                secondary_climates = []
            try:
                # Fans in area
                secondary_fans = collect_area_fans(hass, climate_entity_id)
            except Exception:
                secondary_fans = []

        return {
            "primary_climates": primary,
            "secondary_climates": secondary_climates,
            "secondary_fans": secondary_fans,
        }
    except Exception:  # pragma: no cover - defensive
        return {"primary_climates": [], "secondary_climates": [], "secondary_fans": []}


class AdaptiveClimateOptionsFlowHandler(config_entries.OptionsFlow):
    """Two-step options flow with read-only devices when auto selection is on."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self.auto_device_enabled: bool = bool(
            config_entry.options.get("auto_device_selection", False)
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        options = self.config_entry.options
        default_toggle = bool(options.get("auto_device_selection", False))

        if user_input is not None:
            self.auto_device_enabled = bool(
                user_input.get("auto_device_selection", default_toggle)
            )
            return await self.async_step_options()

        schema = vol.Schema(
            {vol.Optional("auto_device_selection", default=default_toggle): bool}
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        options = self.config_entry.options
        data = self.config_entry.data

        def get_value(key: str) -> Any:
            return options.get(key) if key in options else data.get(key)

        def entity_selector(
            domain: str, device_class: str | None = None, multiple: bool = False
        ):
            cfg: dict[str, Any] = {"domain": domain}
            if device_class:
                cfg["device_class"] = device_class
            if multiple:
                cfg["multiple"] = True
            return selector.selector({"entity": cfg})

        # Helpers to support weather entities in selectors, mirroring config_flow
        def temp_entity_selector(is_outdoor: bool, multiple: bool = False):
            cfg: dict[str, Any] = {
                "domain": ["sensor", "input_number", "weather"],
                "device_class": ["temperature"] if not is_outdoor else ["temperature", "weather"],
            }
            if multiple:
                cfg["multiple"] = True
            return selector.selector({"entity": cfg})

        def humidity_entity_selector(is_outdoor: bool, multiple: bool = False):
            cfg: dict[str, Any] = {
                "domain": ["sensor", "input_number"] + (["weather"] if is_outdoor else []),
                "device_class": ["humidity"],
            }
            if multiple:
                cfg["multiple"] = True
            return selector.selector({"entity": cfg})

        # Discover supported hvac modes to build override selects
        climate_entity_id = (
            options.get("climate_entity") or data.get("climate_entity") or data.get("entity")
        )
        supported_hvac_modes: list[str] = []
        if climate_entity_id and hasattr(self, "hass") and self.hass is not None:
            state = self.hass.states.get(climate_entity_id)
            if state:
                try:
                    supported_hvac_modes = list(state.attributes.get("hvac_modes", []))
                except Exception:  # pragma: no cover
                    supported_hvac_modes = []

        def build_hvac_override_select() -> selector.SelectSelector:
            choices = [{"value": "disable", "label": "Disable"}] + [
                {"value": m, "label": m} for m in supported_hvac_modes
            ]
            return selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=choices, mode=selector.SelectSelectorMode.DROPDOWN
                )
            )

        # Base schema (no toggle here; toggle handled on previous step)
        schema = vol.Schema(
            {
                # Sensors
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
                ): humidity_entity_selector(is_outdoor=True),

                # Comfort
                vol.Optional(
                    "comfort_category",
                    default=options.get("comfort_category", DEFAULT_COMFORT_CATEGORY),
                ): vol.In(list(COMFORT_CATEGORIES.keys())),

                # Energy save
                vol.Optional("energy_save_mode", default=options.get("energy_save_mode", True)): bool,

                # Adaptive auto mode
                vol.Optional("auto_mode_enable", default=options.get("auto_mode_enable", True)): bool,

                # Pause
                vol.Optional(
                    "manual_pause_duration",
                    default=options.get("manual_pause_duration", DEFAULT_MANUAL_PAUSE_DURATION),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=480)),

                # Temperature config
                vol.Optional("min_comfort_temp", default=options.get("min_comfort_temp", DEFAULT_MIN_COMFORT_TEMP)): vol.All(vol.Coerce(float), vol.Range(min=10.0, max=30.0)),
                vol.Optional("max_comfort_temp", default=options.get("max_comfort_temp", DEFAULT_MAX_COMFORT_TEMP)): vol.All(vol.Coerce(float), vol.Range(min=15.0, max=35.0)),
                vol.Optional("temperature_change_threshold", default=options.get("temperature_change_threshold", DEFAULT_TEMPERATURE_CHANGE_THRESHOLD)): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=5.0)),
                vol.Optional("override_temperature", default=options.get("override_temperature", DEFAULT_OVERRIDE_TEMPERATURE)): vol.All(vol.Coerce(float), vol.Range(min=-2, max=2)),

                # Aggressive thresholds
                vol.Optional("aggressive_cooling_threshold", default=options.get("aggressive_cooling_threshold", DEFAULT_AGGRESSIVE_COOLING_THRESHOLD)): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),
                vol.Optional("aggressive_heating_threshold", default=options.get("aggressive_heating_threshold", DEFAULT_AGGRESSIVE_HEATING_THRESHOLD)): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),

                # HVAC and fan control
                vol.Optional("control_secondary_fans", default=options.get("control_secondary_fans", True)): bool,
                vol.Optional("enable_fan_mode", default=options.get("enable_fan_mode", DEFAULT_ENABLE_FAN_MODE)): bool,
                vol.Optional("enable_cool_mode", default=options.get("enable_cool_mode", DEFAULT_ENABLE_COOL_MODE)): bool,
                vol.Optional("enable_heat_mode", default=options.get("enable_heat_mode", DEFAULT_ENABLE_HEAT_MODE)): bool,
                vol.Optional("enable_dry_mode", default=options.get("enable_dry_mode", DEFAULT_ENABLE_DRY_MODE)): bool,
                vol.Optional("enable_off_mode", default=options.get("enable_off_mode", DEFAULT_ENABLE_OFF_MODE)): bool,
                vol.Optional("max_fan_speed", default=options.get("max_fan_speed", DEFAULT_MAX_FAN_SPEED)): vol.In(list(FAN_SPEED_OPTIONS.keys())),
                vol.Optional("min_fan_speed", default=options.get("min_fan_speed", DEFAULT_MIN_FAN_SPEED)): vol.In(list(FAN_SPEED_OPTIONS.keys())),
            }
        )

        # Add hvac override selects
        schema = schema.extend(
            {
                vol.Optional("hvac_mode_for_cooling"): build_hvac_override_select(),
                vol.Optional("hvac_mode_for_heating"): build_hvac_override_select(),
                vol.Optional("hvac_mode_for_drying"): build_hvac_override_select(),
                vol.Optional("hvac_mode_for_fan_only"): build_hvac_override_select(),
            }
        )

        # Devices: read-only vs editable
        if self.auto_device_enabled:
            auto = _auto_selected_entities(self.hass, self.config_entry)
            schema = schema.extend(
                {
                    vol.Optional(
                        "primary_climates",
                        default=auto.get("primary_climates", []),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="climate", multiple=True, read_only=True
                        )
                    ),
                    vol.Optional(
                        "secondary_climates",
                        default=auto.get("secondary_climates", []),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="climate", multiple=True, read_only=True
                        )
                    ),
                    vol.Optional(
                        "secondary_fans",
                        default=auto.get("secondary_fans", []),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="fan", multiple=True, read_only=True
                        )
                    ),
                }
            )
        else:
            schema = schema.extend(
                {
                    vol.Optional("primary_climates", default=options.get("primary_climates", [])): entity_selector("climate", multiple=True),
                    vol.Optional("secondary_climates", default=options.get("secondary_climates", [])): entity_selector("climate", multiple=True),
                    vol.Optional("secondary_fans", default=options.get("secondary_fans", [])): entity_selector("fan", multiple=True),
                }
            )

        if user_input is None:
            return self.async_show_form(step_id="options", data_schema=schema)

        to_save = dict(user_input)
        # Persist toggle from step 1
        to_save["auto_device_selection"] = self.auto_device_enabled

        # Simple validation for comfort range
        errors: dict[str, str] = {}
        try:
            min_t = float(to_save.get("min_comfort_temp", DEFAULT_MIN_COMFORT_TEMP))
            max_t = float(to_save.get("max_comfort_temp", DEFAULT_MAX_COMFORT_TEMP))
            if min_t >= max_t:
                errors["comfort"] = "min_must_be_below_max"
        except Exception:
            errors["comfort"] = "invalid"

        if errors:
            return self.async_show_form(step_id="options", data_schema=schema, errors=errors)

        return self.async_create_entry(title="", data=to_save)


@callback
def async_get_options_flow(
    config_entry: config_entries.ConfigEntry,
) -> AdaptiveClimateOptionsFlowHandler:
    """Get the options flow for this handler."""
    return AdaptiveClimateOptionsFlowHandler(config_entry)