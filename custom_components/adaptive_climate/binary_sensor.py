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

from .const import DOMAIN, VERSION
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
            "identifiers": {(DOMAIN, config_entry.entry_id)},            "name": config_entry.data.get("name", "Adaptive Climate"),
            "manufacturer": "ASHRAE",
            "model": "Adaptive Climate Controller",
            "sw_version": VERSION,
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
        if self.coordinator.data and self.coordinator.data.get("ashrae_compliant") is not None:
            return self.coordinator.data.get("ashrae_compliant", False)
        return False  # Default to non-compliant when no data

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
        
        # Use effective comfort range for accurate diagnosis
        effective_min = self.coordinator.data.get("effective_comfort_min", self.coordinator.data.get("comfort_temp_min"))
        effective_max = self.coordinator.data.get("effective_comfort_max", self.coordinator.data.get("comfort_temp_max"))
        
        return {
            # Current conditions
            "indoor_temperature": self.coordinator.data.get("indoor_temperature"),
            
            # Comfort ranges (diagnostic values)
            "comfort_range_min": round(self.coordinator.data.get("comfort_temp_min", 0), 1),
            "comfort_range_max": round(self.coordinator.data.get("comfort_temp_max", 0), 1),
            "effective_comfort_min": round(effective_min, 1) if effective_min else None,
            "effective_comfort_max": round(effective_max, 1) if effective_max else None,
            
            # Configuration values (user-configurable)
            "comfort_category": self.coordinator.config.get("comfort_category", "II"),
            "min_comfort_temp_limit": self.coordinator.config.get("min_comfort_temp", 18.0),
            "max_comfort_temp_limit": self.coordinator.config.get("max_comfort_temp", 28.0),
            
            # Offset diagnostics  
            "air_velocity_offset": round(self.coordinator.data.get("air_velocity_offset", 0), 2),
            "humidity_offset": round(self.coordinator.data.get("humidity_offset", 0), 2),
            
            # Compliance calculation explanation - protect against None values
            "compliance_calculation": self._safe_compliance_calculation(effective_min, effective_max),
        }
    
    def _safe_compliance_calculation(self, effective_min, effective_max):
        """Generate compliance calculation string with safe handling of None values."""
        try:
            # Get indoor temp with more robust None handling
            indoor_temp = self.coordinator.data.get('indoor_temperature')
            # Convert to float first if not None, then format
            indoor_temp_str = f"{float(indoor_temp):.1f}" if indoor_temp is not None else "N/A"
            
            # Safe format min and max values with additional checks
            min_str = f"{float(effective_min):.1f}" if effective_min is not None else "N/A"
            max_str = f"{float(effective_max):.1f}" if effective_max is not None else "N/A"
            
            return f"{indoor_temp_str}°C in range [{min_str}°C - {max_str}°C]"
        except Exception as err:
            _LOGGER.debug("Error formatting compliance calculation: %s", err)
            return "Calculating compliance range..."


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
        if self.coordinator.data and self.coordinator.data.get("natural_ventilation_active") is not None:
            return self.coordinator.data.get("natural_ventilation_active", False)
        return False  # Default to not active when no data

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
        
        outdoor_temp = self.coordinator.data.get("outdoor_temperature", 0) or 0
        indoor_temp = self.coordinator.data.get("indoor_temperature", 0) or 0
        comfort_max = self.coordinator.data.get("comfort_temp_max", 28.0) or 28.0
        threshold = self.coordinator.config.get("natural_ventilation_threshold", 2.0)
        temp_diff = indoor_temp - outdoor_temp
        
        # Determine why natural ventilation is on/off
        conditions = {
            "indoor_above_comfort_max": indoor_temp > comfort_max,
            "outdoor_cooler_than_indoor": outdoor_temp < indoor_temp,  
            "temp_difference_sufficient": temp_diff >= threshold,
        }
        
        all_conditions_met = all(conditions.values())
        
        return {
            "outdoor_temperature": round(outdoor_temp, 2),
            "indoor_temperature": round(indoor_temp, 2),
            "temperature_difference": round(temp_diff, 2),
            "natural_ventilation_threshold": threshold,
            "comfort_temp_max": round(comfort_max, 1),
            "conditions_met": conditions,
            "all_conditions_met": all_conditions_met,
            "diagnostic_summary": f"Indoor {float(indoor_temp):.1f}°C {'>' if conditions['indoor_above_comfort_max'] else '≤'} {float(comfort_max):.1f}°C, Outdoor {float(outdoor_temp):.1f}°C {'<' if conditions['outdoor_cooler_than_indoor'] else '≥'} Indoor, Diff {float(temp_diff):.1f}°C {'≥' if conditions['temp_difference_sufficient'] else '<'} {float(threshold)}°C",
        }
