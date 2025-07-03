"""Advanced configuration utilities for Adaptive Climate."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry, entity_registry, device_registry

_LOGGER = logging.getLogger(__name__)


class AreaBasedConfigHelper:
    """Helper class for area-based configuration."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the helper."""
        self.hass = hass
        self._area_registry = area_registry.async_get(hass)
        self._entity_registry = entity_registry.async_get(hass)
        self._device_registry = device_registry.async_get(hass)

    def get_areas_with_climate_entities(self) -> list[dict[str, Any]]:
        """Get all areas that have climate entities."""
        areas_with_climate = []
        
        for area in self._area_registry.areas.values():
            climate_entities = self.get_climate_entities_in_area(area.id)
            if climate_entities:
                areas_with_climate.append({
                    "area_id": area.id,
                    "area_name": area.name,
                    "climate_entities": climate_entities,
                    "suggested_sensors": self._get_suggested_sensors_for_area(area.id),
                })
        
        return areas_with_climate

    def get_climate_entities_in_area(self, area_id: str) -> list[str]:
        """Get all climate entities in a specific area."""
        climate_entities = []
        
        for entity in self._entity_registry.entities.values():
            if (
                entity.domain == "climate"
                and entity.area_id == area_id
                and not entity.disabled
            ):
                climate_entities.append(entity.entity_id)
        
        return climate_entities

    def _get_suggested_sensors_for_area(self, area_id: str) -> dict[str, list[str]]:
        """Get suggested sensors for an area."""
        suggestions = {
            "temperature_sensors": [],
            "humidity_sensors": [],
            "occupancy_sensors": [],
        }
        
        for entity in self._entity_registry.entities.values():
            if entity.area_id != area_id or entity.disabled:
                continue
            
            # Temperature sensors
            if entity.domain == "sensor":
                state = self.hass.states.get(entity.entity_id)
                if state and state.attributes.get("unit_of_measurement") in ["°C", "°F"]:
                    suggestions["temperature_sensors"].append(entity.entity_id)
                elif state and state.attributes.get("device_class") == "temperature":
                    suggestions["temperature_sensors"].append(entity.entity_id)
                elif state and state.attributes.get("unit_of_measurement") == "%":
                    suggestions["humidity_sensors"].append(entity.entity_id)
                elif state and state.attributes.get("device_class") == "humidity":
                    suggestions["humidity_sensors"].append(entity.entity_id)
            
            # Occupancy sensors
            elif entity.domain == "binary_sensor":
                state = self.hass.states.get(entity.entity_id)
                if state and state.attributes.get("device_class") in ["motion", "occupancy", "presence"]:
                    suggestions["occupancy_sensors"].append(entity.entity_id)
        
        return suggestions

    def generate_bulk_config_suggestions(self) -> list[dict[str, Any]]:
        """Generate bulk configuration suggestions for multiple areas."""
        suggestions = []
        
        for area_data in self.get_areas_with_climate_entities():
            area_id = area_data["area_id"]
            area_name = area_data["area_name"]
            climate_entities = area_data["climate_entities"]
            sensors = area_data["suggested_sensors"]
            
            for climate_entity in climate_entities:
                # Try to find the best indoor temperature sensor
                indoor_temp_sensor = None
                if sensors["temperature_sensors"]:
                    # Prefer sensors with "indoor", "room", or area name in the name
                    for sensor in sensors["temperature_sensors"]:
                        sensor_name = sensor.lower()
                        if any(keyword in sensor_name for keyword in ["indoor", "room", area_name.lower()]):
                            indoor_temp_sensor = sensor
                            break
                    
                    # Fallback to first available sensor
                    if not indoor_temp_sensor:
                        indoor_temp_sensor = sensors["temperature_sensors"][0]
                
                # Suggest outdoor temperature sensor (typically weather entity)
                outdoor_temp_sensor = "weather.home"  # Common default
                weather_entities = [
                    entity.entity_id for entity in self._entity_registry.entities.values()
                    if entity.domain == "weather" and not entity.disabled
                ]
                if weather_entities:
                    outdoor_temp_sensor = weather_entities[0]
                
                # Build suggestion
                suggestion = {
                    "name": f"Adaptive Climate - {area_name}",
                    "area": area_id,
                    "climate_entity": climate_entity,
                    "indoor_temp_sensor": indoor_temp_sensor,
                    "outdoor_temp_sensor": outdoor_temp_sensor,
                    "comfort_category": "II",  # Default to residential
                }
                
                # Add optional sensors if available
                if sensors["occupancy_sensors"]:
                    suggestion["occupancy_sensor"] = sensors["occupancy_sensors"][0]
                    suggestion["use_occupancy_features"] = True
                
                if sensors["humidity_sensors"]:
                    suggestion["indoor_humidity_sensor"] = sensors["humidity_sensors"][0]
                    suggestion["humidity_comfort_enable"] = True
                
                suggestions.append(suggestion)
        
        return suggestions

    def validate_area_config(self, area_id: str, config: dict[str, Any]) -> dict[str, str]:
        """Validate configuration for a specific area."""
        errors = {}
        
        # Check if area exists
        if area_id not in self._area_registry.areas:
            errors["area"] = "area_not_found"
        
        # Check if entities are in the correct area
        for field, entity_id in config.items():
            if field.endswith("_entity") or field.endswith("_sensor"):
                if entity_id and entity_id in self._entity_registry.entities:
                    entity = self._entity_registry.entities[entity_id]
                    if entity.area_id != area_id and field != "outdoor_temp_sensor":
                        errors[field] = "entity_not_in_area"
        
        return errors

    def get_entities_in_area(self, area_id: str, domain_filter: list[str] = None) -> list[str]:
        """Get all entities in a specific area with optional domain filtering.
        
        Args:
            area_id: The area ID to filter entities by.
            domain_filter: Optional list of domains to filter entities by.
            
        Returns:
            A list of entity IDs in the specified area, optionally filtered by domain.
        """
        entities = []
        
        for entity in self._entity_registry.entities.values():
            # Skip disabled entities
            if entity.disabled:
                continue
                
            # Check if entity is in the specified area
            if entity.area_id == area_id:
                # Apply domain filter if provided
                if domain_filter and entity.domain not in domain_filter:
                    continue
                    
                entities.append(entity.entity_id)
        
        return entities


def get_area_name(hass: HomeAssistant, area_id: str | None) -> str:
    """Get area name from area ID."""
    if not area_id:
        return "Unknown Area"
    
    area_reg = area_registry.async_get(hass)
    area = area_reg.async_get_area(area_id)
    return area.name if area else "Unknown Area"


def suggest_entity_name_for_area(area_name: str, entity_type: str) -> str:
    """Suggest an entity name based on area and type."""
    clean_area_name = area_name.replace(" ", "_").lower()
    return f"adaptive_climate_{clean_area_name}_{entity_type}"
