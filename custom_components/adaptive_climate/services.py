"""Services for Adaptive Climate integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_CLEAR_OVERRIDE = "clear_override"
SERVICE_SET_COMFORT_CATEGORY = "set_comfort_category"
SERVICE_UPDATE_CALCULATIONS = "update_calculations"
SERVICE_SET_TEMPORARY_OVERRIDE = "set_temporary_override"

CLEAR_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_ids,
    }
)

SET_COMFORT_CATEGORY_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_ids,
        vol.Required("category"): vol.In(["I", "II", "III"]),
    }
)

UPDATE_CALCULATIONS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_ids,
    }
)

SET_TEMPORARY_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_ids,
        vol.Optional("temperature"): vol.All(vol.Coerce(float), vol.Range(min=10, max=40)),
        vol.Optional("hvac_mode"): vol.In(["heat", "cool", "auto", "fan_only", "off"]),
        vol.Optional("duration_hours"): vol.All(vol.Coerce(int), vol.Range(min=1, max=24)),
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Adaptive Climate."""
    
    async def async_clear_override(call: ServiceCall) -> None:
        """Clear manual override for specified entities."""
        entity_ids = call.data.get("entity_id", [])
        component: EntityComponent = hass.data[DOMAIN]
        
        for entity_id in entity_ids:
            entity = component.get_entity(entity_id)
            if entity and hasattr(entity, "clear_manual_override"):
                await entity.clear_manual_override()
                _LOGGER.info("Manual override cleared for %s", entity_id)

    async def async_set_comfort_category(call: ServiceCall) -> None:
        """Set comfort category for specified entities."""
        entity_ids = call.data.get("entity_id", [])
        category = call.data.get("category")
        component: EntityComponent = hass.data[DOMAIN]
        
        for entity_id in entity_ids:
            entity = component.get_entity(entity_id)
            if entity and hasattr(entity, "set_comfort_category"):
                await entity.set_comfort_category(category)
                _LOGGER.info("Comfort category set to %s for %s", category, entity_id)

    async def async_update_calculations(call: ServiceCall) -> None:
        """Force update calculations for specified entities."""
        entity_ids = call.data.get("entity_id", [])
        component: EntityComponent = hass.data[DOMAIN]
        
        for entity_id in entity_ids:
            entity = component.get_entity(entity_id)
            if entity and hasattr(entity, "force_update_calculations"):
                await entity.force_update_calculations()
                _LOGGER.info("Calculations updated for %s", entity_id)

    async def async_set_temporary_override(call: ServiceCall) -> None:
        """Set temporary override for specified entities."""
        entity_ids = call.data.get("entity_id", [])
        temperature = call.data.get("temperature")
        hvac_mode = call.data.get("hvac_mode")
        duration_hours = call.data.get("duration_hours", 1)
        component: EntityComponent = hass.data[DOMAIN]
        
        for entity_id in entity_ids:
            entity = component.get_entity(entity_id)
            if entity and hasattr(entity, "set_temporary_override"):
                await entity.set_temporary_override(
                    temperature=temperature,
                    hvac_mode=hvac_mode,
                    duration_hours=duration_hours,
                )
                _LOGGER.info(
                    "Temporary override set for %s: temp=%s, mode=%s, duration=%dh",
                    entity_id, temperature, hvac_mode, duration_hours
                )

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


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services for Adaptive Climate."""
    hass.services.async_remove(DOMAIN, SERVICE_CLEAR_OVERRIDE)
    hass.services.async_remove(DOMAIN, SERVICE_SET_COMFORT_CATEGORY)
    hass.services.async_remove(DOMAIN, SERVICE_UPDATE_CALCULATIONS)
    hass.services.async_remove(DOMAIN, SERVICE_SET_TEMPORARY_OVERRIDE)
