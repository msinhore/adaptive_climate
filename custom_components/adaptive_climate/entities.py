"""Bridge entities for Adaptive Climate integration.

This module implements bridge entities that act as UI interface for config_entry.data,
providing user-friendly controls without affecting the core coordinator logic.
The coordinator continues to work normally, consulting the binary_sensor for configuration.
Bridge entities only serve as a configuration UI layer.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity  
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN, 
    COMFORT_CATEGORIES,
    DEFAULT_MIN_COMFORT_TEMP,
    DEFAULT_MAX_COMFORT_TEMP,
    DEFAULT_AIR_VELOCITY,
    DEFAULT_SETBACK_TEMPERATURE_OFFSET,
    DEFAULT_NATURAL_VENTILATION_THRESHOLD,
    DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
)

_LOGGER = logging.getLogger(__name__)

# Configuration mapping for bridge UI entities - only for initial setup interface
BRIDGE_CONFIG_MAPPING = {
    # Number entities for config_entry.data
    "min_comfort_temp": {
        "type": "number",
        "name": "Minimum Comfort Temperature", 
        "min": 15.0, "max": 25.0, "step": 0.5, "unit": "°C",
        "default": DEFAULT_MIN_COMFORT_TEMP,
        "icon": "mdi:thermometer-low"
    },
    "max_comfort_temp": {
        "type": "number", 
        "name": "Maximum Comfort Temperature",
        "min": 25.0, "max": 35.0, "step": 0.5, "unit": "°C", 
        "default": DEFAULT_MAX_COMFORT_TEMP,
        "icon": "mdi:thermometer-high"
    },
    "air_velocity": {
        "type": "number",
        "name": "Air Velocity",
        "min": 0.0, "max": 2.0, "step": 0.1, "unit": "m/s",
        "default": DEFAULT_AIR_VELOCITY, 
        "icon": "mdi:weather-windy"
    },
    "setback_temperature_offset": {
        "type": "number",
        "name": "Setback Temperature Offset", 
        "min": 0.0, "max": 5.0, "step": 0.5, "unit": "°C",
        "default": DEFAULT_SETBACK_TEMPERATURE_OFFSET,
        "icon": "mdi:thermometer-minus"
    },
    "natural_ventilation_threshold": {
        "type": "number",
        "name": "Natural Ventilation Threshold",
        "min": 0.5, "max": 10.0, "step": 0.5, "unit": "°C", 
        "default": DEFAULT_NATURAL_VENTILATION_THRESHOLD,
        "icon": "mdi:window-open"
    },
    "temperature_change_threshold": {
        "type": "number", 
        "name": "Temperature Change Threshold",
        "min": 0.1, "max": 3.0, "step": 0.1, "unit": "°C",
        "default": DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
        "icon": "mdi:thermometer-alert"
    },
    
    # Switch entities for config_entry.data
    "energy_save_mode": {
        "type": "switch",
        "name": "Energy Save Mode",
        "default": True,
        "icon": "mdi:leaf"
    },
    "natural_ventilation_enable": {
        "type": "switch", 
        "name": "Natural Ventilation",
        "default": True,
        "icon": "mdi:window-open-variant"
    },
    "adaptive_air_velocity": {
        "type": "switch",
        "name": "Adaptive Air Velocity", 
        "default": False,
        "icon": "mdi:fan-auto"
    },
    "humidity_comfort_enable": {
        "type": "switch",
        "name": "Humidity Comfort",
        "default": True, 
        "icon": "mdi:water-percent"
    },
    "comfort_precision_mode": {
        "type": "switch",
        "name": "Precision Mode",
        "default": False,
        "icon": "mdi:target"
    },
    "use_occupancy_features": {
        "type": "switch", 
        "name": "Occupancy Features",
        "default": True,
        "icon": "mdi:account-check"
    },
    "auto_shutdown_enable": {
        "type": "switch",
        "name": "Auto Shutdown",
        "default": False,
        "icon": "mdi:power-standby"
    },
    "use_operative_temperature": {
        "type": "switch",
        "name": "Use Operative Temperature", 
        "default": False,
        "icon": "mdi:thermometer-check"
    },
    
    # Select entities for config_entry.data
    "comfort_category": {
        "type": "select",
        "name": "Comfort Category",
        "options": ["I", "II", "III"],
        "default": "II",
        "icon": "mdi:chart-bell-curve"
    }
}


def async_setup_device_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up bridge entities for UI configuration interface.
    
    Creates bridge entities that provide user-friendly UI controls for config_entry.data
    without affecting the core coordinator logic. Coordinator continues to work normally.
    """
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Create device info shared by all entities
    device_info = DeviceInfo(
        identifiers={(DOMAIN, config_entry.entry_id)},
        name=config_entry.title,
        manufacturer="Adaptive Climate",
        model="ASHRAE 55 Controller", 
        sw_version="1.0.0",
        configuration_url=f"homeassistant://config/integrations/integration/{DOMAIN}",
    )
    
    entities = []
    
    # Create bridge entities for UI configuration (affecting config_entry.data only)
    for config_key, config_info in BRIDGE_CONFIG_MAPPING.items():
        entity_type = config_info["type"]
        
        if entity_type == "number":
            entities.append(
                AdaptiveClimateConfigBridge(
                    hass, config_entry, device_info, config_key, config_info
                )
            )
        elif entity_type == "switch":
            entities.append(
                AdaptiveClimateSwitchBridge(
                    hass, config_entry, device_info, config_key, config_info
                )
            )
        elif entity_type == "select":
            entities.append(
                AdaptiveClimateSelectBridge(
                    hass, config_entry, device_info, config_key, config_info
                )
            )
    
    # Add utility buttons for configuration
    entities.extend([
        AdaptiveClimateActionButton(
            hass, config_entry, device_info, 
            "reset_outdoor_history", "Reset Outdoor History"
        ),
    ])
    
    # Add diagnostic sensors (read-only, from coordinator data)
    entities.extend([
        AdaptiveClimateDiagnosticSensor(
            coordinator, config_entry, device_info, 
            "adaptive_comfort_temp", "Adaptive Comfort Temperature", "°C"
        ),
        AdaptiveClimateDiagnosticSensor(
            coordinator, config_entry, device_info,
            "outdoor_running_mean", "Outdoor Running Mean", "°C"
        ),
        AdaptiveClimateDiagnosticSensor(
            coordinator, config_entry, device_info,
            "comfort_temp_min", "Comfort Range Min", "°C"
        ),
        AdaptiveClimateDiagnosticSensor(
            coordinator, config_entry, device_info,
            "comfort_temp_max", "Comfort Range Max", "°C" 
        ),
    ])
    
    async_add_entities(entities)


