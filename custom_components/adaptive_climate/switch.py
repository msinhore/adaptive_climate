"""Real Switch Entities for Adaptive Climate - Simplified Version.

This module contains SwitchEntity implementations for essential
configuration parameters only, following Home Assistant and HACS best practices.
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
            entity_key="auto_shutdown_enable",
            name="Auto Shutdown Enable",
            icon="mdi:power-off",
        ),
        AdaptiveClimateSwitchEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="auto_start_enable",
            name="Auto Resume on Presence Enable",
            icon="mdi:power-on",
        ),
        AdaptiveClimateSwitchEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="user_override_enable",
            name="User Override Settings Enable",
            icon="mdi:autorenew",
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
        icon_off: str | None = None,
        default_value: bool = True,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._entity_key = entity_key
        area = coordinator.config.get("name", "Adaptive Climate")
        self._attr_name = f"{name} ({area})"
        self._attr_icon = icon
        self._icon_off = icon_off
        self._default_value = default_value
        self._attr_unique_id = f"{config_entry.entry_id}_{entity_key}"
        _LOGGER.debug(
            "Initialized switch entity: %s (key: %s, unique_id: %s)",
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
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.config.get(self._entity_key, self._default_value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        _LOGGER.info("Turning on %s", self._entity_key)
        try:
            await self.coordinator.async_update_config_value(self._entity_key, True)
            self.async_write_ha_state()
            _LOGGER.debug("Successfully turned on %s", self._entity_key)
        except Exception as e:
            _LOGGER.error("Failed to turn on %s: %s", self._entity_key, e)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        _LOGGER.info("Turning off %s", self._entity_key)
        try:
            await self.coordinator.async_update_config_value(self._entity_key, False)
            self.async_write_ha_state()
            _LOGGER.debug("Successfully turned off %s", self._entity_key)
        except Exception as e:
            _LOGGER.error("Failed to turn off %s: %s", self._entity_key, e)

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