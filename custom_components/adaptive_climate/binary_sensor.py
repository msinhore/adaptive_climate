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

from .const import (
    DOMAIN, 
    VERSION,
    DEFAULT_MIN_COMFORT_TEMP,
    DEFAULT_MAX_COMFORT_TEMP,
    DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
    DEFAULT_AIR_VELOCITY,
    DEFAULT_NATURAL_VENTILATION_THRESHOLD,
    DEFAULT_SETBACK_TEMPERATURE_OFFSET,
    DEFAULT_PROLONGED_ABSENCE_MINUTES,
    DEFAULT_AUTO_SHUTDOWN_MINUTES,
    DEFAULT_COMFORT_TEMP_MIN_OFFSET,
    DEFAULT_COMFORT_TEMP_MAX_OFFSET,
    DEFAULT_COMFORT_CATEGORY,
)
from .coordinator import AdaptiveClimateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Adaptive Climate binary sensor."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Only one entity per device - ASHRAE Compliance with all data as attributes
    entities = [
        ASHRAEComplianceSensor(coordinator, config_entry),
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
            "sw_version": VERSION,
        }


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
        """Return the state attributes organized in user-friendly sections."""
        if not self.coordinator.data:
            return {}
        
        # Calculate effective comfort range (only show if different from base range)
        base_min = self.coordinator.data.get("comfort_temp_min", 0)
        base_max = self.coordinator.data.get("comfort_temp_max", 0)
        effective_min = self.coordinator.data.get("effective_comfort_min", base_min)
        effective_max = self.coordinator.data.get("effective_comfort_max", base_max)
        
        # Get configuration
        config = self.coordinator.config
        
        attributes = {}
        
        # === CONTROLS & STATUS ===
        attributes.update({
            "compliance_status": self._safe_compliance_calculation(effective_min, effective_max),
            "occupancy": self.coordinator.data.get("occupancy", "unknown"),
            "manual_override": self.coordinator.data.get("manual_override", False),
            "natural_ventilation_optimal": self.coordinator.data.get("natural_ventilation_active", False),
        })
        
        # === CONFIGURATION (Editable via Services) ===
        attributes.update({
            # Temperature Limits
            "min_comfort_temp": config.get("min_comfort_temp", DEFAULT_MIN_COMFORT_TEMP),
            "max_comfort_temp": config.get("max_comfort_temp", DEFAULT_MAX_COMFORT_TEMP),
            "temperature_change_threshold": config.get("temperature_change_threshold", DEFAULT_TEMPERATURE_CHANGE_THRESHOLD),
            
            # Comfort Settings
            "comfort_category": config.get("comfort_category", DEFAULT_COMFORT_CATEGORY),
            "comfort_precision_mode": config.get("comfort_precision_mode", False),
            "use_operative_temperature": config.get("use_operative_temperature", False),
            
            # Air & Ventilation
            "air_velocity": config.get("air_velocity", DEFAULT_AIR_VELOCITY),
            "adaptive_air_velocity": config.get("adaptive_air_velocity", False),
            "natural_ventilation_enable": config.get("natural_ventilation_enable", True),
            "natural_ventilation_threshold": config.get("natural_ventilation_threshold", DEFAULT_NATURAL_VENTILATION_THRESHOLD),
            
            # Occupancy & Energy
            "use_occupancy_features": config.get("use_occupancy_features", True),
            "energy_save_mode": config.get("energy_save_mode", True),
            "setback_temperature_offset": config.get("setback_temperature_offset", DEFAULT_SETBACK_TEMPERATURE_OFFSET),
            "prolonged_absence_minutes": config.get("prolonged_absence_minutes", DEFAULT_PROLONGED_ABSENCE_MINUTES),
            "auto_shutdown_enable": config.get("auto_shutdown_enable", False),
            "auto_shutdown_minutes": config.get("auto_shutdown_minutes", DEFAULT_AUTO_SHUTDOWN_MINUTES),
            
            # Advanced Settings
            "humidity_comfort_enable": config.get("humidity_comfort_enable", True),
            "comfort_temp_min_offset": config.get("comfort_range_min_offset", DEFAULT_COMFORT_TEMP_MIN_OFFSET),
            "comfort_temp_max_offset": config.get("comfort_range_max_offset", DEFAULT_COMFORT_TEMP_MAX_OFFSET),
        })
        
        # === DIAGNOSTICS (Read-only) ===
        attributes.update({
            # Current Measurements
            "indoor_temperature": self.coordinator.data.get("indoor_temperature"),
            "outdoor_temperature": self.coordinator.data.get("outdoor_temperature"),
            "outdoor_running_mean": self.coordinator.data.get("outdoor_running_mean"),
            
            # ASHRAE Calculations
            "adaptive_comfort_temp": round(self.coordinator.data.get("adaptive_comfort_temp", 0), 1),
            "comfort_range_min": round(base_min, 1),
            "comfort_range_max": round(base_max, 1),
        })
        
        # Only show effective range if it differs from base range
        if abs(effective_min - base_min) > 0.1 or abs(effective_max - base_max) > 0.1:
            attributes.update({
                "effective_comfort_min": round(effective_min, 1),
                "effective_comfort_max": round(effective_max, 1),
            })
        
        # Add correction offsets (only if non-zero)
        air_velocity_offset = self.coordinator.data.get("air_velocity_offset", 0)
        humidity_offset = self.coordinator.data.get("humidity_offset", 0)
        if abs(air_velocity_offset) > 0.01:
            attributes["air_velocity_offset"] = round(air_velocity_offset, 2)
        if abs(humidity_offset) > 0.01:
            attributes["humidity_offset"] = round(humidity_offset, 2)
        
        # Natural ventilation detailed diagnostics
        attributes["natural_ventilation_diagnostics"] = self._get_natural_ventilation_diagnostics()
        
        return attributes
    
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
    
    def _get_natural_ventilation_diagnostics(self):
        """Get natural ventilation diagnostic information with clear conditions."""
        if not self.coordinator.data:
            return {"status": "No data available"}
        
        outdoor_temp = self.coordinator.data.get("outdoor_temperature", 0) or 0
        indoor_temp = self.coordinator.data.get("indoor_temperature", 0) or 0
        comfort_max = self.coordinator.data.get("comfort_temp_max", 28.0) or 28.0
        threshold = self.coordinator.config.get("natural_ventilation_threshold", 2.0)
        temp_diff = indoor_temp - outdoor_temp
        
        # Check each condition for natural ventilation
        conditions = {
            "indoor_above_comfort_max": indoor_temp > comfort_max,
            "outdoor_cooler_than_indoor": outdoor_temp < indoor_temp,  
            "temperature_difference_sufficient": temp_diff >= threshold,
        }
        
        optimal = all(conditions.values())
        
        return {
            "status": "optimal" if optimal else "not_optimal",
            "temperature_difference": round(temp_diff, 1),
            "conditions": {
                "indoor_too_warm": conditions["indoor_above_comfort_max"],
                "outdoor_is_cooler": conditions["outdoor_cooler_than_indoor"],
                "sufficient_temp_difference": conditions["temp_difference_sufficient"],
            },
            "summary": f"Indoor {indoor_temp:.1f}°C, Outdoor {outdoor_temp:.1f}°C, Diff {temp_diff:.1f}°C (need ≥{threshold}°C)",
        }
