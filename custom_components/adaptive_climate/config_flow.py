"""Config flow for Adaptive Climate integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from .const import (
    DOMAIN,
    DEFAULT_COMFORT_CATEGORY,
    DEFAULT_MIN_COMFORT_TEMP,
    DEFAULT_MAX_COMFORT_TEMP,
    DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
    DEFAULT_AIR_VELOCITY,
    DEFAULT_NATURAL_VENTILATION_THRESHOLD,
    DEFAULT_SETBACK_TEMPERATURE_OFFSET,
    DEFAULT_PROLONGED_ABSENCE_MINUTES,
    DEFAULT_AUTO_SHUTDOWN_MINUTES,
    COMFORT_CATEGORIES,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="Adaptive Climate"): str,
        vol.Optional("area"): selector.AreaSelector(),
        vol.Required("climate_entity"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="climate")
        ),
        vol.Required("indoor_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"]
            )
        ),
        vol.Required("outdoor_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"]
            )
        ),
        vol.Optional("comfort_category", default=DEFAULT_COMFORT_CATEGORY): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": "I", "label": f"Category I {COMFORT_CATEGORIES['I']['description']}"},
                    {"value": "II", "label": f"Category II {COMFORT_CATEGORIES['II']['description']}"},
                    {"value": "III", "label": f"Category III {COMFORT_CATEGORIES['III']['description']}"},
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)

STEP_ADVANCED_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional("occupancy_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="binary_sensor",
                device_class=["motion", "occupancy", "presence"],
            )
        ),
        vol.Optional("mean_radiant_temp_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        vol.Optional("indoor_humidity_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        vol.Optional("outdoor_humidity_sensor"): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=["sensor", "input_number", "weather"]
            )
        ),
        vol.Optional("use_operative_temperature", default=False): bool,
        vol.Optional("energy_save_mode", default=True): bool,
        vol.Optional("comfort_precision_mode", default=False): bool,
        vol.Optional("use_occupancy_features", default=False): bool,
        vol.Optional("natural_ventilation_enable", default=True): bool,
        vol.Optional("adaptive_air_velocity", default=True): bool,
        vol.Optional("humidity_comfort_enable", default=True): bool,
        vol.Optional("auto_shutdown_enable", default=False): bool,
    }
)

STEP_THRESHOLDS_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional("min_comfort_temp", default=DEFAULT_MIN_COMFORT_TEMP): vol.All(
            vol.Coerce(float), vol.Range(min=15.0, max=22.0)
        ),
        vol.Optional("max_comfort_temp", default=DEFAULT_MAX_COMFORT_TEMP): vol.All(
            vol.Coerce(float), vol.Range(min=25.0, max=32.0)
        ),
        vol.Optional("temperature_change_threshold", default=DEFAULT_TEMPERATURE_CHANGE_THRESHOLD): vol.All(
            vol.Coerce(float), vol.Range(min=0.5, max=2.0)
        ),
        vol.Optional("air_velocity", default=DEFAULT_AIR_VELOCITY): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=2.0)
        ),
        vol.Optional("natural_ventilation_threshold", default=DEFAULT_NATURAL_VENTILATION_THRESHOLD): vol.All(
            vol.Coerce(float), vol.Range(min=0.5, max=5.0)
        ),
        vol.Optional("setback_temperature_offset", default=DEFAULT_SETBACK_TEMPERATURE_OFFSET): vol.All(
            vol.Coerce(float), vol.Range(min=1.0, max=5.0)
        ),
        vol.Optional("prolonged_absence_minutes", default=DEFAULT_PROLONGED_ABSENCE_MINUTES): vol.All(
            vol.Coerce(int), vol.Range(min=10, max=240)
        ),
        vol.Optional("auto_shutdown_minutes", default=DEFAULT_AUTO_SHUTDOWN_MINUTES): vol.All(
            vol.Coerce(int), vol.Range(min=15, max=480)
        ),
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Adaptive Climate."""

    VERSION = 1
    MINOR_VERSION = 0

    def __init__(self):
        """Initialize config flow."""
        self.config_data = {}
        self._reauth_entry = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        # Validate that entities exist
        registry = async_get_entity_registry(self.hass)
        for field in ["climate_entity", "indoor_temp_sensor", "outdoor_temp_sensor"]:
            entity_id = user_input[field]
            if not registry.async_is_registered(entity_id):
                if entity_id not in self.hass.states.async_entity_ids():
                    errors[field] = "entity_not_found"

        if errors:
            # Rebuild schema with area filter if area was selected
            selected_area = user_input.get("area")
            entity_filter = {}
            if selected_area:
                entity_filter["area"] = selected_area
            
            user_schema_with_area = vol.Schema(
                {
                    vol.Required(CONF_NAME, default=user_input.get(CONF_NAME, "Adaptive Climate")): str,
                    vol.Optional("area", default=selected_area): selector.AreaSelector(),
                    vol.Required("climate_entity", default=user_input.get("climate_entity", "")): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="climate", **entity_filter)
                    ),
                    vol.Required("indoor_temp_sensor", default=user_input.get("indoor_temp_sensor", "")): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor", "input_number", "weather"],
                            **entity_filter
                        )
                    ),
                    vol.Required("outdoor_temp_sensor", default=user_input.get("outdoor_temp_sensor", "")): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor", "input_number", "weather"]
                        )
                    ),
                    vol.Optional("comfort_category", default=user_input.get("comfort_category", DEFAULT_COMFORT_CATEGORY)): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": "I", "label": f"Category I {COMFORT_CATEGORIES['I']['description']}"},
                                {"value": "II", "label": f"Category II {COMFORT_CATEGORIES['II']['description']}"},
                                {"value": "III", "label": f"Category III {COMFORT_CATEGORIES['III']['description']}"},
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            )
            
            return self.async_show_form(
                step_id="user", data_schema=user_schema_with_area, errors=errors
            )

        self.config_data.update(user_input)
        return await self.async_step_advanced()

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle advanced options step.""" 
        if user_input is None:
            # Create dynamic schema based on selected area
            selected_area = self.config_data.get("area")
            
            # Build entity selectors with area filter if area is selected
            entity_filter = {}
            if selected_area:
                entity_filter["area"] = selected_area
            
            advanced_schema = vol.Schema(
                {
                    vol.Optional("occupancy_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="binary_sensor",
                            device_class=["motion", "occupancy", "presence"],
                            **entity_filter
                        )
                    ),
                    vol.Optional("mean_radiant_temp_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor", "input_number"],
                            **entity_filter
                        )
                    ),
                    vol.Optional("indoor_humidity_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor", "input_number"],
                            **entity_filter
                        )
                    ),
                    vol.Optional("outdoor_humidity_sensor"): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor", "input_number", "weather"]
                        )
                    ),
                    vol.Optional("use_operative_temperature", default=False): bool,
                    vol.Optional("energy_save_mode", default=True): bool,
                    vol.Optional("comfort_precision_mode", default=False): bool,
                    vol.Optional("use_occupancy_features", default=False): bool,
                    vol.Optional("natural_ventilation_enable", default=True): bool,
                    vol.Optional("adaptive_air_velocity", default=True): bool,
                    vol.Optional("humidity_comfort_enable", default=True): bool,
                    vol.Optional("auto_shutdown_enable", default=False): bool,
                }
            )
            
            return self.async_show_form(
                step_id="advanced", data_schema=advanced_schema
            )

        self.config_data.update(user_input)
        return await self.async_step_thresholds()

    async def async_step_thresholds(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle thresholds configuration step."""
        if user_input is None:
            return self.async_show_form(
                step_id="thresholds", data_schema=STEP_THRESHOLDS_DATA_SCHEMA
            )

        self.config_data.update(user_input)

        # Check if entry already exists
        await self.async_set_unique_id(self.config_data[CONF_NAME])
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=self.config_data[CONF_NAME], data=self.config_data
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Adaptive Climate."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options main menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["parameters", "thresholds", "features", "reset"]
        )

    async def async_step_parameters(self, user_input=None):
        """Handle main parameters configuration."""
        if user_input is not None:
            # Update coordinator with new options
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
            await coordinator.update_config(user_input)
            
            # Merge with existing options
            new_options = {**self.config_entry.options, **user_input}
            return self.async_create_entry(title="", data=new_options)

        # Get current values from coordinator
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        current_config = coordinator.config

        return self.async_show_form(
            step_id="parameters",
            data_schema=vol.Schema({
                vol.Optional(
                    "comfort_category", 
                    default=current_config.get("comfort_category", "II")
                ): vol.In(["I", "II", "III"]),
                vol.Optional(
                    "air_velocity", 
                    default=current_config.get("air_velocity", 0.1)
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),
                vol.Optional(
                    "use_operative_temperature",
                    default=current_config.get("use_operative_temperature", False)
                ): bool,
                vol.Optional(
                    "energy_save_mode",
                    default=current_config.get("energy_save_mode", True)
                ): bool,
            }),
            description_placeholders={
                "category_i": "±2°C (90% satisfaction)",
                "category_ii": "±3°C (80% satisfaction)", 
                "category_iii": "±4°C (65% satisfaction)",
            }
        )

    async def async_step_thresholds(self, user_input=None):
        """Handle thresholds configuration."""
        if user_input is not None:
            # Update coordinator with new options
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
            await coordinator.update_config(user_input)
            
            # Merge with existing options
            new_options = {**self.config_entry.options, **user_input}
            return self.async_create_entry(title="", data=new_options)

        # Get current values from coordinator
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        current_config = coordinator.config

        return self.async_show_form(
            step_id="thresholds",
            data_schema=vol.Schema({
                vol.Optional(
                    "temperature_change_threshold",
                    default=current_config.get("temperature_change_threshold", 1.0)
                ): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=3.0)),
                vol.Optional(
                    "natural_ventilation_threshold",
                    default=current_config.get("natural_ventilation_threshold", 2.0)
                ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=10.0)),
                vol.Optional(
                    "setback_temperature_offset",
                    default=current_config.get("setback_temperature_offset", 2.0)
                ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=5.0)),
                vol.Optional(
                    "min_comfort_temp",
                    default=current_config.get("min_comfort_temp", 18.0)
                ): vol.All(vol.Coerce(float), vol.Range(min=15.0, max=22.0)),
                vol.Optional(
                    "max_comfort_temp",
                    default=current_config.get("max_comfort_temp", 28.0)
                ): vol.All(vol.Coerce(float), vol.Range(min=25.0, max=32.0)),
            })
        )

    async def async_step_features(self, user_input=None):
        """Handle features configuration."""
        if user_input is not None:
            # Update coordinator with new options
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
            await coordinator.update_config(user_input)
            
            # Merge with existing options
            new_options = {**self.config_entry.options, **user_input}
            return self.async_create_entry(title="", data=new_options)

        # Get current values from coordinator
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        current_config = coordinator.config

        return self.async_show_form(
            step_id="features",
            data_schema=vol.Schema({
                vol.Optional(
                    "adaptive_air_velocity",
                    default=current_config.get("adaptive_air_velocity", False)
                ): bool,
                vol.Optional(
                    "natural_ventilation_enable",
                    default=current_config.get("natural_ventilation_enable", True)
                ): bool,
                vol.Optional(
                    "humidity_comfort_enable",
                    default=current_config.get("humidity_comfort_enable", True)
                ): bool,
                vol.Optional(
                    "comfort_precision_mode",
                    default=current_config.get("comfort_precision_mode", False)
                ): bool,
                vol.Optional(
                    "use_occupancy_features",
                    default=current_config.get("use_occupancy_features", False)
                ): bool,
                vol.Optional(
                    "auto_shutdown_enable",
                    default=current_config.get("auto_shutdown_enable", False)
                ): bool,
            })
        )

    async def async_step_reset(self, user_input=None):
        """Handle reset options."""
        if user_input is not None:
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
            
            if user_input.get("reset_outdoor_history", False):
                await coordinator.reset_outdoor_history()
            
            if user_input.get("reset_to_defaults", False):
                # Reset to default values
                default_config = {
                    "comfort_category": "II",
                    "air_velocity": 0.1,
                    "temperature_change_threshold": 1.0,
                    "natural_ventilation_threshold": 2.0,
                    "setback_temperature_offset": 2.0,
                    "min_comfort_temp": 18.0,
                    "max_comfort_temp": 28.0,
                    "adaptive_air_velocity": False,
                    "natural_ventilation_enable": True,
                    "humidity_comfort_enable": True,
                    "comfort_precision_mode": False,
                    "use_occupancy_features": False,
                    "auto_shutdown_enable": False,
                    "energy_save_mode": True,
                    "use_operative_temperature": False,
                }
                await coordinator.update_config(default_config)
                return self.async_create_entry(title="", data=default_config)
            
            return self.async_create_entry(title="", data=self.config_entry.options)

        return self.async_show_form(
            step_id="reset",
            data_schema=vol.Schema({
                vol.Optional("reset_outdoor_history", default=False): bool,
                vol.Optional("reset_to_defaults", default=False): bool,
            }),
            description_placeholders={
                "warning": "Reset operations cannot be undone!"
            }
        )
