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
from .template import async_register_template_functions
from .logbook import async_describe_events
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR, 
    Platform.BINARY_SENSOR, 
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Adaptive Climate from a config entry."""
    _LOGGER.debug("Setting up Adaptive Climate coordinator")
    
    # Initialize domain data
    hass.data.setdefault(DOMAIN, {})
    
    # Register custom template functions
    async_register_template_functions(hass)
    
    # Set up logbook integration
    await _async_setup_logbook(hass)
    
    # Create coordinator
    coordinator = AdaptiveClimateCoordinator(hass, entry.data, entry)
    
    # Store coordinator
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
    await async_setup_services(hass)
    
    # Add update listener for options flow
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    
    return True


async def _async_setup_logbook(hass: HomeAssistant) -> None:
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
            async_unload_services(hass)
    
    return unload_ok
