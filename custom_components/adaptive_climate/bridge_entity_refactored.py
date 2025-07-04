"""Refactored Bridge Entity Example - NumberBridgeEntity.

This file demonstrates the improved bridge entity architecture using
CoordinatorEntity and async_write_ha_state instead of hass.states.async_set.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AdaptiveClimateCoordinator

_LOGGER = logging.getLogger(__name__)


class RefactoredNumberBridgeEntity(CoordinatorEntity, NumberEntity):
    """Refactored number entity that bridges via coordinator.
    
    This is an improved version that:
    - Inherits from CoordinatorEntity for automatic state management
    - Uses async_write_ha_state() instead of hass.states.async_set()
    - Leverages coordinator caching and update mechanisms
    - Provides better logging and error handling
    """

    def __init__(
        self,
        coordinator: AdaptiveClimateCoordinator,
        config_entry: ConfigEntry,
        attribute_name: str,
        entity_config: dict[str, Any],
    ) -> None:
        """Initialize the refactored bridge entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attribute_name = attribute_name
        self._entity_config = entity_config
        
        _LOGGER.debug(
            "Initializing refactored bridge entity: %s (attribute: %s)",
            entity_config.get("name", attribute_name), attribute_name
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID for the entity."""
        return f"{self._config_entry.entry_id}_{self._attribute_name}_bridge_v2"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        base_name = self._entity_config.get("name", self._attribute_name.replace("_", " ").title())
        return f"{base_name} (Refactored)"

    @property
    def icon(self) -> str | None:
        """Return the icon for the entity."""
        return self._entity_config.get("icon")

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        return self._entity_config.get("min_value", 0.0)

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        return self._entity_config.get("max_value", 100.0)

    @property
    def native_step(self) -> float:
        """Return the step value."""
        return self._entity_config.get("step", 1.0)

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        return self._entity_config.get("unit")

    @property
    def native_value(self) -> float | None:
        """Return the current value from coordinator.
        
        This uses the coordinator's cached data instead of directly
        accessing hass.states, providing better performance and consistency.
        """
        try:
            # Use coordinator method for clean attribute access
            value = self.coordinator.get_bridge_attribute_value(self._attribute_name)
            
            if value is not None:
                float_value = float(value)
                _LOGGER.debug(
                    "Retrieved value for %s: %s (from coordinator)",
                    self._attribute_name, float_value
                )
                return float_value
            else:
                _LOGGER.debug("No value found for %s", self._attribute_name)
                return None
                
        except (ValueError, TypeError) as err:
            _LOGGER.warning(
                "Invalid value for %s: %s (error: %s)", 
                self._attribute_name, value, err
            )
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the value via coordinator.
        
        This uses the coordinator's update method instead of directly
        manipulating hass.states, providing better integration with
        the coordinator's state management.
        """
        try:
            _LOGGER.info(
                "Refactored bridge entity setting %s = %s",
                self._attribute_name, value
            )
            
            # Validate value range
            if value < self.native_min_value or value > self.native_max_value:
                _LOGGER.warning(
                    "Value %s for %s is outside valid range [%s, %s]",
                    value, self._attribute_name, 
                    self.native_min_value, self.native_max_value
                )
                return
            
            # Update via coordinator (cleaner than hass.states.async_set)
            await self.coordinator.update_bridge_attribute(self._attribute_name, value)
            
            # Use async_write_ha_state() for proper HA integration
            self.async_write_ha_state()
            
            _LOGGER.debug(
                "Successfully updated %s = %s via coordinator",
                self._attribute_name, value
            )
            
        except Exception as err:
            _LOGGER.error(
                "Error setting value for %s = %s: %s",
                self._attribute_name, value, err
            )
            raise

    @property
    def available(self) -> bool:
        """Return if entity is available.
        
        Leverages coordinator's availability tracking.
        """
        return (
            self.coordinator.last_update_success and
            self.coordinator.data is not None
        )

    @property
    def should_poll(self) -> bool:
        """No polling needed - coordinator handles updates."""
        return False

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass.
        
        CoordinatorEntity handles the coordinator connection automatically,
        so we don't need manual event listeners.
        """
        await super().async_added_to_hass()
        _LOGGER.debug(
            "Refactored bridge entity %s added to hass (attribute: %s)",
            self.name, self._attribute_name
        )

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        _LOGGER.debug(
            "Refactored bridge entity %s being removed from hass",
            self.name
        )


class RefactoredSwitchBridgeEntity(CoordinatorEntity, SwitchEntity):
    """Refactored switch entity that bridges via coordinator."""

    def __init__(
        self,
        coordinator: AdaptiveClimateCoordinator,
        config_entry: ConfigEntry,
        attribute_name: str,
        entity_config: dict[str, Any],
    ) -> None:
        """Initialize the refactored switch bridge entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attribute_name = attribute_name
        self._entity_config = entity_config
        
        _LOGGER.debug(
            "Initializing refactored switch bridge entity: %s (attribute: %s)",
            entity_config.get("name", attribute_name), attribute_name
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID for the entity."""
        return f"{self._config_entry.entry_id}_{self._attribute_name}_switch_bridge_v2"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        base_name = self._entity_config.get("name", self._attribute_name.replace("_", " ").title())
        return f"{base_name} (Refactored)"

    @property
    def icon(self) -> str | None:
        """Return the icon for the entity."""
        return self._entity_config.get("icon")

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        try:
            value = self.coordinator.get_bridge_attribute_value(self._attribute_name)
            if value is not None:
                bool_value = bool(value)
                _LOGGER.debug(
                    "Retrieved switch state for %s: %s (from coordinator)",
                    self._attribute_name, bool_value
                )
                return bool_value
            return None
        except Exception as err:
            _LOGGER.warning(
                "Error getting switch state for %s: %s", 
                self._attribute_name, err
            )
            return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        try:
            _LOGGER.info(
                "Refactored switch bridge entity turning on %s",
                self._attribute_name
            )
            await self.coordinator.update_bridge_attribute(self._attribute_name, True)
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error(
                "Error turning on switch %s: %s",
                self._attribute_name, err
            )
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        try:
            _LOGGER.info(
                "Refactored switch bridge entity turning off %s",
                self._attribute_name
            )
            await self.coordinator.update_bridge_attribute(self._attribute_name, False)
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.error(
                "Error turning off switch %s: %s",
                self._attribute_name, err
            )
            raise


class RefactoredSelectBridgeEntity(CoordinatorEntity, SelectEntity):
    """Refactored select entity that bridges via coordinator."""

    def __init__(
        self,
        coordinator: AdaptiveClimateCoordinator,
        config_entry: ConfigEntry,
        attribute_name: str,
        entity_config: dict[str, Any],
    ) -> None:
        """Initialize the refactored select bridge entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attribute_name = attribute_name
        self._entity_config = entity_config
        
        _LOGGER.debug(
            "Initializing refactored select bridge entity: %s (attribute: %s)",
            entity_config.get("name", attribute_name), attribute_name
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID for the entity."""
        return f"{self._config_entry.entry_id}_{self._attribute_name}_select_bridge_v2"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        base_name = self._entity_config.get("name", self._attribute_name.replace("_", " ").title())
        return f"{base_name} (Refactored)"

    @property
    def icon(self) -> str | None:
        """Return the icon for the entity."""
        return self._entity_config.get("icon")

    @property
    def options(self) -> list[str]:
        """Return the list of available options."""
        return self._entity_config.get("options", [])

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        try:
            value = self.coordinator.get_bridge_attribute_value(self._attribute_name)
            if value is not None and str(value) in self.options:
                option = str(value)
                _LOGGER.debug(
                    "Retrieved select option for %s: %s (from coordinator)",
                    self._attribute_name, option
                )
                return option
            return None
        except Exception as err:
            _LOGGER.warning(
                "Error getting select option for %s: %s", 
                self._attribute_name, err
            )
            return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        try:
            if option not in self.options:
                _LOGGER.warning(
                    "Invalid option %s for %s. Valid options: %s",
                    option, self._attribute_name, self.options
                )
                return
                
            _LOGGER.info(
                "Refactored select bridge entity setting %s = %s",
                self._attribute_name, option
            )
            
            await self.coordinator.update_bridge_attribute(self._attribute_name, option)
            self.async_write_ha_state()
            
        except Exception as err:
            _LOGGER.error(
                "Error selecting option %s for %s: %s",
                option, self._attribute_name, err
            )
            raise


class RefactoredSensorBridgeEntity(CoordinatorEntity, SensorEntity):
    """Refactored sensor entity that bridges via coordinator (read-only)."""

    def __init__(
        self,
        coordinator: AdaptiveClimateCoordinator,
        config_entry: ConfigEntry,
        attribute_name: str,
        entity_config: dict[str, Any],
    ) -> None:
        """Initialize the refactored sensor bridge entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attribute_name = attribute_name
        self._entity_config = entity_config
        
        _LOGGER.debug(
            "Initializing refactored sensor bridge entity: %s (attribute: %s)",
            entity_config.get("name", attribute_name), attribute_name
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID for the entity."""
        return f"{self._config_entry.entry_id}_{self._attribute_name}_sensor_bridge_v2"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        base_name = self._entity_config.get("name", self._attribute_name.replace("_", " ").title())
        return f"{base_name} (Refactored)"

    @property
    def icon(self) -> str | None:
        """Return the icon for the entity."""
        return self._entity_config.get("icon")

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        return self._entity_config.get("unit")

    @property
    def device_class(self) -> str | None:
        """Return the device class."""
        return self._entity_config.get("device_class")

    @property
    def native_value(self) -> Any:
        """Return the current value."""
        try:
            value = self.coordinator.get_bridge_attribute_value(self._attribute_name)
            _LOGGER.debug(
                "Retrieved sensor value for %s: %s (from coordinator)",
                self._attribute_name, value
            )
            return value
        except Exception as err:
            _LOGGER.warning(
                "Error getting sensor value for %s: %s", 
                self._attribute_name, err
            )
            return None


def create_refactored_outdoor_temp_entity(
    coordinator: AdaptiveClimateCoordinator,
    config_entry: ConfigEntry,
) -> RefactoredNumberBridgeEntity:
    """Create a refactored outdoor temperature bridge entity as example."""
    entity_config = {
        "name": "Outdoor Temperature (Refactored)",
        "min_value": -30.0,
        "max_value": 50.0,
        "step": 0.1,
        "unit": "°C",
        "icon": "mdi:thermometer",
    }
    
    return RefactoredNumberBridgeEntity(
        coordinator=coordinator,
        config_entry=config_entry,
        attribute_name="outdoor_temp",
        entity_config=entity_config,
    )


def create_refactored_bridge_entities(
    coordinator: AdaptiveClimateCoordinator,
    config_entry: ConfigEntry,
    platform: str,
) -> list[CoordinatorEntity]:
    """Create refactored bridge entities for the specified platform."""
    entities = []
    
    # Use the same configuration as the original bridge entities
    from .bridge_entity import BRIDGE_ENTITY_CONFIG
    
    if platform not in BRIDGE_ENTITY_CONFIG:
        return entities
    
    platform_config = BRIDGE_ENTITY_CONFIG[platform]
    
    for attribute_name, entity_config in platform_config.items():
        if platform == "number":
            entity = RefactoredNumberBridgeEntity(
                coordinator, config_entry, attribute_name, entity_config
            )
        elif platform == "switch":
            entity = RefactoredSwitchBridgeEntity(
                coordinator, config_entry, attribute_name, entity_config
            )
        elif platform == "select":
            entity = RefactoredSelectBridgeEntity(
                coordinator, config_entry, attribute_name, entity_config
            )
        elif platform == "sensor":
            entity = RefactoredSensorBridgeEntity(
                coordinator, config_entry, attribute_name, entity_config
            )
        else:
            continue
            
        entities.append(entity)
    
    _LOGGER.info(
        "Created %d refactored %s bridge entities: %s",
        len(entities), platform, [e.name for e in entities]
    )
    
    return entities
