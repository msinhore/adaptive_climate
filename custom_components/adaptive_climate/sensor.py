"""Sensor platform for Adaptive Climate."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .coordinator import AdaptiveClimateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Adaptive Climate sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        AdaptiveComfortTemperatureSensor(coordinator, config_entry),
        ComfortRangeMinSensor(coordinator, config_entry),
        ComfortRangeMaxSensor(coordinator, config_entry),
        OutdoorRunningMeanSensor(coordinator, config_entry),
    ]
    
    async_add_entities(entities)


class AdaptiveClimateSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Adaptive Climate sensors."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": config_entry.data.get("name", "Adaptive Climate"),
            "manufacturer": "ASHRAE",
            "model": "Adaptive Climate Controller",
            "sw_version": "0.1.1",
        }
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


class AdaptiveComfortTemperatureSensor(AdaptiveClimateSensorBase):
    """Sensor for adaptive comfort temperature."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_comfort_temperature"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Comfort Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("adaptive_comfort_temp")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        
        return {
            "outdoor_temperature": self.coordinator.data.get("outdoor_temperature"),
            "comfort_category": self.coordinator.config.get("comfort_category"),
            "calculation_method": "ASHRAE 55-2020",
            "formula": "18.9 + 0.255 × Outdoor Temperature",
        }


class ComfortRangeMinSensor(AdaptiveClimateSensorBase):
    """Sensor for comfort zone minimum temperature."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_comfort_range_min"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Comfort Range Min"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:thermometer-low"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("comfort_temp_min")
        return None


class ComfortRangeMaxSensor(AdaptiveClimateSensorBase):
    """Sensor for comfort zone maximum temperature."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_comfort_range_max"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Comfort Range Max"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:thermometer-high"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("comfort_temp_max")
        return None


class OutdoorRunningMeanSensor(AdaptiveClimateSensorBase):
    """Sensor for outdoor running mean temperature."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_outdoor_running_mean"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Outdoor Running Mean"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:chart-timeline-variant"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("outdoor_running_mean")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        
        return {
            "calculation_period": "7 days",
            "current_outdoor_temp": self.coordinator.data.get("outdoor_temperature"),
        }
