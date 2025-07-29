"""The Adaptive Climate component."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import DOMAIN
from .coordinator import AdaptiveClimateCoordinator

_LOGGER = logging.getLogger(__name__)

# Configuration schema for YAML setup
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(cv.ensure_list, [
            vol.Schema({
                vol.Required("entity"): cv.entity_id,
            })
        ])
    },
    extra=vol.ALLOW_EXTRA,
)

# Supported platforms
PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
]


async def handle_reset_override_service(call) -> None:
    """Handle reset override service call."""
    hass = call.hass
    entity_id = call.data.get("entity_id")
    
    if not entity_id:
        _LOGGER.error("No entity_id provided for reset_override service")
        return
    
    coordinator = hass.data[DOMAIN]["coordinators"].get(entity_id)
    if coordinator:
        _LOGGER.debug(f"[{coordinator.device_name}] Resetting override via service call")
        await coordinator.async_reset_override()
    else:
        _LOGGER.error(f"Could not find coordinator for entity {entity_id}")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Adaptive Climate from YAML configuration."""
    _LOGGER.debug("Setting up Adaptive Climate from YAML configuration")
    
    # Initialize data structure to avoid overwriting configs
    hass.data.setdefault(DOMAIN, {"configs": {}, "coordinators": {}})

    entries = config.get(DOMAIN, [])
    _LOGGER.debug(f"Adaptive Climate YAML entries loaded: {len(entries)} entries")

    hass.data[DOMAIN]["configs"] = {}

    # Process YAML entries
    for entry in entries:
        if isinstance(entry, dict) and "entity" in entry:
            entity_id = entry["entity"]
            hass.data[DOMAIN]["configs"][entity_id] = entry
            _LOGGER.debug(f"Added YAML config for entity: {entity_id}")
        else:
            _LOGGER.error(f"Invalid YAML entry for Adaptive Climate: {entry}")

    # Create and store coordinators
    for entity_id, config_entry in hass.data[DOMAIN]["configs"].items():
        if "entity" not in config_entry:
            _LOGGER.error(f"Skipping entry '{entity_id}' - Missing required 'entity' definition in YAML configuration.")
            continue

        try:
            coordinator = AdaptiveClimateCoordinator(hass, config_entry)
            coordinator.primary_entity_id = config_entry["entity"]
            hass.data[DOMAIN]["coordinators"][entity_id] = coordinator
            
            _LOGGER.debug(f"[{coordinator.device_name}] YAML coordinator created successfully")
            
            # Perform initial data fetch
            await coordinator.async_config_entry_first_refresh()
            
        except Exception as e:
            _LOGGER.error(f"Failed to create coordinator for entity {entity_id}: {e}")
            continue

    # Register services
    hass.services.async_register(DOMAIN, "reset_override", handle_reset_override_service)
    
    _LOGGER.info(f"Adaptive Climate YAML setup completed - {len(hass.data[DOMAIN]['coordinators'])} coordinators created")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Adaptive Climate from a Config Entry (UI-based)."""
    _LOGGER.debug(f"Setting up Adaptive Climate from Config Entry: {entry.title}")
    
    # Validate required fields
    if not entry.data.get("entity") and not entry.data.get("climate_entity"):
        _LOGGER.warning(
            f"Config Entry '{entry.title}' lacks 'entity' or 'climate_entity'. Skipping Adaptive Climate setup."
        )
        return False

    entity_id = entry.data.get("entity") or entry.data.get("climate_entity")
    yaml_configs = hass.data.get(DOMAIN, {}).get("configs", {})

    # Check if entity is already configured via YAML
    if entity_id in yaml_configs:
        _LOGGER.info(
            f"Config Entry '{entry.title}' ignored: '{entity_id}' configured via YAML. YAML takes precedence."
        )
        return False

    try:
        # Create coordinator
        coordinator = AdaptiveClimateCoordinator(hass, entry.data, entry.options)
        _LOGGER.debug(f"[{coordinator.device_name}] Config Entry coordinator created successfully")
        
        # Store coordinator
        hass.data[DOMAIN]["coordinators"][entry.entry_id] = coordinator
        
        # Perform initial data fetch with retry logic
        try:
            await coordinator.async_config_entry_first_refresh()
            _LOGGER.debug(f"[{coordinator.device_name}] Initial data fetch completed")
        except Exception as err:
            _LOGGER.warning(f"[{coordinator.device_name}] Initial data fetch failed, will retry on next update: {err}")
            # Don't fail setup, just log and continue - sensors will show as unavailable until data is available
        
        # Set up platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        _LOGGER.debug(f"[{coordinator.device_name}] Platforms setup completed")
        
        # Set up services
        await _async_setup_services(hass, coordinator)
        _LOGGER.debug(f"[{coordinator.device_name}] Services setup completed")
        
        # Add update listener for options flow
        entry.async_on_unload(entry.add_update_listener(_async_update_listener))
        
        _LOGGER.info(f"[{coordinator.device_name}] Config Entry setup completed successfully")
        return True
        
    except Exception as e:
        _LOGGER.error(f"Failed to setup Config Entry '{entry.title}': {e}")
        return False


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener for options flow."""
    _LOGGER.debug(f"Updating Adaptive Climate coordinator with new options for entry: {entry.title}")
    
    try:
        coordinator = hass.data[DOMAIN]["coordinators"][entry.entry_id]
        _LOGGER.debug(f"[{coordinator.device_name}] Updating configuration from options flow")
        
        # Update coordinator configuration
        await coordinator.update_config({**entry.data, **entry.options})
        
        # Request refresh to apply new configuration
        await coordinator.async_request_refresh()
        
        _LOGGER.debug(f"[{coordinator.device_name}] Configuration update completed successfully")
        
    except KeyError:
        _LOGGER.error(f"Could not find coordinator for entry {entry.entry_id}")
    except Exception as err:
        _LOGGER.error(f"Error updating coordinator configuration: {err}")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(f"Unloading Adaptive Climate coordinator for entry: {entry.title}")
    
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        
        if unload_ok:
            coordinator = hass.data[DOMAIN]["coordinators"].pop(entry.entry_id)
            _LOGGER.debug(f"[{coordinator.device_name}] Coordinator unloaded successfully")
            
            # Remove services if this was the last entry
            if not hass.data[DOMAIN]["coordinators"]:
                _LOGGER.debug("Removing Adaptive Climate services - no more coordinators")
                hass.services.async_remove(DOMAIN, "clear_override")
                hass.services.async_remove(DOMAIN, "set_comfort_category")
                hass.services.async_remove(DOMAIN, "update_calculations")
                hass.services.async_remove(DOMAIN, "set_temporary_override")
                hass.services.async_remove(DOMAIN, "reset_override")
        
        _LOGGER.info(f"Adaptive Climate unload completed for entry: {entry.title}")
        return unload_ok
        
    except Exception as e:
        _LOGGER.error(f"Error unloading Adaptive Climate entry {entry.title}: {e}")
        return False


