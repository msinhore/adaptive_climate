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
    DEFAULT_COMFORT_TEMP_MIN_OFFSET,
    DEFAULT_COMFORT_TEMP_MAX_OFFSET,
    DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
    DEFAULT_AIR_VELOCITY,
    DEFAULT_NATURAL_VENTILATION_THRESHOLD,
    DEFAULT_SETBACK_TEMPERATURE_OFFSET,
    DEFAULT_AUTO_SHUTDOWN_MINUTES,
)
from .coordinator import AdaptiveClimateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Adaptive Climate number entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        MinComfortTempNumber(coordinator, config_entry),
        MaxComfortTempNumber(coordinator, config_entry),
        TemperatureChangeThresholdNumber(coordinator, config_entry),
        AirVelocityNumber(coordinator, config_entry),
        NaturalVentilationThresholdNumber(coordinator, config_entry),
        SetbackTemperatureOffsetNumber(coordinator, config_entry),
        AutoShutdownMinutesNumber(coordinator, config_entry),
    ]
    
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
            "sw_version": "0.1.3",
        }
        self._attr_entity_category = EntityCategory.CONFIG


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
        self._attr_native_value = 18.0

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
        self._attr_native_value = 27.0

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

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.coordinator.config.get("temperature_change_threshold", DEFAULT_TEMPERATURE_CHANGE_THRESHOLD)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
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

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.coordinator.config.get("air_velocity", DEFAULT_AIR_VELOCITY)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
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

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.coordinator.config.get("natural_ventilation_threshold", DEFAULT_NATURAL_VENTILATION_THRESHOLD)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
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

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.coordinator.config.get("setback_temperature_offset", DEFAULT_SETBACK_TEMPERATURE_OFFSET)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
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

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.coordinator.config.get("auto_shutdown_minutes", DEFAULT_AUTO_SHUTDOWN_MINUTES)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self.coordinator.update_config({"auto_shutdown_minutes": value})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
