"""Button platform for Adaptive Climate integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
    """Set up button entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        AdaptiveClimateActionButton(coordinator, config_entry, "reset_outdoor_history", "Reset Outdoor History", "mdi:chart-line"),
        AdaptiveClimateActionButton(coordinator, config_entry, "reconfigure_entities", "Reconfigure Entities", "mdi:cog-refresh"),
        AdaptiveClimateActionButton(coordinator, config_entry, "reload_integration", "Reload Integration", "mdi:reload"),
    ]
    
    async_add_entities(entities)


class AdaptiveClimateActionButton(CoordinatorEntity, ButtonEntity):
    """Button entity for actions."""
    
    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry, 
                 action: str, name: str, icon: str):
        """Initialize the button."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._action = action
        self._attr_unique_id = f"{config_entry.entry_id}_action_{action}"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} {name}"
        self._attr_icon = icon
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": config_entry.data.get("name", "Adaptive Climate"),
            "manufacturer": "ASHRAE",
            "model": "Adaptive Climate Controller",
            "sw_version": VERSION,
        }
        
    async def async_press(self) -> None:
        """Handle button press."""
        if self._action == "reset_outdoor_history":
            await self._reset_outdoor_history()
        elif self._action == "reconfigure_entities":
            await self._reconfigure_entities()
        elif self._action == "reload_integration":
            await self._reload_integration()
    
    async def _reset_outdoor_history(self) -> None:
        """Reset outdoor temperature history."""
        try:
            if hasattr(self.coordinator, 'reset_outdoor_history'):
                await self.coordinator.reset_outdoor_history()
                _LOGGER.info("Outdoor temperature history reset successfully")
            else:
                _LOGGER.warning("Reset outdoor history method not available")
        except Exception as e:
            _LOGGER.error("Failed to reset outdoor history: %s", e)
    
    async def _reconfigure_entities(self) -> None:
        """Trigger entity reconfiguration flow."""
        try:
            # Best practice: Remove entry and trigger reconfiguration
            # This is the recommended approach since HA doesn't officially 
            # support entity reconfiguration in OptionsFlow
            entry_id = self.config_entry.entry_id
            title = self.config_entry.title
            
            # Store current data for recovery if needed
            backup_data = {
                "data": dict(self.config_entry.data),
                "options": dict(self.config_entry.options),
                "title": title
            }
            
            # Store backup temporarily
            if "adaptive_climate_backup" not in self.hass.data:
                self.hass.data["adaptive_climate_backup"] = {}
            self.hass.data["adaptive_climate_backup"][entry_id] = backup_data
            
            # Remove current entry
            await self.hass.config_entries.async_remove(entry_id)
            
            # Trigger new config flow with context
            self.hass.async_create_task(
                self.hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": "reconfigure"},
                    data={"previous_entry_id": entry_id, "backup_data": backup_data}
                )
            )
            
            _LOGGER.info("Entity reconfiguration flow triggered")
            
        except Exception as e:
            _LOGGER.error("Failed to trigger reconfiguration: %s", e)
    
    async def _reload_integration(self) -> None:
        """Reload the integration."""
        try:
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            _LOGGER.info("Integration reloaded successfully")
        except Exception as e:
            _LOGGER.error("Failed to reload integration: %s", e)
