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

from .const import DOMAIN, VERSION
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
        OutdoorRunningMeanSensor(coordinator, config_entry),
        # Diagnostic sensors for Controls/Sensors tabs
        AdaptiveClimateConfigSensor(coordinator, config_entry, "climate_entity", "Climate Entity"),
        AdaptiveClimateConfigSensor(coordinator, config_entry, "indoor_temp_sensor", "Indoor Temperature Sensor"),
        AdaptiveClimateConfigSensor(coordinator, config_entry, "outdoor_temp_sensor", "Outdoor Temperature Sensor"),
        AdaptiveClimateConfigSensor(coordinator, config_entry, "occupancy_sensor", "Occupancy Sensor"),
        AdaptiveClimateConfigSensor(coordinator, config_entry, "mean_radiant_temp_sensor", "Mean Radiant Temperature Sensor"),
        AdaptiveClimateConfigSensor(coordinator, config_entry, "indoor_humidity_sensor", "Indoor Humidity Sensor"),
        AdaptiveClimateConfigSensor(coordinator, config_entry, "outdoor_humidity_sensor", "Outdoor Humidity Sensor"),
    ]
    
    async_add_entities(entities)


class AdaptiveClimateSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Adaptive Climate sensors."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._config_name = config_entry.data.get("name", "Adaptive Climate")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": self._config_name,
            "manufacturer": "ASHRAE",
            "model": "Adaptive Climate Controller",
            "sw_version": VERSION,
        }
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


class AdaptiveComfortTemperatureSensor(AdaptiveClimateSensorBase):
    """Sensor for adaptive comfort temperature."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_comfort_temperature"
        self._attr_name = f"ASHRAE 55 {self._config_name} Comfort Temperature"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data and self.coordinator.data.get("adaptive_comfort_temp") is not None:
            return self.coordinator.data.get("adaptive_comfort_temp")
        return 22.0  # Default fallback value

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success and
            self.coordinator.data is not None and
            self.coordinator.data.get("status") != "entities_unavailable"
        )

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


class OutdoorRunningMeanSensor(AdaptiveClimateSensorBase):
    """Sensor for outdoor running mean temperature."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_outdoor_running_mean"
        self._attr_name = f"{self._config_name} Outdoor Running Mean"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_icon = "mdi:chart-timeline-variant"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data and self.coordinator.data.get("outdoor_running_mean") is not None:
            return self.coordinator.data.get("outdoor_running_mean")
        return None  # This one can be None as it needs data to be meaningful

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success and
            self.coordinator.data is not None and
            self.coordinator.data.get("status") != "entities_unavailable" and
            self.coordinator.data.get("outdoor_running_mean") is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        
        return {
            "calculation_period": "7 days",
            "current_outdoor_temp": self.coordinator.data.get("outdoor_temperature"),
        }


class AdaptiveClimateConfigSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity for configuration information (appears in Sensors tab)."""
    
    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry, 
                 config_key: str, name: str):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._config_key = config_key
        self._attr_unique_id = f"{config_entry.entry_id}_config_{config_key}"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} {name}"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:information-outline"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": config_entry.data.get("name", "Adaptive Climate"),
            "manufacturer": "ASHRAE",
            "model": "Adaptive Climate Controller",
            "sw_version": VERSION,
        }
        
    @property
    def native_value(self) -> str | None:
        """Return config value."""
        value = self.config_entry.data.get(self._config_key)
        if value:
            # Return friendly name if it's an entity
            if "." in str(value):
                state = self.hass.states.get(value)
                if state:
                    return state.attributes.get("friendly_name", value)
            return str(value)
        return "Not configured"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        value = self.config_entry.data.get(self._config_key)
        attributes = {}
        
        if value and "." in str(value):
            # Add entity information for configured entities
            state = self.hass.states.get(value)
            if state:
                attributes["entity_id"] = value
                attributes["domain"] = value.split(".")[0]
                attributes["device_class"] = state.attributes.get("device_class")
                attributes["unit_of_measurement"] = state.attributes.get("unit_of_measurement")
                attributes["current_state"] = state.state
                
        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
