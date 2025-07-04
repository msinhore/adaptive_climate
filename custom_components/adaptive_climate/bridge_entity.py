"""Bridge entities for Adaptive Climate integration.

These entities act as UI helpers that bridge the frontend with the main binary_sensor
attributes. They allow modification of binary_sensor attributes via the UI without
directly altering config_entry or coordinator.config.
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
from homeassistant.helpers.entity import Entity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Entity configuration mapping
BRIDGE_ENTITY_CONFIG = {
    "number": {
        "outdoor_temp": {
            "name": "Outdoor Temperature",
            "min_value": -30.0,
            "max_value": 50.0,
            "step": 0.1,
            "unit": "°C",
            "icon": "mdi:thermometer",
        },
        "indoor_temp": {
            "name": "Indoor Temperature", 
            "min_value": 10.0,
            "max_value": 35.0,
            "step": 0.1,
            "unit": "°C",
            "icon": "mdi:home-thermometer",
        },
        "air_velocity": {
            "name": "Air Velocity",
            "min_value": 0.0,
            "max_value": 3.0,
            "step": 0.1,
            "unit": "m/s",
            "icon": "mdi:weather-windy",
        },
        "metabolic_rate": {
            "name": "Metabolic Rate",
            "min_value": 0.8,
            "max_value": 4.0,
            "step": 0.1,
            "unit": "met",
            "icon": "mdi:fire",
        },
        "clothing_insulation": {
            "name": "Clothing Insulation",
            "min_value": 0.0,
            "max_value": 3.0,
            "step": 0.1,
            "unit": "clo",
            "icon": "mdi:tshirt-crew",
        },
    },
    "switch": {
        "auto_update": {
            "name": "Auto Update",
            "icon": "mdi:update",
        },
        "use_feels_like": {
            "name": "Use Feels Like Temperature",
            "icon": "mdi:thermometer-lines",
        },
    },
    "select": {
        "comfort_class": {
            "name": "Comfort Class",
            "options": ["class_1", "class_2", "class_3"],
            "icon": "mdi:comfort",
        },
    },
    "sensor": {
        "comfort_temperature": {
            "name": "Comfort Temperature",
            "unit": "°C",
            "icon": "mdi:thermometer-check",
            "device_class": "temperature",
        },
        "comfort_range_min": {
            "name": "Comfort Range Min",
            "unit": "°C", 
            "icon": "mdi:thermometer-minus",
            "device_class": "temperature",
        },
        "comfort_range_max": {
            "name": "Comfort Range Max",
            "unit": "°C",
            "icon": "mdi:thermometer-plus", 
            "device_class": "temperature",
        },
    },
}


class BaseBridgeEntity(Entity):
    """Base class for bridge entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        attribute_name: str,
        entity_config: dict[str, Any],
    ) -> None:
        """Initialize the bridge entity."""
        self.hass = hass
        self._config_entry = config_entry
        self._attribute_name = attribute_name
        self._entity_config = entity_config
        
        # Construct entity_id to match binary_sensor format
        device_name = config_entry.data.get('name', 'adaptive_climate').lower().replace(' ', '_')
        self._binary_sensor_entity_id = f"binary_sensor.{device_name}_ashrae_compliance"

    @property
    def unique_id(self) -> str:
        """Return unique ID for the entity."""
        return f"{self._config_entry.entry_id}_{self._attribute_name}_bridge"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._entity_config.get("name", self._attribute_name.replace("_", " ").title())

    @property
    def icon(self) -> str | None:
        """Return the icon for the entity."""
        return self._entity_config.get("icon")

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    def _get_binary_sensor_state(self):
        """Get the current state of the binary sensor."""
        return self.hass.states.get(self._binary_sensor_entity_id)

    def _get_attribute_value(self):
        """Get the current value of the attribute from the binary sensor."""
        state = self._get_binary_sensor_state()
        if state and state.attributes:
            return state.attributes.get(self._attribute_name)
        return None

    async def _update_binary_sensor_attribute(self, new_value: Any) -> None:
        """Update the binary sensor attribute with a new value."""
        state = self._get_binary_sensor_state()
        if not state:
            _LOGGER.warning(
                "Binary sensor %s not found, cannot update attribute %s",
                self._binary_sensor_entity_id,
                self._attribute_name,
            )
            return

        # Get current attributes and update the specific one
        attributes = dict(state.attributes)
        attributes[self._attribute_name] = new_value

        # Update the binary sensor state with new attributes
        self.hass.states.async_set(
            self._binary_sensor_entity_id,
            state.state,
            attributes,
        )
        
        # Schedule an update for this entity
        self.async_schedule_update_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        
        # Listen for changes to the binary sensor
        self.async_on_remove(
            self.hass.bus.async_listen(
                "state_changed",
                self._handle_binary_sensor_change,
            )
        )

    async def _handle_binary_sensor_change(self, event) -> None:
        """Handle changes to the binary sensor."""
        if event.data.get("entity_id") == self._binary_sensor_entity_id:
            self.async_schedule_update_ha_state()


class NumberBridgeEntity(BaseBridgeEntity, NumberEntity):
    """Number entity that bridges to binary sensor attributes."""

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
        """Return the current value."""
        value = self._get_attribute_value()
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self._update_binary_sensor_attribute(value)


class SwitchBridgeEntity(BaseBridgeEntity, SwitchEntity):
    """Switch entity that bridges to binary sensor attributes."""

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        value = self._get_attribute_value()
        if value is not None:
            return bool(value)
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._update_binary_sensor_attribute(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._update_binary_sensor_attribute(False)


class SelectBridgeEntity(BaseBridgeEntity, SelectEntity):
    """Select entity that bridges to binary sensor attributes."""

    @property
    def options(self) -> list[str]:
        """Return the list of available options."""
        return self._entity_config.get("options", [])

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        value = self._get_attribute_value()
        if value is not None and str(value) in self.options:
            return str(value)
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option in self.options:
            await self._update_binary_sensor_attribute(option)


class SensorBridgeEntity(BaseBridgeEntity, SensorEntity):
    """Sensor entity that bridges to binary sensor attributes (read-only)."""

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
        return self._get_attribute_value()


def create_bridge_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    platform: str,
) -> list[Entity]:
    """Create bridge entities for the specified platform."""
    entities = []
    
    if platform not in BRIDGE_ENTITY_CONFIG:
        return entities
    
    platform_config = BRIDGE_ENTITY_CONFIG[platform]
    
    for attribute_name, entity_config in platform_config.items():
        if platform == "number":
            entity = NumberBridgeEntity(hass, config_entry, attribute_name, entity_config)
        elif platform == "switch":
            entity = SwitchBridgeEntity(hass, config_entry, attribute_name, entity_config)
        elif platform == "select":
            entity = SelectBridgeEntity(hass, config_entry, attribute_name, entity_config)
        elif platform == "sensor":
            entity = SensorBridgeEntity(hass, config_entry, attribute_name, entity_config)
        else:
            continue
            
        entities.append(entity)
    
    return entities
