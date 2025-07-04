"""Number platform for Adaptive Climate."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import (
    DOMAIN,
    VERSION,
    DEFAULT_COMFORT_TEMP_MIN_OFFSET,
    DEFAULT_COMFORT_TEMP_MAX_OFFSET,
    DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
    DEFAULT_AIR_VELOCITY,
    DEFAULT_NATURAL_VENTILATION_THRESHOLD,
    DEFAULT_SETBACK_TEMPERATURE_OFFSET,
    DEFAULT_AUTO_SHUTDOWN_MINUTES,
    DEFAULT_MIN_COMFORT_TEMP,
    DEFAULT_MAX_COMFORT_TEMP,
    DEFAULT_PROLONGED_ABSENCE_MINUTES,
)
from .coordinator import AdaptiveClimateCoordinator
from .bridge_entity import create_bridge_entities
# Import refactored entity for testing
from .bridge_entity_refactored import create_refactored_outdoor_temp_entity, create_stage1b_test_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Adaptive Climate number entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        # Core temperature settings
        MinComfortTempNumber(coordinator, config_entry),
        MaxComfortTempNumber(coordinator, config_entry),
        TemperatureChangeThresholdNumber(coordinator, config_entry),
        
        # Air velocity and natural ventilation
        AirVelocityNumber(coordinator, config_entry),
        NaturalVentilationThresholdNumber(coordinator, config_entry),
        
        # Setback and occupancy settings
        SetbackTemperatureOffsetNumber(coordinator, config_entry),
        ProlongedAbsenceMinutesNumber(coordinator, config_entry),
        AutoShutdownMinutesNumber(coordinator, config_entry),
        
        # Advanced comfort zone offsets
        ComfortTempMinOffsetNumber(coordinator, config_entry),
        ComfortTempMaxOffsetNumber(coordinator, config_entry),
    ]
    
    # Add bridge entities for UI helpers
    bridge_entities = create_bridge_entities(hass, config_entry, "number")
    entities.extend(bridge_entities)
    
    # Add refactored outdoor temperature entity for testing
    refactored_entity = create_refactored_outdoor_temp_entity(coordinator, config_entry)
    entities.append(refactored_entity)
    
    # Add Stage 1b test entities
    stage1b_entities = create_stage1b_test_entities(coordinator, config_entry)
    entities.extend(stage1b_entities)
    
    _LOGGER.info(
        "STAGE1B_SETUP: Added %d test entities for validation. Total entities: %d",
        len(stage1b_entities),
        len(entities)
    )
    
    async_add_entities(entities)


class AdaptiveClimateNumberBase(CoordinatorEntity, NumberEntity):
    """Base class for Adaptive Climate number entities."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": config_entry.data.get("name", "Adaptive Climate"),
            "manufacturer": "ASHRAE",
            "model": "Adaptive Climate Controller",
            "sw_version": VERSION,
        }
        # Remove entity_category to make numbers appear in Controls tab
        # self._attr_entity_category = EntityCategory.CONFIG


