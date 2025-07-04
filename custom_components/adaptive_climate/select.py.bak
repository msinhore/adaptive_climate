"""Select platform for Adaptive Climate integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION, COMFORT_CATEGORIES, DEFAULT_COMFORT_CATEGORY
from .coordinator import AdaptiveClimateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        AdaptiveClimateComfortCategorySelect(coordinator, config_entry),
    ]
    
    async_add_entities(entities)


class AdaptiveClimateComfortCategorySelect(CoordinatorEntity, SelectEntity):
    """Select entity for comfort category selection."""
    
    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry):
        """Initialize the select."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_comfort_category"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Comfort Category"
        self._attr_icon = "mdi:account-group"
        # Remove entity_category to make select appear in Controls tab
        # self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = ["I", "II", "III"]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": config_entry.data.get("name", "Adaptive Climate"),
            "manufacturer": "ASHRAE",
            "model": "Adaptive Climate Controller",
            "sw_version": VERSION,
        }
        
    @property
    def current_option(self) -> str | None:
        """Return current option."""
        # Check options first, then data, then default
        return (
            self.config_entry.options.get("comfort_category") or 
            self.config_entry.data.get("comfort_category", DEFAULT_COMFORT_CATEGORY)
        )
    
    async def async_select_option(self, option: str) -> None:
        """Select new option."""
        new_options = dict(self.config_entry.options)
        new_options["comfort_category"] = option
        self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)
        
        _LOGGER.info("Comfort category changed to: %s", option)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
