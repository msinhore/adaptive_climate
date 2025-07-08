"""Real Number Entities for Adaptive Climate - Simplified Version.

This module contains NumberEntity implementations for active numeric
configuration parameters, following Home Assistant and HACS best practices.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity
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
    """Set up Adaptive Climate number entities."""
    coordinator: AdaptiveClimateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        AdaptiveClimateNumberEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="min_comfort_temp",
            name="Minimum Comfort Temperature",
            icon="mdi:thermometer-chevron-down",
            native_min_value=10.0,
            native_max_value=30.0,
            native_step=0.5,
            native_unit_of_measurement="°C",
            device_class="temperature",
        ),
        AdaptiveClimateNumberEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="max_comfort_temp",
            name="Maximum Comfort Temperature",
            icon="mdi:thermometer-chevron-up",
            native_min_value=15.0,
            native_max_value=35.0,
            native_step=0.5,
            native_unit_of_measurement="°C",
            device_class="temperature",
        ),
        AdaptiveClimateNumberEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="air_velocity",
            name="Air Velocity",
            icon="mdi:weather-windy",
            native_min_value=0.0,
            native_max_value=2.0,
            native_step=0.1,
            native_unit_of_measurement="m/s",
        ),
        AdaptiveClimateNumberEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="temperature_change_threshold",
            name="Temperature Change Threshold",
            icon="mdi:thermometer-alert",
            native_min_value=0.1,
            native_max_value=5.0,
            native_step=0.1,
            native_unit_of_measurement="°C",
            device_class="temperature",
        ),
        AdaptiveClimateNumberEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="setback_temperature_offset",
            name="Setback Temperature Offset",
            icon="mdi:thermometer-minus",
            native_min_value=0.5,
            native_max_value=10.0,
            native_step=0.5,
            native_unit_of_measurement="°C",
            device_class="temperature",
        ),
        AdaptiveClimateNumberEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="auto_shutdown_minutes",
            name="Auto Shutdown Minutes",
            icon="mdi:timer-off",
            native_min_value=1,
            native_max_value=240,
            native_step=1,
            native_unit_of_measurement="min", 
        ),
        AdaptiveClimateNumberEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="auto_start_minutes",
            name="Auto Start Minutes",
            icon="mdi:timer-on",
            native_min_value=1,
            native_max_value=30,
            native_step=1,
            native_unit_of_measurement="min", 
        ),
        AdaptiveClimateNumberEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="user_override_minutes",
            name="User Override Minutes",
            icon="mdi:timer-cog",
            native_min_value=10,
            native_max_value=240,
            native_step=10,
            native_unit_of_measurement="min", 
        ),
    ]
    
    async_add_entities(entities)
    _LOGGER.info("Added %d number entities for Adaptive Climate", len(entities))


class AdaptiveClimateNumberEntity(CoordinatorEntity, NumberEntity):
    """Number entity for Adaptive Climate configuration parameters."""

    def __init__(
        self,
        coordinator: AdaptiveClimateCoordinator,
        config_entry: ConfigEntry,
        entity_key: str,
        name: str,
        icon: str,
        native_min_value: float,
        native_max_value: float,
        native_step: float,
        native_unit_of_measurement: str,
        device_class: str | None = None,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._entity_key = entity_key
        area = coordinator.config.get("name", "Adaptive Climate")
        self._attr_name = f"{name} ({area})"
        self._attr_icon = icon
        self._attr_native_min_value = native_min_value
        self._attr_native_max_value = native_max_value
        self._attr_native_step = native_step
        self._attr_native_unit_of_measurement = native_unit_of_measurement
        self._attr_device_class = device_class
        self._attr_mode = "box" 
        self._attr_unique_id = f"{config_entry.entry_id}_{entity_key}"
        _LOGGER.debug(
            "Initialized number entity: %s (key: %s, unique_id: %s)",
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
    def native_value(self) -> float | None:
        """Return the current value."""
        value = None
        
        if self.coordinator.data:
            value = self.coordinator.data.get(self._entity_key)
        
        if value is None:
            value = self._config_entry.data.get(self._entity_key)

        if value is None:
            value = self._attr_native_min_value

        _LOGGER.debug(
            "Number entity %s native_value: %s",
            self._entity_key, value
        )
        
        return value

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        _LOGGER.info(
            "Setting %s from %s to %s",
            self._entity_key, self.native_value, value
        )
        
        await self.coordinator.async_update_config_value(self._entity_key, value)
        self.async_write_ha_state()
        
        _LOGGER.debug("Successfully updated %s to %s", self._entity_key, value)

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
        