class MinComfortTempNumber(AdaptiveClimateNumberBase):
    """Number entity for minimum comfort temperature."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_min_comfort_temp"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Min Comfort Temperature"
        self._attr_icon = "mdi:thermometer-low"
        self._attr_native_min_value = 15.0
        self._attr_native_max_value = 22.0
        self._attr_native_step = 0.1
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_native_value = coordinator.config.get("min_comfort_temp", DEFAULT_MIN_COMFORT_TEMP)
    
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._attr_native_value
    
    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        self._attr_native_value = value
        await self.coordinator.update_config({"min_comfort_temp": value})
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class MaxComfortTempNumber(AdaptiveClimateNumberBase):
    """Number entity for maximum comfort temperature."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_max_comfort_temp"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Max Comfort Temperature"
        self._attr_icon = "mdi:thermometer-high"
        self._attr_native_min_value = 25.0
        self._attr_native_max_value = 32.0
        self._attr_native_step = 0.1
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_native_value = coordinator.config.get("max_comfort_temp", DEFAULT_MAX_COMFORT_TEMP)
    
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._attr_native_value
    
    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        self._attr_native_value = value
        await self.coordinator.update_config({"max_comfort_temp": value})
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class TemperatureChangeThresholdNumber(AdaptiveClimateNumberBase):
    """Number entity for temperature change threshold."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_temperature_change_threshold"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Temperature Change Threshold"
        self._attr_icon = "mdi:thermometer-alert"
        self._attr_native_min_value = 0.1
        self._attr_native_max_value = 3.0
        self._attr_native_step = 0.1
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_native_value = coordinator.config.get("temperature_change_threshold", DEFAULT_TEMPERATURE_CHANGE_THRESHOLD)

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        self._attr_native_value = value
        await self.coordinator.update_config({"temperature_change_threshold": value})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class AirVelocityNumber(AdaptiveClimateNumberBase):
    """Number entity for air velocity."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_air_velocity"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Air Velocity"
        self._attr_icon = "mdi:weather-windy"
        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 2.0
        self._attr_native_step = 0.01
        self._attr_native_unit_of_measurement = "m/s"
        self._attr_native_value = coordinator.config.get("air_velocity", DEFAULT_AIR_VELOCITY)

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        self._attr_native_value = value
        await self.coordinator.update_config({"air_velocity": value})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class NaturalVentilationThresholdNumber(AdaptiveClimateNumberBase):
    """Number entity for natural ventilation threshold."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_natural_ventilation_threshold"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Natural Ventilation Threshold"
        self._attr_icon = "mdi:window-open"
        self._attr_native_min_value = 0.5
        self._attr_native_max_value = 10.0
        self._attr_native_step = 0.1
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_native_value = coordinator.config.get("natural_ventilation_threshold", DEFAULT_NATURAL_VENTILATION_THRESHOLD)

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        self._attr_native_value = value
        await self.coordinator.update_config({"natural_ventilation_threshold": value})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class SetbackTemperatureOffsetNumber(AdaptiveClimateNumberBase):
    """Number entity for setback temperature offset."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_setback_temperature_offset"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Setback Temperature Offset"
        self._attr_icon = "mdi:thermometer-off"
        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 10.0
        self._attr_native_step = 0.1
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_native_value = coordinator.config.get("setback_temperature_offset", DEFAULT_SETBACK_TEMPERATURE_OFFSET)

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        self._attr_native_value = value
        await self.coordinator.update_config({"setback_temperature_offset": value})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class AutoShutdownMinutesNumber(AdaptiveClimateNumberBase):
    """Number entity for auto shutdown minutes."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_auto_shutdown_minutes"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Auto Shutdown Minutes"
        self._attr_icon = "mdi:timer-off"
        self._attr_native_min_value = 5
        self._attr_native_max_value = 480  # 8 hours
        self._attr_native_step = 5
        self._attr_native_unit_of_measurement = "min"
        self._attr_native_value = coordinator.config.get("auto_shutdown_minutes", DEFAULT_AUTO_SHUTDOWN_MINUTES)

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        self._attr_native_value = value
        await self.coordinator.update_config({"auto_shutdown_minutes": value})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class ProlongedAbsenceMinutesNumber(AdaptiveClimateNumberBase):
    """Number entity for prolonged absence minutes."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_prolonged_absence_minutes"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Prolonged Absence Minutes"
        self._attr_icon = "mdi:timer-outline"
        self._attr_native_min_value = 10
        self._attr_native_max_value = 240  # 4 hours
        self._attr_native_step = 5
        self._attr_native_unit_of_measurement = "min"
        self._attr_native_value = coordinator.config.get("prolonged_absence_minutes", DEFAULT_PROLONGED_ABSENCE_MINUTES)

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        self._attr_native_value = value
        await self.coordinator.update_config({"prolonged_absence_minutes": value})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class ComfortTempMinOffsetNumber(AdaptiveClimateNumberBase):
    """Number entity for comfort temperature minimum offset."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_comfort_temp_min_offset"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Comfort Min Offset"
        self._attr_icon = "mdi:thermometer-minus"
        self._attr_native_min_value = -5.0
        self._attr_native_max_value = 0.0
        self._attr_native_step = 0.1
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_native_value = coordinator.config.get("comfort_range_min_offset", DEFAULT_COMFORT_TEMP_MIN_OFFSET)
    
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._attr_native_value
    
    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        self._attr_native_value = value
        await self.coordinator.update_config({"comfort_range_min_offset": value})
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class ComfortTempMaxOffsetNumber(AdaptiveClimateNumberBase):
    """Number entity for comfort temperature maximum offset."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_comfort_temp_max_offset"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Comfort Max Offset"
        self._attr_icon = "mdi:thermometer-plus"
        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 5.0
        self._attr_native_step = 0.1
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = NumberDeviceClass.TEMPERATURE
        self._attr_native_value = coordinator.config.get("comfort_range_max_offset", DEFAULT_COMFORT_TEMP_MAX_OFFSET)
    
    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._attr_native_value
    
    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        self._attr_native_value = value
        await self.coordinator.update_config({"comfort_range_max_offset": value})
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class AdaptiveClimateConfigNumber(CoordinatorEntity, NumberEntity):
    """Number entity for configuration values (appears in Controls tab)."""
    
    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry, 
                 option_key: str, name: str, min_val: float, max_val: float, step: float, unit: str):
        """Initialize the number."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._option_key = option_key
        self._attr_unique_id = f"{config_entry.entry_id}_config_{option_key}"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} {name}"
        # Remove entity_category to make config numbers appear in Controls tab
        # self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": config_entry.data.get("name", "Adaptive Climate"),
            "manufacturer": "ASHRAE",
            "model": "Adaptive Climate Controller",
            "sw_version": VERSION,
        }
        
        # Set appropriate device class and icon based on unit
        if unit == "°C":
            self._attr_device_class = NumberDeviceClass.TEMPERATURE
            self._attr_icon = "mdi:thermometer"
        elif unit == "m/s":
            self._attr_icon = "mdi:fan"
        elif unit == "min":
            self._attr_icon = "mdi:clock-outline"
        else:
            self._attr_icon = "mdi:tune"
        
    @property
    def native_value(self) -> float | None:
        """Return current value."""
        return self.config_entry.options.get(self._option_key)
    
    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        new_options = dict(self.config_entry.options)
        new_options[self._option_key] = value
        self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
