"""Advanced configuration utilities for Adaptive Climate."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry, entity_registry, device_registry

_LOGGER = logging.getLogger(__name__)

# Set to debug level for easier troubleshooting
_LOGGER.setLevel(logging.DEBUG)


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
        
    def dump_entity_registry_assignments(self) -> dict[str, Any]:
        """Dump entity registry assignments for debugging.
        
        Returns:
            A dictionary with debug info about entity registry assignments.
        """
        result = {
            "entity_count": 0,
            "entities_with_area": 0,
            "entities_without_area": 0,
            "area_stats": {},
            "domain_stats": {},
            "areas_without_entities": [],
            "domains_without_areas": {},
            "climate_entities": [],
            "temperature_sensors": [],
            "humidity_sensors": []
        }
        
        # Get statistics about entities and areas
        for entity in self._entity_registry.entities.values():
            if entity.disabled:
                continue
                
            result["entity_count"] += 1
            domain = entity.domain
            
            # Count by domain
            result["domain_stats"][domain] = result["domain_stats"].get(domain, 0) + 1
            
            # Check if entity has an area
            if entity.area_id:
                result["entities_with_area"] += 1
                
                # Get area name
                area = self._area_registry.async_get_area(entity.area_id)
                area_name = area.name if area else "Unknown Area"
                
                # Count by area
                if area_name not in result["area_stats"]:
                    result["area_stats"][area_name] = {
                        "total": 0,
                        "domains": {}
                    }
                
                result["area_stats"][area_name]["total"] += 1
                
                if domain not in result["area_stats"][area_name]["domains"]:
                    result["area_stats"][area_name]["domains"][domain] = 0
                    
                result["area_stats"][area_name]["domains"][domain] += 1
                
                # Track climate entities
                if domain == "climate":
                    result["climate_entities"].append({
                        "entity_id": entity.entity_id,
                        "area_name": area_name,
                        "area_id": entity.area_id
                    })
                
                # Track sensor entities and categorize them
                if domain == "sensor":
                    state = self.hass.states.get(entity.entity_id)
                    if state:
                        unit = state.attributes.get("unit_of_measurement")
                        device_class = state.attributes.get("device_class")
                        
                        # Check for temperature sensors
                        if unit in ["°C", "°F"] or device_class == "temperature":
                            result["temperature_sensors"].append({
                                "entity_id": entity.entity_id,
                                "area_name": area_name,
                                "area_id": entity.area_id,
                                "unit": unit,
                                "device_class": device_class
                            })
                        
                        # Check for humidity sensors
                        elif unit == "%" or device_class == "humidity":
                            result["humidity_sensors"].append({
                                "entity_id": entity.entity_id,
                                "area_name": area_name,
                                "area_id": entity.area_id,
                                "unit": unit,
                                "device_class": device_class
                            })
            else:
                result["entities_without_area"] += 1
                
                # Track domains without areas
                if domain not in result["domains_without_areas"]:
                    result["domains_without_areas"][domain] = 0
                    
                result["domains_without_areas"][domain] += 1
                
                # Check if it's a relevant entity that should have an area
                if domain == "climate":
                    result["climate_entities"].append({
                        "entity_id": entity.entity_id,
                        "area_name": "No Area",
                        "area_id": None
                    })
                
                # Check for temperature/humidity sensors without area
                if domain == "sensor":
                    state = self.hass.states.get(entity.entity_id)
                    if state:
                        unit = state.attributes.get("unit_of_measurement")
                        device_class = state.attributes.get("device_class")
                        
                        if unit in ["°C", "°F"] or device_class == "temperature":
                            result["temperature_sensors"].append({
                                "entity_id": entity.entity_id,
                                "area_name": "No Area",
                                "area_id": None,
                                "unit": unit,
                                "device_class": device_class
                            })
                        
                        elif unit == "%" or device_class == "humidity":
                            result["humidity_sensors"].append({
                                "entity_id": entity.entity_id,
                                "area_name": "No Area",
                                "area_id": None,
                                "unit": unit,
                                "device_class": device_class
                            })
        
        # Find areas without entities
        for area_id, area in self._area_registry.areas.items():
            area_has_entities = False
            for entity in self._entity_registry.entities.values():
                if entity.area_id == area_id and not entity.disabled:
                    area_has_entities = True
                    break
            
            if not area_has_entities:
                result["areas_without_entities"].append(area.name)
        
        return result

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

    def get_entities_by_type_in_area(self, area_id: str) -> dict[str, list[str]]:
        """Get entities in an area grouped by domain type.
        
        Args:
            area_id: The area ID to filter entities by.
            
        Returns:
            A dictionary with entity types as keys and lists of entity IDs as values.
        """
        _LOGGER.debug("Getting entities in area %s", area_id)
        
        # Initialize result dictionary with empty lists
        result = {
            "climate": [],
            "sensor": [],
            "binary_sensor": [],
            "switch": [],
            "light": [],
            "media_player": [],
            "weather": [],
            "other": [],
            "temperature_sensors": [],
            "humidity_sensors": [],
            "other_sensors": [],
            "occupancy_sensors": [],
            "other_binary_sensors": [],
        }
        
        # Verificar se a área existe
        area = self._area_registry.async_get_area(area_id)
        if not area:
            _LOGGER.warning("Area with ID %s not found", area_id)
            return result
        
        _LOGGER.debug("Finding entities for area: %s (ID: %s)", area.name, area_id)
        
        # Verificar todas as entidades registradas em cada área para diagnóstico
        area_entity_count = {}
        for entity in self._entity_registry.entities.values():
            if not entity.disabled and entity.area_id:
                area_entity_count[entity.area_id] = area_entity_count.get(entity.area_id, 0) + 1
        
        _LOGGER.debug("Area entity counts: %s", 
                     {a_id: count for a_id, count in area_entity_count.items()})
        
        # Verificar se há áreas vazias (sem entidades)
        empty_areas = []
        for a_id, area_obj in self._area_registry.areas.items():
            if a_id not in area_entity_count or area_entity_count[a_id] == 0:
                empty_areas.append(area_obj.name)
        
        if empty_areas:
            _LOGGER.warning("Found areas with no entities assigned: %s", empty_areas)
        
        # Count entities by domain for debugging
        domain_counts = {}
        for entity in self._entity_registry.entities.values():
            if entity.disabled:
                continue
                
            domain = entity.domain
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        _LOGGER.debug("Entities by domain: %s", domain_counts)
        
        # Count entities by area for debugging
        area_counts = {}
        for entity in self._entity_registry.entities.values():
            entity_area = entity.area_id
            if entity_area:
                area_counts[entity_area] = area_counts.get(entity_area, 0) + 1
        
        _LOGGER.debug("Entities by area: %s", area_counts)
        _LOGGER.debug("Looking for entities in area ID: %s", area_id)
        
        # Get all entities in the area
        area_entities = []
        for entity in self._entity_registry.entities.values():
            if entity.disabled:
                continue
                
            if entity.area_id == area_id:
                area_entities.append(entity.entity_id)
                
                # Group by domain
                domain = entity.domain
                if domain in result:
                    result[domain].append(entity.entity_id)
                else:
                    result["other"].append(entity.entity_id)
        
        _LOGGER.debug("Found %d entities in area %s: %s", 
                     len(area_entities), area.name, area_entities)
        
        # Depuração: verificar quantas entidades foram encontradas para cada categoria
        for domain, entities in result.items():
            _LOGGER.debug("Found %d entities of type %s: %s", 
                        len(entities), domain, entities)
                
        # Get additional information for sensors to further categorize them
        temp_sensors = []
        humidity_sensors = []
        other_sensors = []
        
        for entity_id in result["sensor"]:
            state = self.hass.states.get(entity_id)
            if not state:
                _LOGGER.debug("No state found for entity %s", entity_id)
                other_sensors.append(entity_id)
                continue
                
            # Check for temperature sensors
            if (state.attributes.get("unit_of_measurement") in ["°C", "°F"] or 
                    state.attributes.get("device_class") == "temperature"):
                temp_sensors.append(entity_id)
                _LOGGER.debug("Found temperature sensor: %s with attributes %s", 
                             entity_id, state.attributes)
            # Check for humidity sensors
            elif (state.attributes.get("unit_of_measurement") == "%" or 
                  state.attributes.get("device_class") == "humidity"):
                humidity_sensors.append(entity_id)
                _LOGGER.debug("Found humidity sensor: %s with attributes %s", 
                             entity_id, state.attributes)
            else:
                other_sensors.append(entity_id)
                
        # Check for binary sensors related to occupancy
        occupancy_sensors = []
        other_binary_sensors = []
        
        for entity_id in result["binary_sensor"]:
            state = self.hass.states.get(entity_id)
            if not state:
                other_binary_sensors.append(entity_id)
                continue
                
            if state.attributes.get("device_class") in ["motion", "occupancy", "presence"]:
                occupancy_sensors.append(entity_id)
                _LOGGER.debug("Found occupancy sensor: %s with attributes %s", 
                             entity_id, state.attributes)
            else:
                other_binary_sensors.append(entity_id)
                
        # Add additional categories to the result
        result["temperature_sensors"] = temp_sensors
        result["humidity_sensors"] = humidity_sensors
        result["other_sensors"] = other_sensors
        result["occupancy_sensors"] = occupancy_sensors
        result["other_binary_sensors"] = other_binary_sensors
        
        _LOGGER.debug("Final categorized entities: %s", result)
        
        return result

    def diagnose_area_entity_issues(self) -> dict[str, Any]:
        """Diagnostica problemas relacionados à atribuição de entidades em áreas.
        
        Returns:
            Um dicionário com informações de diagnóstico.
        """
        issues = {}
        
        # Verificar áreas sem entidades
        area_entity_count = {}
        for entity in self._entity_registry.entities.values():
            if not entity.disabled and entity.area_id:
                area_entity_count[entity.area_id] = area_entity_count.get(entity.area_id, 0) + 1
        
        empty_areas = []
        for a_id, area in self._area_registry.areas.items():
            if a_id not in area_entity_count:
                empty_areas.append(area.name)
        
        if empty_areas:
            issues["empty_areas"] = empty_areas
            _LOGGER.warning("Áreas sem entidades atribuídas: %s", empty_areas)
        
        # Verificar entidades de clima sem área atribuída
        climate_without_area = []
        for entity in self._entity_registry.entities.values():
            if entity.domain == "climate" and not entity.disabled and not entity.area_id:
                climate_without_area.append(entity.entity_id)
        
        if climate_without_area:
            issues["climate_without_area"] = climate_without_area
            _LOGGER.warning("Entidades de clima sem área atribuída: %s", climate_without_area)
        
        # Verificar sensores sem área atribuída
        sensors_without_area = []
        for entity in self._entity_registry.entities.values():
            if entity.domain == "sensor" and not entity.disabled and not entity.area_id:
                state = self.hass.states.get(entity.entity_id)
                if state and (
                    state.attributes.get("device_class") in ["temperature", "humidity"] or
                    state.attributes.get("unit_of_measurement") in ["°C", "°F", "%"]
                ):
                    sensors_without_area.append(entity.entity_id)
        
        if sensors_without_area:
            issues["sensors_without_area"] = sensors_without_area
            _LOGGER.warning("Sensores relevantes sem área atribuída: %s", sensors_without_area)
        
        # Verificar sensores binários sem área atribuída
        binary_sensors_without_area = []
        for entity in self._entity_registry.entities.values():
            if entity.domain == "binary_sensor" and not entity.disabled and not entity.area_id:
                state = self.hass.states.get(entity.entity_id)
                if state and state.attributes.get("device_class") in ["motion", "occupancy", "presence"]:
                    binary_sensors_without_area.append(entity.entity_id)
        
        if binary_sensors_without_area:
            issues["binary_sensors_without_area"] = binary_sensors_without_area
            _LOGGER.warning("Sensores binários relevantes sem área atribuída: %s", binary_sensors_without_area)
        
        return issues


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


def get_entities_by_area_and_domain(hass: HomeAssistant, area_name_or_id: str, domains: list[str] = None) -> list[str]:
    """Get entities filtered by area and domain.
    
    This function can be used in templates with the template.area_domain_entities custom template function.
    
    Args:
        hass: The Home Assistant instance.
        area_name_or_id: The name or ID of the area to filter entities by.
        domains: Optional list of domains to filter entities by (e.g., ["climate", "sensor"]).
        
    Returns:
        A list of entity_ids in the specified area, optionally filtered by domain.
    """
    _LOGGER.debug("Finding entities in area %s with domains %s", area_name_or_id, domains)
    area_reg = area_registry.async_get(hass)
    
    # If an area name is provided, try to find the corresponding area ID
    area_id = area_name_or_id
    if area_name_or_id and not area_name_or_id.startswith(("area_", "0123456789abcdef")):
        for a_id, area in area_reg.areas.items():
            if area.name.lower() == area_name_or_id.lower():
                area_id = a_id
                break
    
    if not area_id:
        _LOGGER.warning("Area with name or ID %s not found", area_name_or_id)
        return []
    
    ent_reg = entity_registry.async_get(hass)
    entities = []
    
    for entity in ent_reg.entities.values():
        if entity.disabled:
            continue
            
        if entity.area_id == area_id:
            if domains and entity.domain not in domains:
                continue
                
            entities.append(entity.entity_id)
    
    _LOGGER.debug("Found %d entities in area %s with domains %s: %s", 
                 len(entities), area_name_or_id, domains, entities)
    
    return entities
