"""Template helpers for Adaptive Climate."""
from __future__ import annotations

import logging
from typing import Any, Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import template, area_registry, entity_registry
from .template_helpers import safe_state, safe_states_list

_LOGGER = logging.getLogger(__name__)


@callback
def async_register_template_functions(hass: HomeAssistant) -> None:
    """Register custom template functions for Adaptive Climate."""
    try:
        # Get the function references ready
        area_domain_entities_func = _area_domain_entities_function(hass)
        check_area_entities_func = _check_area_entities_function(hass)
        safe_name_func = _safe_name_function()
        
        # Create a dictionary of functions to register
        template_functions = {
            "area_domain_entities": area_domain_entities_func,
            "check_area_entities": check_area_entities_func,
            "safe_name": safe_name_func,
            "safe_state": safe_state,
            "safe_states": safe_states_list,
        }
        
        # Simplified registration approach using known stable methods
        success = False
        
        # Method 1: Try direct access to template environment globals
        try:
            if "template.environment" in hass.data and hasattr(hass.data["template.environment"], "globals"):
                env_globals = hass.data["template.environment"].globals
                for name, func in template_functions.items():
                    env_globals[name] = func
                _LOGGER.debug("Registered custom template functions using template environment globals")
                success = True
        except Exception as err:
            _LOGGER.debug("Could not register via template environment: %s", err)
        
        # Method 2: Legacy method if the first approach failed
        if not success and hasattr(template, "attach_function_to_template"):
            try:
                for name, func in template_functions.items():
                    template.attach_function_to_template(hass, name, func)
                _LOGGER.debug("Registered custom template functions using legacy attach_function_to_template")
                success = True
            except Exception as err:
                _LOGGER.debug("Could not register via attach_function_to_template: %s", err)
        
        if not success:
            _LOGGER.warning("Could not register template functions through any known method. Template functions may not be available.")
    except Exception as err:
        _LOGGER.error("Error registering custom template functions: %s", err)


def _safe_name_function() -> Callable:
    """Create a function to safely get entity or dictionary name."""
    
    def safe_name(obj: Any) -> str:
        """Safely get the name of an entity or dictionary.
        
        Args:
            obj: The object to get the name from. Can be a dictionary, ReadOnlyDict, or any object.
            
        Returns:
            The name as a string, or a fallback value if no name is available.
            
        Examples:
            {{ safe_name(this) }}
        """
        try:
            # Try direct attribute access first
            if hasattr(obj, "name"):
                return obj.name
            
            # Try dictionary access
            if hasattr(obj, "get"):
                name = obj.get("name")
                if name:
                    return name
            
            # Try __getitem__ access
            try:
                return obj["name"]
            except (KeyError, TypeError):
                pass
                
            # If all else fails, try to convert to string
            return str(obj)
        except Exception:
            return "Unknown"
    
    return safe_name


def _area_domain_entities_function(hass: HomeAssistant) -> Callable:
    """Create a function to get entities by area and domain for templates."""
    
    def area_domain_entities(area_name_or_id: str, domains: list[str] = None) -> list[str]:
        """Get entities filtered by area and domain.
        
        Args:
            area_name_or_id: The name or ID of the area to filter entities by.
            domains: Optional domain or list of domains to filter entities by.
                    Can be a string (single domain) or list of strings.
            
        Returns:
            A list of entity_ids in the specified area, optionally filtered by domain.
            
        Examples:
            {{ area_domain_entities('Living Room', 'climate') }}
            {{ area_domain_entities('Living Room', ['sensor', 'binary_sensor']) }}
        """
        if not area_name_or_id:
            raise TemplateError("area_name_or_id is required")
        
        # Handle single domain as string
        domain_list = None
        if domains:
            if isinstance(domains, str):
                domain_list = [domains]
            else:
                domain_list = list(domains)
        
        # Inline implementation of get_entities_by_area_and_domain
        area_reg = area_registry.async_get(hass)
        
        # Find area by name or ID
        area_id = area_name_or_id
        if area_name_or_id and not area_name_or_id.startswith(("area_", "0123456789abcdef")):
            for a_id, area in area_reg.areas.items():
                if area.name.lower() == area_name_or_id.lower():
                    area_id = a_id
                    break
        
        if not area_id:
            return []
        
        ent_reg = entity_registry.async_get(hass)
        entities = []
        
        for entity in ent_reg.entities.values():
            if entity.disabled:
                continue
                
            if entity.area_id == area_id:
                if domain_list and entity.domain not in domain_list:
                    continue
                    
                entities.append(entity.entity_id)
        
        return entities
    
    return area_domain_entities


