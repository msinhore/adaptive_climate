"""Services for Adaptive Climate integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import AdaptiveClimateCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_CLEAR_OVERRIDE = "clear_override"
SERVICE_SET_COMFORT_CATEGORY = "set_comfort_category"
SERVICE_UPDATE_CALCULATIONS = "update_calculations"
SERVICE_SET_TEMPORARY_OVERRIDE = "set_temporary_override"
SERVICE_UPDATE_CONFIG = "update_config"
SERVICE_RESET_OUTDOOR_HISTORY = "reset_outdoor_history"

CLEAR_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
    }
)

SET_COMFORT_CATEGORY_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required("category"): vol.In(["I", "II", "III"]),
    }
)

UPDATE_CALCULATIONS_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
    }
)

SET_TEMPORARY_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Optional("temperature"): vol.All(vol.Coerce(float), vol.Range(min=10, max=40)),
        vol.Optional("hvac_mode"): vol.In(["heat", "cool", "auto", "fan_only", "off"]),
        vol.Optional("duration_hours"): vol.All(vol.Coerce(int), vol.Range(min=1, max=24)),
    }
)

UPDATE_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Optional("air_velocity"): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=2.0)),
        vol.Optional("natural_ventilation_threshold"): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=5.0)),
        vol.Optional("temperature_change_threshold"): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=3.0)),
        vol.Optional("setback_temperature_offset"): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=5.0)),
        vol.Optional("adaptive_air_velocity"): cv.boolean,
    }
)

RESET_OUTDOOR_HISTORY_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Adaptive Climate."""
    
    async def async_clear_override(call: ServiceCall) -> None:
        """Clear manual override for specified config entry."""
        config_entry_id = call.data.get("config_entry_id")
        coordinator: AdaptiveClimateCoordinator = hass.data[DOMAIN].get(config_entry_id)
        
        if coordinator:
            await coordinator.clear_manual_override()
            _LOGGER.info("Manual override cleared for config entry %s", config_entry_id)
        else:
            _LOGGER.error("Coordinator not found for config entry %s", config_entry_id)

    async def async_set_comfort_category(call: ServiceCall) -> None:
        """Set comfort category for specified config entry."""
        config_entry_id = call.data.get("config_entry_id")
        category = call.data.get("category")
        coordinator: AdaptiveClimateCoordinator = hass.data[DOMAIN].get(config_entry_id)
        
        if coordinator:
            await coordinator.set_comfort_category(category)
            _LOGGER.info("Comfort category set to %s for config entry %s", category, config_entry_id)
        else:
            _LOGGER.error("Coordinator not found for config entry %s", config_entry_id)

    async def async_update_calculations(call: ServiceCall) -> None:
        """Force update calculations for specified config entry."""
        config_entry_id = call.data.get("config_entry_id")
        coordinator: AdaptiveClimateCoordinator = hass.data[DOMAIN].get(config_entry_id)
        
        if coordinator:
            await coordinator.async_refresh()
            _LOGGER.info("Calculations updated for config entry %s", config_entry_id)
        else:
            _LOGGER.error("Coordinator not found for config entry %s", config_entry_id)

    async def async_set_temporary_override(call: ServiceCall) -> None:
        """Set temporary override for specified config entry."""
        config_entry_id = call.data.get("config_entry_id")
        temperature = call.data.get("temperature")
        hvac_mode = call.data.get("hvac_mode")
        duration_hours = call.data.get("duration_hours", 1)
        coordinator: AdaptiveClimateCoordinator = hass.data[DOMAIN].get(config_entry_id)
        
        if coordinator:
            await coordinator.set_temporary_override(
                temperature=temperature,
                hvac_mode=hvac_mode,
                duration_hours=duration_hours,
            )
            _LOGGER.info(
                "Temporary override set for config entry %s: temp=%s, mode=%s, duration=%dh",
                config_entry_id, temperature, hvac_mode, duration_hours
            )
        else:
            _LOGGER.error("Coordinator not found for config entry %s", config_entry_id)

    async def async_update_config(call: ServiceCall) -> None:
        """Update configuration for specified config entry."""
        config_entry_id = call.data.get("config_entry_id")
        coordinator: AdaptiveClimateCoordinator = hass.data[DOMAIN].get(config_entry_id)
        
        if coordinator:
            # Update config with new values (excluding config_entry_id)
            config_updates = {k: v for k, v in call.data.items() if k != "config_entry_id"}
            await coordinator.update_config(config_updates)
            _LOGGER.info("Configuration updated for config entry %s: %s", config_entry_id, config_updates)
        else:
            _LOGGER.error("Coordinator not found for config entry %s", config_entry_id)

    async def async_reset_outdoor_history(call: ServiceCall) -> None:
        """Reset outdoor temperature history for specified config entry."""
        config_entry_id = call.data.get("config_entry_id")
        coordinator: AdaptiveClimateCoordinator = hass.data[DOMAIN].get(config_entry_id)
        
        if coordinator:
            await coordinator.reset_outdoor_history()
            _LOGGER.info("Outdoor temperature history reset for config entry %s", config_entry_id)
        else:
            _LOGGER.error("Coordinator not found for config entry %s", config_entry_id)

    # Register services
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_OVERRIDE, async_clear_override, schema=CLEAR_OVERRIDE_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_SET_COMFORT_CATEGORY, async_set_comfort_category, 
        schema=SET_COMFORT_CATEGORY_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_UPDATE_CALCULATIONS, async_update_calculations,
        schema=UPDATE_CALCULATIONS_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_SET_TEMPORARY_OVERRIDE, async_set_temporary_override,
        schema=SET_TEMPORARY_OVERRIDE_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_UPDATE_CONFIG, async_update_config,
        schema=UPDATE_CONFIG_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_RESET_OUTDOOR_HISTORY, async_reset_outdoor_history,
        schema=RESET_OUTDOOR_HISTORY_SCHEMA
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services for Adaptive Climate."""
    hass.services.async_remove(DOMAIN, SERVICE_CLEAR_OVERRIDE)
    hass.services.async_remove(DOMAIN, SERVICE_SET_COMFORT_CATEGORY)
    hass.services.async_remove(DOMAIN, SERVICE_UPDATE_CALCULATIONS)
    hass.services.async_remove(DOMAIN, SERVICE_SET_TEMPORARY_OVERRIDE)
    hass.services.async_remove(DOMAIN, SERVICE_UPDATE_CONFIG)
    hass.services.async_remove(DOMAIN, SERVICE_RESET_OUTDOOR_HISTORY)
