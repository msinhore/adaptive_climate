"""Config flow for Adaptive Climate integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import selector
from homeassistant.helpers.entity_registry import (
    async_get as async_get_entity_registry,
)

from custom_components.adaptive_climate.const import (
    COMFORT_CATEGORIES,
    DEFAULT_COMFORT_CATEGORY,
    DEFAULT_ENABLE_COOL_MODE,
    DEFAULT_ENABLE_DRY_MODE,
    DEFAULT_ENABLE_FAN_MODE,
    DEFAULT_ENABLE_HEAT_MODE,
    DEFAULT_ENABLE_OFF_MODE,
    DEFAULT_MANUAL_PAUSE_DURATION,
    DEFAULT_MAX_FAN_SPEED,
    DEFAULT_MIN_FAN_SPEED,
    DOMAIN,
    FAN_SPEED_OPTIONS,
    HVAC_MODE_OPTIONS,
)
from custom_components.adaptive_climate.options_flow import async_get_options_flow

_LOGGER = logging.getLogger(__name__)

# Area-based setup schema (single step, minimal)
AREA_SCHEMA = vol.Schema(
    {
        # Name is required; default empty so the user types a friendly name
        vol.Required(CONF_NAME, default=""): str,
        vol.Required("area"): selector.AreaSelector(
            selector.AreaSelectorConfig()
        ),
        vol.Required("indoor_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"],
                device_class=["temperature"],
            )
        ),
        vol.Required("outdoor_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"],
                device_class=["temperature", "weather"],
            )
        ),
        vol.Optional("indoor_humidity_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number"],
                device_class=["humidity"],
            )
        ),
        vol.Optional("outdoor_humidity_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"],
                device_class=["humidity"],
            )
        ),
    }
)

# Config Schema for initial setup - only essential entities (Single device)
CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="Adaptive Climate"): str,
        vol.Required("climate_entity"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="climate")
        ),
        vol.Required("indoor_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"],
                device_class=["temperature"],
            )
        ),
        vol.Required("outdoor_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"],
                device_class=["temperature", "weather"],
            )
        ),
        vol.Optional(
            "comfort_category", default=DEFAULT_COMFORT_CATEGORY
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {
                        "value": "I",
                        "label": f"Category I - {COMFORT_CATEGORIES['I']['description']}",
                    },
                    {
                        "value": "II",
                        "label": f"Category II - {COMFORT_CATEGORIES['II']['description']}",
                    },
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional("min_comfort_temp", default=21): vol.All(
            vol.Coerce(float), vol.Range(min=10.0, max=30.0)
        ),
        vol.Optional("max_comfort_temp", default=27): vol.All(
            vol.Coerce(float), vol.Range(min=15.0, max=35.0)
        ),
        vol.Optional("temperature_change_threshold", default=0.5): vol.All(
            vol.Coerce(float), vol.Range(min=0.1, max=5.0)
        ),
        vol.Optional("override_temperature", default=0): vol.All(
            vol.Coerce(float), vol.Range(min=-2, max=2)
        ),
        vol.Optional("energy_save_mode", default=True): bool,
        vol.Optional("auto_mode_enable", default=True): bool,
        vol.Optional("aggressive_cooling_threshold", default=2.0): vol.All(
            vol.Coerce(float), vol.Range(min=0.5, max=10.0)
        ),
        vol.Optional("aggressive_heating_threshold", default=2.0): vol.All(
            vol.Coerce(float), vol.Range(min=0.5, max=10.0)
        ),
        # === HVAC and Fan Control ===
        vol.Optional("enable_fan_mode", default=DEFAULT_ENABLE_FAN_MODE): bool,
        vol.Optional(
            "enable_cool_mode", default=DEFAULT_ENABLE_COOL_MODE
        ): bool,
        vol.Optional(
            "enable_heat_mode", default=DEFAULT_ENABLE_HEAT_MODE
        ): bool,
        vol.Optional("enable_dry_mode", default=DEFAULT_ENABLE_DRY_MODE): bool,
        vol.Optional("enable_off_mode", default=DEFAULT_ENABLE_OFF_MODE): bool,
        vol.Optional("max_fan_speed", default=DEFAULT_MAX_FAN_SPEED): vol.In(
            list(FAN_SPEED_OPTIONS.keys())
        ),
        vol.Optional("min_fan_speed", default=DEFAULT_MIN_FAN_SPEED): vol.In(
            list(FAN_SPEED_OPTIONS.keys())
        ),
        # Participation in area orchestration (optional, can also be toggled in options)
        vol.Optional("participate_area_orchestration", default=False): bool,
    }
)

# Bulk add schema - multi device selection sharing same sensors
BULK_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="Adaptive Climate"): str,
        vol.Required("climate_entities"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="climate", multiple=True)
        ),
        vol.Required("indoor_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"],
                device_class=["temperature"],
            )
        ),
        vol.Required("outdoor_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"],
                device_class=["temperature", "weather"],
            )
        ),
        vol.Optional("indoor_humidity_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number"],
                device_class=["humidity"],
            )
        ),
        vol.Optional("outdoor_humidity_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"],
                device_class=["humidity"],
            )
        ),
        vol.Optional(
            "comfort_category", default=DEFAULT_COMFORT_CATEGORY
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {
                        "value": "I",
                        "label": f"Category I - {COMFORT_CATEGORIES['I']['description']}",
                    },
                    {
                        "value": "II",
                        "label": f"Category II - {COMFORT_CATEGORIES['II']['description']}",
                    },
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional("min_comfort_temp", default=21): vol.All(
            vol.Coerce(float), vol.Range(min=10.0, max=30.0)
        ),
        vol.Optional("max_comfort_temp", default=27): vol.All(
            vol.Coerce(float), vol.Range(min=15.0, max=35.0)
        ),
        vol.Optional("temperature_change_threshold", default=0.5): vol.All(
            vol.Coerce(float), vol.Range(min=0.1, max=5.0)
        ),
        vol.Optional("override_temperature", default=0): vol.All(
            vol.Coerce(float), vol.Range(min=-2, max=2)
        ),
        vol.Optional("energy_save_mode", default=True): bool,
        vol.Optional("auto_mode_enable", default=True): bool,
        vol.Optional("aggressive_cooling_threshold", default=2.0): vol.All(
            vol.Coerce(float), vol.Range(min=0.5, max=10.0)
        ),
        vol.Optional("aggressive_heating_threshold", default=2.0): vol.All(
            vol.Coerce(float), vol.Range(min=0.5, max=10.0)
        ),
        vol.Optional("enable_fan_mode", default=DEFAULT_ENABLE_FAN_MODE): bool,
        vol.Optional(
            "enable_cool_mode", default=DEFAULT_ENABLE_COOL_MODE
        ): bool,
        vol.Optional(
            "enable_heat_mode", default=DEFAULT_ENABLE_HEAT_MODE
        ): bool,
        vol.Optional("enable_dry_mode", default=DEFAULT_ENABLE_DRY_MODE): bool,
        vol.Optional("enable_off_mode", default=DEFAULT_ENABLE_OFF_MODE): bool,
        vol.Optional("max_fan_speed", default=DEFAULT_MAX_FAN_SPEED): vol.In(
            list(FAN_SPEED_OPTIONS.keys())
        ),
        vol.Optional("min_fan_speed", default=DEFAULT_MIN_FAN_SPEED): vol.In(
            list(FAN_SPEED_OPTIONS.keys())
        ),
        vol.Optional("participate_area_orchestration", default=False): bool,
    }
)

# Optional sensors schema for second step
OPTIONAL_SENSORS_SCHEMA = vol.Schema(
    {
        vol.Optional("indoor_humidity_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number"], device_class=["humidity"]
            )
        ),
        vol.Optional("outdoor_humidity_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"],
                device_class=["humidity"],
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
        """Preferred: area-based setup. Creates/updates one entry per climate in the area."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=AREA_SCHEMA
            )

        # Do not hard-fail on sensor validation here; sensors will be validated per entry later

        area_raw = user_input.get("area")
        # Normalize AreaSelector return (string area_id or dict)
        area_id = None
        if isinstance(area_raw, str):
            area_id = area_raw
        elif isinstance(area_raw, dict):
            area_id = (
                area_raw.get("area_id")
                or area_raw.get("id")
                or area_raw.get("area")
            )
        _LOGGER.debug(
            f"Area-based setup: received area input={area_raw}, normalized area_id={area_id}"
        )
        if not area_id:
            return self.async_show_form(
                step_id="user",
                data_schema=AREA_SCHEMA,
                errors={"base": "area_not_found"},
            )

        # Scan area for climate entities
        try:
            climates = self._find_climates_in_area(area_id)
        except Exception as e:
            _LOGGER.error(f"Failed to find climates in area {area_id}: {e}")
            climates = []
        if not climates:
            return self.async_show_form(
                step_id="user",
                data_schema=AREA_SCHEMA,
                errors={"base": "no_climates_in_area"},
            )

        base = {k: v for k, v in user_input.items() if k not in ("area",)}
        base["area_id"] = area_id

        for climate in sorted(climates):
            data = {**base, "climate_entity": climate}
            await self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data=data,
            )

        return self.async_abort(reason="created_multiple_entries")

    async def async_step_single(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Simplified single device setup (name + required sensors)."""
        minimal_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=""): str,
                vol.Required("climate_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="climate")
                ),
                vol.Required("indoor_temp_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number", "weather"],
                        device_class=["temperature"],
                    )
                ),
                vol.Required("outdoor_temp_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number", "weather"],
                        device_class=["temperature", "weather"],
                    )
                ),
                vol.Optional("indoor_humidity_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number"], device_class=["humidity"]
                    )
                ),
                vol.Optional("outdoor_humidity_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "input_number", "weather"],
                        device_class=["humidity"],
                    )
                ),
            }
        )

        if user_input is None:
            return self.async_show_form(step_id="single", data_schema=minimal_schema)

        errors: dict[str, str] = {}
        for field in ["climate_entity", "indoor_temp_sensor", "outdoor_temp_sensor"]:
            entity_id = user_input.get(field)
            if not entity_id or entity_id not in self.hass.states.async_entity_ids():
                errors[field] = "entity_not_found"

        if errors:
            return self.async_show_form(step_id="single", data_schema=minimal_schema, errors=errors)

        self.config_data.update(user_input)
        return await self.async_step_optional_sensors()

    async def async_step_bulk(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Bulk add multiple climate entities with shared sensors/settings."""
        if user_input is None:
            return self.async_show_form(
                step_id="bulk", data_schema=BULK_SCHEMA
            )

        errors: dict[str, str] = {}
        climates: list[str] = user_input.get("climate_entities") or []
        if not climates:
            errors["climate_entities"] = "entity_not_found"

        # Validate sensors exist
        for field in [
            "indoor_temp_sensor",
            "outdoor_temp_sensor",
        ]:
            entity_id = user_input.get(field)
            if (
                not entity_id
                or entity_id not in self.hass.states.async_entity_ids()
            ):
                errors[field] = "entity_not_found"

        if errors:
            return self.async_show_form(
                step_id="bulk", data_schema=BULK_SCHEMA, errors=errors
            )

        base = {k: v for k, v in user_input.items() if k != "climate_entities"}

        # Create/update entries via import flow, one per climate
        for climate in climates:
            data = {**base, "climate_entity": climate}
            await self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data=data,
            )

        # Abort this flow signaling multiple entries created/updated
        return self.async_abort(reason="created_multiple_entries")

    async def async_step_optional_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle optional sensors step."""
        if user_input is None:
            return self.async_show_form(
                step_id="optional_sensors", data_schema=OPTIONAL_SENSORS_SCHEMA
            )

        # Update config data with optional sensors
        self.config_data.update(user_input)

        # Create unique ID based on climate entity to prevent duplicates
        unique_id = f"adaptive_climate_{self.config_data['climate_entity'].replace('.', '_')}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(
            updates={CONF_NAME: self.config_data[CONF_NAME]}
        )

        # Use the user-provided name as the entry title
        title = self.config_data.get(CONF_NAME, "Adaptive Climate")
        return self.async_create_entry(title=title, data=self.config_data)

    async def async_step_import(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle configuration by YAML/bulk import creating a per-climate entry."""
        assert user_input is not None

        # Unique per climate
        unique_id = f"adaptive_climate_{user_input['climate_entity'].replace('.', '_')}"
        await self.async_set_unique_id(unique_id)
        for entry in self._async_current_entries():
            if entry.unique_id == self.unique_id:
                # Update existing entry data to keep in sync
                self.hass.config_entries.async_update_entry(
                    entry, data=user_input
                )
                self._abort_if_unique_id_configured()

        # Use the user-provided name as the entry title (also for bulk/area import)
        title = user_input.get(CONF_NAME, "Adaptive Climate")
        return self.async_create_entry(title=title, data=user_input)

    def _find_climates_in_area(self, area_id: str) -> list[str]:
        """Find all climate entities in a given area (by entity area or device area)."""
        ent_reg = async_get_entity_registry(self.hass)
        dev_reg = dr.async_get(self.hass)
        result: list[str] = []
        for entity in list(ent_reg.entities.values()):
            if entity.domain != "climate":
                continue
            if entity.area_id == area_id:
                result.append(entity.entity_id)
                continue
            if entity.device_id:
                device = dev_reg.async_get(entity.device_id)
                if device and device.area_id == area_id:
                    result.append(entity.entity_id)
        return result
