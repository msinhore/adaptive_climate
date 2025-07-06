"""The Adaptive Climate component."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    EVENT_ADAPTIVE_CLIMATE_MODE_CHANGE,
    EVENT_ADAPTIVE_CLIMATE_TARGET_TEMP,
)
from .coordinator import AdaptiveClimateCoordinator
from .logbook import async_describe_events
from .const import VERSION
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SWITCH, Platform.SELECT]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Adaptive Climate component."""
    hass.data.setdefault(DOMAIN, {})

    # This approach avoids any reference to hass.components
    async def _setup_logbook():
        """Set up logbook integration."""
        try:
            # Dynamic import to avoid dependency issues
            import importlib
            
            try:
                # Try to import logbook module
                logbook_module = importlib.import_module("homeassistant.components.logbook")
                
                # Check if the registration function exists
                if hasattr(logbook_module, "async_register_event_type"):
                    # Register event types
                    logbook_module.async_register_event_type(
                        hass,
                        EVENT_ADAPTIVE_CLIMATE_MODE_CHANGE,
                        "changed HVAC mode",
                    )
                    logbook_module.async_register_event_type(
                        hass,
                        EVENT_ADAPTIVE_CLIMATE_TARGET_TEMP, 
                        "changed target temperature",
                    )
                    _LOGGER.debug("Successfully registered logbook event types")
                else:
                    _LOGGER.debug("Logbook module found but missing registration function")
            except (ImportError, ModuleNotFoundError):
                _LOGGER.debug("Could not import logbook module")
        except Exception as err:
            _LOGGER.debug("Error setting up logbook integration: %s", err)
    
    # Call the setup function but don't block on it
    hass.async_create_task(_setup_logbook())
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Adaptive Climate from a config entry."""
    _LOGGER.debug("Setting up Adaptive Climate coordinator")
    
    # Create coordinator
    coordinator = AdaptiveClimateCoordinator(hass, entry.data)
    
    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Perform initial data fetch with retry logic
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.warning("Initial data fetch failed, will retry on next update: %s", err)
        # Don't fail setup, just log and continue - sensors will show as unavailable until data is available
    
    # Set up platforms (sensors only, no climate entity)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Set up services
    await _async_setup_services(hass, coordinator)
    
    # Add update listener for options flow
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener for options flow."""
    _LOGGER.debug("Updating Adaptive Climate coordinator with new options")
    try:
        coordinator = hass.data[DOMAIN][entry.entry_id]
        
        # Update coordinator configuration
        await coordinator.update_config({**entry.data, **entry.options})
        
        # Request refresh to apply new configuration
        await coordinator.async_request_refresh()
    except Exception as err:
        _LOGGER.error("Error updating coordinator configuration: %s", err)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Adaptive Climate coordinator")
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        
        # Clean up coordinator
        if hasattr(coordinator, 'async_shutdown'):
            await coordinator.async_shutdown()
        
        # Remove services if this was the last entry
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "clear_override")
            hass.services.async_remove(DOMAIN, "set_comfort_category")
            hass.services.async_remove(DOMAIN, "update_calculations")
            hass.services.async_remove(DOMAIN, "set_temporary_override")
    
    return unload_ok


async def _async_setup_services(hass: HomeAssistant, coordinator: AdaptiveClimateCoordinator) -> None:
    """Set up services for the coordinator."""
    
    async def clear_override_service(call):
        """Clear manual override."""
        await coordinator.clear_manual_override()
    
    async def set_comfort_category_service(call):
        """Set comfort category."""
        category = call.data.get("category")
        if category:
            await coordinator.update_comfort_category(category)
    
    async def update_calculations_service(call):
        """Force update calculations."""
        await coordinator.async_request_refresh()
    
    async def set_temporary_override_service(call):
        """Set temporary override."""
        temperature = call.data.get("temperature")
        duration = call.data.get("duration")
        if temperature:
            await coordinator.set_manual_override(temperature, duration)
    
    # Register services (only once for the domain)
    if not hass.services.has_service(DOMAIN, "clear_override"):
        hass.services.async_register(DOMAIN, "clear_override", clear_override_service)
        hass.services.async_register(DOMAIN, "set_comfort_category", set_comfort_category_service)
        hass.services.async_register(DOMAIN, "update_calculations", update_calculations_service)
        hass.services.async_register(DOMAIN, "set_temporary_override", set_temporary_override_service)
