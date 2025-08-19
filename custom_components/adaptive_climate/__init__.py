"""The Adaptive Climate component."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from custom_components.adaptive_climate.const import DOMAIN
from custom_components.adaptive_climate.coordinator import AdaptiveClimateCoordinator

_LOGGER = logging.getLogger(__name__)

# Configuration schema for YAML setup
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required("entity"): cv.entity_id,
                    }
                )
            ],
        )
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
        _LOGGER.debug(
            f"[{coordinator.device_name}] Resetting override via service call"
        )
        await coordinator.async_reset_override()
    else:
        _LOGGER.error(f"Could not find coordinator for entity {entity_id}")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Adaptive Climate from YAML configuration."""
    _LOGGER.debug("Setting up Adaptive Climate from YAML configuration")

    # Initialize data structure to avoid overwriting configs
    hass.data.setdefault(DOMAIN, {"configs": {}, "coordinators": {}})

    entries = config.get(DOMAIN, [])
    _LOGGER.debug(
        f"Adaptive Climate YAML entries loaded: {len(entries)} entries"
    )

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
            _LOGGER.error(
                f"Skipping entry '{entity_id}' - Missing required 'entity' definition in YAML configuration."
            )
            continue

        try:
            coordinator = AdaptiveClimateCoordinator(hass, config_entry)
            hass.data[DOMAIN]["coordinators"][entity_id] = coordinator

            _LOGGER.debug(
                f"Created coordinator for entity: {entity_id}"
            )

            # Set up services for this coordinator
            await _async_setup_services(hass, coordinator)

            # Perform initial data fetch
            await coordinator.async_config_entry_first_refresh()

        except Exception as e:
            _LOGGER.error(
                f"Failed to create coordinator for entity {entity_id}: {e}"
            )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Adaptive Climate from a config entry."""
    _LOGGER.debug(
        f"Setting up Adaptive Climate from config entry: {entry.title}"
    )

    # Initialize data structure if not exists
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"configs": {}, "coordinators": {}}

    try:
        # Create coordinator for this entry
        coordinator = AdaptiveClimateCoordinator(hass, entry.data, entry.options)
        hass.data[DOMAIN]["coordinators"][entry.entry_id] = coordinator

        _LOGGER.debug(
            f"Created coordinator for config entry: {entry.title}"
        )

        # Set up services for this coordinator
        await _async_setup_services(hass, coordinator)

        # Perform initial data fetch
        await coordinator.async_config_entry_first_refresh()

        # Set up platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        _LOGGER.info(
            f"Adaptive Climate setup completed for entry: {entry.title}"
        )
        return True

    except Exception as e:
        _LOGGER.error(
            f"Failed to set up Adaptive Climate for entry {entry.title}: {e}"
        )
        return False


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.debug(
        f"Reloading Adaptive Climate coordinator for entry: {entry.title}"
    )

    try:
        # Unload platforms first
        await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

        # Get the coordinator
        coordinator = hass.data[DOMAIN]["coordinators"].get(entry.entry_id)
        if not coordinator:
            _LOGGER.error(f"Could not find coordinator for entry {entry.entry_id}")
            return

        # Update coordinator configuration
        await coordinator.update_config({**entry.data, **entry.options})

        # Request refresh to apply new configuration
        await coordinator.async_request_refresh()

        _LOGGER.debug(
            f"[{coordinator.device_name}] Configuration update completed successfully"
        )

    except KeyError:
        _LOGGER.error(f"Could not find coordinator for entry {entry.entry_id}")
    except Exception as err:
        _LOGGER.error(f"Error updating coordinator configuration: {err}")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(
        f"Unloading Adaptive Climate coordinator for entry: {entry.title}"
    )

    try:
        unload_ok = await hass.config_entries.async_unload_platforms(
            entry, PLATFORMS
        )

        if unload_ok:
            coordinator = hass.data[DOMAIN]["coordinators"].pop(entry.entry_id)
            _LOGGER.debug(
                f"[{coordinator.device_name}] Coordinator unloaded successfully"
            )

            # Remove services if this was the last entry
            if not hass.data[DOMAIN]["coordinators"]:
                _LOGGER.debug(
                    "Removing Adaptive Climate services - no more coordinators"
                )
                hass.services.async_remove(DOMAIN, "clear_override")
                hass.services.async_remove(DOMAIN, "set_comfort_category")
                hass.services.async_remove(DOMAIN, "update_calculations")
                hass.services.async_remove(DOMAIN, "set_temporary_override")
                hass.services.async_remove(DOMAIN, "reset_override")

        _LOGGER.info(
            f"Adaptive Climate unload completed for entry: {entry.title}"
        )
        return unload_ok

    except Exception as e:
        _LOGGER.error(
            f"Error unloading Adaptive Climate entry {entry.title}: {e}"
        )
        return False


async def _async_setup_services(
    hass: HomeAssistant, coordinator: AdaptiveClimateCoordinator
) -> None:
    """Set up services for the coordinator."""
    _LOGGER.debug(f"[{coordinator.device_name}] Setting up services")

    async def set_comfort_category_service(call) -> None:
        """Set comfort category."""
        category = call.data.get("category")
        if category:
            _LOGGER.debug(
                f"[{coordinator.device_name}] Setting comfort category to: {category}"
            )
            await coordinator.update_comfort_category(category)
        else:
            _LOGGER.error(
                f"[{coordinator.device_name}] No category provided for set_comfort_category service"
            )

    async def update_calculations_service(call) -> None:
        """Force update calculations."""
        _LOGGER.debug(
            f"[{coordinator.device_name}] Update calculations service called"
        )
        await coordinator.async_request_refresh()

    # Register services (only once for the domain)
    if not hass.services.has_service(DOMAIN, "set_comfort_category"):
        hass.services.async_register(
            DOMAIN, "set_comfort_category", set_comfort_category_service
        )
        hass.services.async_register(
            DOMAIN, "update_calculations", update_calculations_service
        )
        _LOGGER.debug(
            f"[{coordinator.device_name}] Services registered successfully"
        )
    else:
        _LOGGER.debug(
            f"[{coordinator.device_name}] Services already registered, skipping"
        )
