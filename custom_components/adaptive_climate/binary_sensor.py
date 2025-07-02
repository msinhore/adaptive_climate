"""Binary sensor platform for Adaptive Climate."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
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
    """Set up Adaptive Climate binary sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        ASHRAEComplianceSensor(coordinator, config_entry),
        NaturalVentilationSensor(coordinator, config_entry),
    ]
    
    async_add_entities(entities)


class AdaptiveClimateBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base class for Adaptive Climate binary sensors."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": config_entry.data.get("name", "Adaptive Climate"),
            "manufacturer": "ASHRAE",
            "model": "Adaptive Climate Controller", 
            "sw_version": "0.1.3",
        }
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


class ASHRAEComplianceSensor(AdaptiveClimateBinarySensorBase):
    """Binary sensor for ASHRAE 55 compliance."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_ashrae_compliance"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} ASHRAE Compliance"
        self._attr_icon = "mdi:check-circle-outline"

    @property
    def is_on(self) -> bool | None:
        """Return true if ASHRAE compliant."""
        if self.coordinator.data:
            return self.coordinator.data.get("ashrae_compliant", False)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        
        return {
            "indoor_temperature": self.coordinator.data.get("indoor_temperature"),
            "comfort_range_min": self.coordinator.data.get("comfort_temp_min"),
            "comfort_range_max": self.coordinator.data.get("comfort_temp_max"),
            "comfort_category": self.coordinator.config.get("comfort_category"),
            "compliance_notes": self.coordinator.data.get("compliance_notes", ""),
        }


class NaturalVentilationSensor(AdaptiveClimateBinarySensorBase):
    """Binary sensor for natural ventilation opportunity."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_natural_ventilation_optimal"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Natural Ventilation Optimal"
        self._attr_icon = "mdi:window-open"

    @property
    def is_on(self) -> bool | None:
        """Return true if natural ventilation is optimal."""
        if self.coordinator.data:
            return self.coordinator.data.get("natural_ventilation_active", False)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes.""" 
        if not self.coordinator.data:
            return {}
        
        return {
            "outdoor_temperature": self.coordinator.data.get("outdoor_temperature"),
            "indoor_temperature": self.coordinator.data.get("indoor_temperature"),
            "temperature_difference": abs(
                (self.coordinator.data.get("outdoor_temperature", 0) or 0) - 
                (self.coordinator.data.get("indoor_temperature", 0) or 0)
            ),
            "natural_ventilation_threshold": self.coordinator.config.get("natural_ventilation_threshold", 2.0),
        }