# === BRIDGE ENTITY BASE CLASS (UI ONLY) ===

class AdaptiveClimateUIBridgeEntity:
    """Base class for bridge entities that provide UI interface to config_entry.data.
    
    These entities act only as UI configuration interface without affecting the core
    coordinator logic. The coordinator continues to work normally consulting binary_sensor.
    """
    
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, device_info: DeviceInfo, 
                 config_key: str, config_info: dict[str, Any]):
        """Initialize the UI bridge entity."""
        self.hass = hass
        self.config_entry = config_entry
        self._device_info = device_info
        self._config_key = config_key
        self._config_info = config_info
        
        # Set entity attributes
        self._attr_unique_id = f"{config_entry.entry_id}_ui_{config_key}"
        self._attr_name = config_info["name"]
        self._attr_icon = config_info.get("icon")
        
        # Show in Controls tab for easy access
        # self._attr_entity_category = EntityCategory.CONFIG
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return self._device_info
    
    @property
    def native_value(self) -> Any:
        """Return current value from config_entry.data."""
        default_value = self._config_info.get("default")
        return self.config_entry.data.get(self._config_key, default_value)
    
    async def async_set_native_value(self, value: Any) -> None:
        """Update value in config_entry.data (UI interface only)."""
        try:
            # Update config_entry.data for persistence
            new_data = {**self.config_entry.data, self._config_key: value}
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data
            )
            
            _LOGGER.debug("UI Bridge updated config_entry.data: %s = %s", self._config_key, value)
            
        except Exception as err:
            _LOGGER.error("Error updating config_entry.data via UI bridge %s = %s: %s", 
                         self._config_key, value, err)
            raise


