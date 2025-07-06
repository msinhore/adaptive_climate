"""Real Select Entities for Adaptive Climate - Stage 3 Refactoring.

This module contains real SelectEntity implementations that replace
the bridge architecture, following Home Assistant and HACS best practices.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION
from .coordinator import AdaptiveClimateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Adaptive Climate select entities."""
    coordinator: AdaptiveClimateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        AdaptiveClimateSelectEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="comfort_category",
            name="Comfort Category",
            icon="mdi:account-group",
            options=["I", "II", "III"],
        ),
    ]
    
    async_add_entities(entities)
    _LOGGER.info("Added %d select entities for Adaptive Climate", len(entities))


class AdaptiveClimateSelectEntity(CoordinatorEntity, SelectEntity):
    """Select entity for Adaptive Climate configuration parameters."""

    def __init__(
        self,
        coordinator: AdaptiveClimateCoordinator,
        config_entry: ConfigEntry,
        entity_key: str,
        name: str,
        icon: str,
        options: list[str],
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._entity_key = entity_key
        area = coordinator.config.get("name", "Adaptive Climate")
        self._attr_name = f"{name} ({area})"
        self._attr_icon = icon
        self._attr_options = options
        
        # Generate stable unique ID
        self._attr_unique_id = f"{config_entry.entry_id}_{entity_key}"
        
        _LOGGER.debug(
            "Initialized select entity: %s (key: %s, unique_id: %s)",
            self._attr_name, entity_key, self._attr_unique_id
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name="Adaptive Climate",
            manufacturer="Adaptive Climate",
            model="ASHRAE 55 Adaptive Comfort",
            sw_version=VERSION,
            configuration_url="https://github.com/msinhore/adaptive-climate",
        )

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        value = None

        if self.coordinator.data:
            value = self.coordinator.data.get(self._entity_key)

        if value is None:
            value = self.coordinator.config.get(self._entity_key, "II")
        
        _LOGGER.debug(
            "Select entity %s current_option: %s (source: %s)",
            self._entity_key,
            value,
            "coordinator_data" if self.coordinator.data and self.coordinator.data.get(self._entity_key) else "config_default",
        )
        
        return value

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        if option not in self._attr_options:
            _LOGGER.error("Invalid option %s for %s. Valid options: %s", option, self._entity_key, self._attr_options)
            return
            
        _LOGGER.info(
            "Setting %s from %s to %s",
            self._entity_key, self.current_option, option
        )
        
        # Update coordinator configuration
        await self.coordinator.async_update_config_value(self._entity_key, option)
        
        # Update the state immediately
        self.async_write_ha_state()
        
        _LOGGER.debug("Successfully updated %s to %s", self._entity_key, option)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return True