def _check_area_entities_function(hass: HomeAssistant) -> Callable:
    """Create a function to check area entity problems for templates."""
    
    def check_area_entities(area_name_or_id: str) -> dict[str, Any]:
        """Check entities in a specific area and return diagnostic information.
        
        Args:
            area_name_or_id: Name or ID of the area to check.
            
        Returns:
            A dictionary with information about entities in the area and possible issues.
            
        Example:
            {{ check_area_entities('Living Room') }}
        """
        if not area_name_or_id:
            return {"error": "Area name or ID is required"}
        
        area_reg = area_registry.async_get(hass)
        ent_reg = entity_registry.async_get(hass)
        
        # Find area by name or ID
        area = None
        area_id = area_name_or_id
        
        # If not an ID, search by name
        if not area_name_or_id.startswith(("area_", "0123456789abcdef")):
            for a_id, a in area_reg.areas.items():
                if a.name.lower() == area_name_or_id.lower():
                    area = a
                    area_id = a_id
                    break
        else:
            area = area_reg.async_get_area(area_id)
            
        if not area:
            return {"error": f"Area '{area_name_or_id}' not found"}
            
        # Count entities by domain
        domain_counts = {}
        entities = []
        
        for entity in ent_reg.entities.values():
            if entity.disabled:
                continue
                
            if entity.area_id == area_id:
                domain = entity.domain
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
                entities.append(entity.entity_id)
        
        # Check if there are climate entities in the area
        climate_entities = [e for e in entities if e.startswith("climate.")]
        sensor_entities = [e for e in entities if e.startswith("sensor.")]
        binary_sensor_entities = [e for e in entities if e.startswith("binary_sensor.")]
        
        # Check if there are temperature and humidity sensors
        temp_sensors = []
        humidity_sensors = []
        motion_sensors = []
        
        for entity_id in sensor_entities:
            state = hass.states.get(entity_id)
            if not state:
                continue
                
            if (state.attributes.get("unit_of_measurement") in ["°C", "°F"] or 
                    state.attributes.get("device_class") == "temperature"):
                temp_sensors.append(entity_id)
            elif (state.attributes.get("unit_of_measurement") == "%" or 
                  state.attributes.get("device_class") == "humidity"):
                humidity_sensors.append(entity_id)
        
        for entity_id in binary_sensor_entities:
            state = hass.states.get(entity_id)
            if not state:
                continue
                
            if state.attributes.get("device_class") in ["motion", "occupancy", "presence"]:
                motion_sensors.append(entity_id)
                
        return {
            "area_name": area.name,
            "area_id": area_id,
            "total_entities": len(entities),
            "domain_counts": domain_counts,
            "entities": entities,
            "climate_entities": climate_entities,
            "temperature_sensors": temp_sensors,
            "humidity_sensors": humidity_sensors,
            "motion_sensors": motion_sensors,
            "has_climate": len(climate_entities) > 0,
            "has_temperature_sensors": len(temp_sensors) > 0,
            "has_humidity_sensors": len(humidity_sensors) > 0,
            "has_motion_sensors": len(motion_sensors) > 0
        }
    
    return check_area_entities