# === BRIDGE ENTITY IMPLEMENTATIONS (UI ONLY) ===

class AdaptiveClimateConfigBridge(AdaptiveClimateUIBridgeEntity, NumberEntity):
    """Number entity bridge for UI configuration of numeric values."""
    
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, device_info: DeviceInfo,
                 config_key: str, config_info: dict[str, Any]):
        """Initialize the number bridge entity."""
        super().__init__(hass, config_entry, device_info, config_key, config_info)
        
        # Set number-specific attributes from config mapping
        self._attr_native_min_value = config_info.get("min", 0)
        self._attr_native_max_value = config_info.get("max", 100) 
        self._attr_native_step = config_info.get("step", 1)
        self._attr_native_unit_of_measurement = config_info.get("unit")
        self._attr_mode = "slider"  # Use slider mode for better UX


class AdaptiveClimateSwitchBridge(AdaptiveClimateUIBridgeEntity, SwitchEntity):
    """Switch entity bridge for UI configuration of boolean values."""
    
    @property
    def is_on(self) -> bool:
        """Return if the switch is on."""
        value = self.native_value
        return bool(value) if value is not None else False
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.async_set_native_value(True)
        
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.async_set_native_value(False)


class AdaptiveClimateSelectBridge(AdaptiveClimateUIBridgeEntity, SelectEntity):
    """Select entity bridge for UI configuration of choice values."""
    
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, device_info: DeviceInfo,
                 config_key: str, config_info: dict[str, Any]):
        """Initialize the select bridge entity."""
        super().__init__(hass, config_entry, device_info, config_key, config_info)
        
        # Set select-specific attributes
        self._attr_options = config_info.get("options", [])
    
    @property
    def current_option(self) -> str | None:
        """Return current option."""
        value = self.native_value
        return str(value) if value is not None else None
    
    async def async_select_option(self, option: str) -> None:
        """Select new option."""
        await self.async_set_native_value(option)


# === UTILITY ENTITIES ===

class AdaptiveClimateActionButton(ButtonEntity):
    """Button entity for utility actions (UI only)."""
    
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, device_info: DeviceInfo, 
                 action: str, name: str):
        """Initialize the button."""
        self.hass = hass
        self.config_entry = config_entry
        self._device_info = device_info
        self._action = action
        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_action_{action}"
        self._attr_icon = "mdi:refresh" if "reset" in action else "mdi:cog"
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return self._device_info
    
    async def async_press(self) -> None:
        """Handle button press."""
        if self._action == "reset_outdoor_history":
            # Call coordinator method if available
            coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
            if coordinator and hasattr(coordinator, 'reset_outdoor_history'):
                await coordinator.reset_outdoor_history()
                _LOGGER.info("Outdoor temperature history reset via UI button")


class AdaptiveClimateDiagnosticSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity for diagnostic information (read-only)."""
    
    def __init__(self, coordinator, config_entry: ConfigEntry, device_info: DeviceInfo,
                 sensor_key: str, name: str, unit: str | None = None):
        """Initialize the diagnostic sensor.""" 
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._device_info = device_info
        self._sensor_key = sensor_key
        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_diag_{sensor_key}"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = "mdi:information"
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return self._device_info
    
    @property
    def native_value(self) -> Any:
        """Return sensor value from coordinator data."""
        if hasattr(self.coordinator, 'data') and self.coordinator.data:
            value = self.coordinator.data.get(self._sensor_key)
            # Round temperature values for better display
            if isinstance(value, (int, float)) and self._attr_native_unit_of_measurement == "°C":
                return round(float(value), 1)
            return value
        return None
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success and 
            self.coordinator.data is not None
        )
