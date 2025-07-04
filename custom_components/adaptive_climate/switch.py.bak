"""Switch platform for Adaptive Climate."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
    """Set up Adaptive Climate switch entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        UseOperativeTemperatureSwitch(coordinator, config_entry),
        EnergySaveModeSwitch(coordinator, config_entry),
        ComfortPrecisionModeSwitch(coordinator, config_entry),
        UseOccupancyFeaturesSwitch(coordinator, config_entry),
        NaturalVentilationEnableSwitch(coordinator, config_entry),
        AdaptiveAirVelocitySwitch(coordinator, config_entry),
        HumidityComfortEnableSwitch(coordinator, config_entry),
        AutoShutdownEnableSwitch(coordinator, config_entry),
    ]
    
    async_add_entities(entities)


class AdaptiveClimateSwitchBase(CoordinatorEntity, SwitchEntity):
    """Base class for Adaptive Climate switch entities."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": config_entry.data.get("name", "Adaptive Climate"),
            "manufacturer": "ASHRAE",
            "model": "Adaptive Climate Controller",
            "sw_version": VERSION,
        }

class UseOperativeTemperatureSwitch(AdaptiveClimateSwitchBase):
    """Switch entity for using operative temperature."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_use_operative_temperature"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Use Operative Temperature"
        self._attr_icon = "mdi:thermometer-plus"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.config.get("use_operative_temperature", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.update_config({"use_operative_temperature": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.update_config({"use_operative_temperature": False})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class EnergySaveModeSwitch(AdaptiveClimateSwitchBase):
    """Switch entity for energy save mode."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_energy_save_mode"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Energy Save Mode"
        self._attr_icon = "mdi:leaf"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.config.get("energy_save_mode", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.update_config({"energy_save_mode": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.update_config({"energy_save_mode": False})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class ComfortPrecisionModeSwitch(AdaptiveClimateSwitchBase):
    """Switch entity for comfort precision mode."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_comfort_precision_mode"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Comfort Precision Mode"
        self._attr_icon = "mdi:target"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.config.get("comfort_precision_mode", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.update_config({"comfort_precision_mode": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.update_config({"comfort_precision_mode": False})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class UseOccupancyFeaturesSwitch(AdaptiveClimateSwitchBase):
    """Switch entity for using occupancy features."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_use_occupancy_features"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Use Occupancy Features"
        self._attr_icon = "mdi:account-group"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.config.get("use_occupancy_features", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.update_config({"use_occupancy_features": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.update_config({"use_occupancy_features": False})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class NaturalVentilationEnableSwitch(AdaptiveClimateSwitchBase):
    """Switch entity for enabling natural ventilation."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_natural_ventilation_enable"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Natural Ventilation Enable"
        self._attr_icon = "mdi:window-open-variant"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.config.get("natural_ventilation_enable", True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.update_config({"natural_ventilation_enable": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.update_config({"natural_ventilation_enable": False})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class AdaptiveAirVelocitySwitch(AdaptiveClimateSwitchBase):
    """Switch entity for adaptive air velocity."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_adaptive_air_velocity"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Adaptive Air Velocity"
        self._attr_icon = "mdi:fan"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.config.get("adaptive_air_velocity", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.update_config({"adaptive_air_velocity": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.update_config({"adaptive_air_velocity": False})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class HumidityComfortEnableSwitch(AdaptiveClimateSwitchBase):
    """Switch entity for humidity comfort enable."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_humidity_comfort_enable"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Humidity Comfort Enable"
        self._attr_icon = "mdi:water-percent"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.config.get("humidity_comfort_enable", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.update_config({"humidity_comfort_enable": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.update_config({"humidity_comfort_enable": False})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class AutoShutdownEnableSwitch(AdaptiveClimateSwitchBase):
    """Switch entity for auto shutdown enable."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_auto_shutdown_enable"
        self._attr_name = f"{config_entry.data.get('name', 'Adaptive Climate')} Auto Shutdown Enable"
        self._attr_icon = "mdi:power-sleep"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.config.get("auto_shutdown_enable", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.update_config({"auto_shutdown_enable": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.update_config({"auto_shutdown_enable": False})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

