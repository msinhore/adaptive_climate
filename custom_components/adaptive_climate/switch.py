"""Real Switch Entities for Adaptive Climate - Stage 3 Refactoring.

This module contains real SwitchEntity implementations that replace
the bridge architecture, following Home Assistant and HACS best practices.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up Adaptive Climate switch entities."""
    coordinator: AdaptiveClimateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        AdaptiveClimateSwitchEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="energy_save_mode",
            name="Energy Save Mode",
            icon="mdi:leaf",
        ),
        AdaptiveClimateSwitchEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="natural_ventilation_enable",
            name="Natural Ventilation",
            icon="mdi:window-open",
        ),
        AdaptiveClimateSwitchEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="adaptive_air_velocity",
            name="Adaptive Air Velocity",
            icon="mdi:weather-windy",
        ),
        AdaptiveClimateSwitchEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="humidity_comfort_enable",
            name="Humidity Comfort Correction",
            icon="mdi:water-percent",
        ),
        AdaptiveClimateSwitchEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="comfort_precision_mode",
            name="Comfort Precision Mode",
            icon="mdi:target",
        ),
        AdaptiveClimateSwitchEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="use_operative_temperature",
            name="Use Operative Temperature",
            icon="mdi:thermometer-plus",
        ),
    ]
    
    async_add_entities(entities)
    _LOGGER.info("Added %d switch entities for Adaptive Climate", len(entities))


class AdaptiveClimateSwitchEntity(CoordinatorEntity, SwitchEntity):
    """Switch entity for Adaptive Climate configuration parameters."""

    def __init__(
        self,
        coordinator: AdaptiveClimateCoordinator,
        config_entry: ConfigEntry,
        entity_key: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._entity_key = entity_key
        self._attr_name = name
        self._attr_icon = icon
        
        # Generate stable unique ID
        self._attr_unique_id = f"{config_entry.entry_id}_{entity_key}"
        
        _LOGGER.debug(
            "Initialized switch entity: %s (key: %s, unique_id: %s)",
            name, entity_key, self._attr_unique_id
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
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if not self.coordinator.data:
            return None
            
        value = self.coordinator.data.get(self._entity_key)
        if value is None:
            # Get default value from coordinator config
            value = self.coordinator.get_config_value(self._entity_key)
            
        _LOGGER.debug(
            "Switch entity %s is_on: %s (from %s)",
            self._entity_key, value, "coordinator_data" if self.coordinator.data.get(self._entity_key) else "config_default"
        )
        
        return bool(value) if value is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        _LOGGER.info("Turning on %s", self._entity_key)
        
        # Update coordinator configuration
        await self.coordinator.async_update_config_value(self._entity_key, True)
        
        # Update the state immediately
        self.async_write_ha_state()
        
        _LOGGER.debug("Successfully turned on %s", self._entity_key)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        _LOGGER.info("Turning off %s", self._entity_key)
        
        # Update coordinator configuration
        await self.coordinator.async_update_config_value(self._entity_key, False)
        
        # Update the state immediately
        self.async_write_ha_state()
        
        _LOGGER.debug("Successfully turned off %s", self._entity_key)

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