async def _async_setup_services(hass: HomeAssistant, coordinator: AdaptiveClimateCoordinator) -> None:
    """Set up services for the coordinator."""
    _LOGGER.debug(f"[{coordinator.device_name}] Setting up services")
    
    async def clear_override_service(call) -> None:
        """Clear manual override."""
        _LOGGER.debug(f"[{coordinator.device_name}] Clear override service called")
        await coordinator.clear_manual_override()
    
    async def set_comfort_category_service(call) -> None:
        """Set comfort category."""
        category = call.data.get("category")
        if category:
            _LOGGER.debug(f"[{coordinator.device_name}] Setting comfort category to: {category}")
            await coordinator.update_comfort_category(category)
        else:
            _LOGGER.error(f"[{coordinator.device_name}] No category provided for set_comfort_category service")
    
    async def update_calculations_service(call) -> None:
        """Force update calculations."""
        _LOGGER.debug(f"[{coordinator.device_name}] Update calculations service called")
        await coordinator.async_request_refresh()
    
    async def set_temporary_override_service(call) -> None:
        """Set temporary override."""
        temperature = call.data.get("temperature")
        duration = call.data.get("duration")
        
        if temperature is not None:
            _LOGGER.debug(f"[{coordinator.device_name}] Setting temporary override: {temperature}°C for {duration}s")
            await coordinator.set_manual_override(temperature, duration)
        else:
            _LOGGER.error(f"[{coordinator.device_name}] No temperature provided for set_temporary_override service")
    
    # Register services (only once for the domain)
    if not hass.services.has_service(DOMAIN, "clear_override"):
        hass.services.async_register(DOMAIN, "clear_override", clear_override_service)
        hass.services.async_register(DOMAIN, "set_comfort_category", set_comfort_category_service)
        hass.services.async_register(DOMAIN, "update_calculations", update_calculations_service)
        hass.services.async_register(DOMAIN, "set_temporary_override", set_temporary_override_service)
        _LOGGER.debug(f"[{coordinator.device_name}] Services registered successfully")
    else:
        _LOGGER.debug(f"[{coordinator.device_name}] Services already registered, skipping")