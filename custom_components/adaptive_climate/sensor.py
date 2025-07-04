"""Real Sensor Entities for Adaptive Climate - Stage 3 Refactoring.

This module contains real SensorEntity implementations for diagnostic and informational
data, following Home Assistant and HACS best practices.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
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
    """Set up Adaptive Climate sensor entities."""
    coordinator: AdaptiveClimateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        AdaptiveClimateSensorEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="comfort_temperature",
            name="Comfort Temperature",
            icon="mdi:thermometer",
            native_unit_of_measurement="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        AdaptiveClimateSensorEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="comfort_range_min",
            name="Comfort Range Minimum",
            icon="mdi:thermometer-chevron-down",
            native_unit_of_measurement="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        AdaptiveClimateSensorEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="comfort_range_max",
            name="Comfort Range Maximum",
            icon="mdi:thermometer-chevron-up",
            native_unit_of_measurement="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        AdaptiveClimateSensorEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="running_mean_outdoor_temp",
            name="Running Mean Outdoor Temperature",
            icon="mdi:chart-line",
            native_unit_of_measurement="°C",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        AdaptiveClimateSensorEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            entity_key="ashrae_comfort_category",
            name="ASHRAE Comfort Category",
            icon="mdi:account-group",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
    ]
    
    async_add_entities(entities)
    _LOGGER.info("Added %d sensor entities for Adaptive Climate", len(entities))


class AdaptiveClimateSensorEntity(CoordinatorEntity, SensorEntity):
    """Sensor entity for Adaptive Climate diagnostic information."""

    def __init__(
        self,
        coordinator: AdaptiveClimateCoordinator,
        config_entry: ConfigEntry,
        entity_key: str,
        name: str,
        icon: str,
        native_unit_of_measurement: str | None = None,
        device_class: SensorDeviceClass | None = None,
        state_class: SensorStateClass | None = None,
        entity_category: EntityCategory | None = None,
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._entity_key = entity_key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = native_unit_of_measurement
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_entity_category = entity_category
        
        # Generate stable unique ID
        self._attr_unique_id = f"{config_entry.entry_id}_{entity_key}"
        
        _LOGGER.debug(
            "Initialized sensor entity: %s (key: %s, unique_id: %s)",
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
    def native_value(self) -> Any:
        """Return the current value."""
        if not self.coordinator.data:
            return None
            
        value = self.coordinator.data.get(self._entity_key)
        
        _LOGGER.debug(
            "Sensor entity %s native_value: %s",
            self._entity_key, value
        )
        
        return value

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
