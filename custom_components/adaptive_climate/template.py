"""Template helpers for Adaptive Climate."""
from __future__ import annotations

import logging
from typing import Any, Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import template, area_registry, entity_registry

from .area_helper import get_entities_by_area_and_domain

_LOGGER = logging.getLogger(__name__)


@callback
def async_register_template_functions(hass: HomeAssistant) -> None:
    """Register custom template functions for Adaptive Climate."""
    try:
        # Get the function references ready
        area_domain_entities_func = _area_domain_entities_function(hass)
        check_area_entities_func = _check_area_entities_function(hass)
        
        # Method 1: Modern HA 2023.9+ approach using HomeAssistant.components.template.template
        if hasattr(hass, "components") and hasattr(hass.components, "template"):
            if hasattr(hass.components.template, "Template") and hasattr(hass.components.template.Template, "register_template_functions"):
                hass.components.template.Template.register_template_functions({
                    "area_domain_entities": area_domain_entities_func,
                    "check_area_entities": check_area_entities_func,
                })
                _LOGGER.debug("Registered custom template functions using hass.components.template.Template.register_template_functions")
                return
                
        # Method 2: Direct access to template module
        if hasattr(template, "Template") and hasattr(template.Template, "register_template_functions"):
            template.Template.register_template_functions({
                "area_domain_entities": area_domain_entities_func,
                "check_area_entities": check_area_entities_func,
            })
            _LOGGER.debug("Registered custom template functions using template.Template.register_template_functions")
            return
            
        # Method 3: Direct access to template environment globals (modern approach)
        if "template.environment" in hass.data and hasattr(hass.data["template.environment"], "globals"):
            hass.data["template.environment"].globals["area_domain_entities"] = area_domain_entities_func
            hass.data["template.environment"].globals["check_area_entities"] = check_area_entities_func
            _LOGGER.debug("Registered custom template functions directly to template environment globals")
            return
            
        # Method 4 (Very Legacy): Not recommended but included as final fallback
        if hasattr(template, "attach_function_to_template"):
            template.attach_function_to_template(hass, "area_domain_entities", area_domain_entities_func)
            template.attach_function_to_template(hass, "check_area_entities", check_area_entities_func)
            _LOGGER.debug("Registered custom template functions using legacy attach_function_to_template")
            return
            
        _LOGGER.warning("Could not register template functions through any known method. Template functions may not be available.")
    except Exception as err:
        _LOGGER.error("Error registering custom template functions: %s", err)


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
        
        return get_entities_by_area_and_domain(
            hass, area_name_or_id, domain_list
        )
    
    return area_domain_entities


def _check_area_entities_function(hass: HomeAssistant) -> Callable:
    """Criar uma função para verificar problemas de entidades em áreas para templates."""
    
    def check_area_entities(area_name_or_id: str) -> dict[str, Any]:
        """Verificar entidades em uma área específica e retornar informações de diagnóstico.
        
        Args:
            area_name_or_id: Nome ou ID da área para verificar.
            
        Returns:
            Um dicionário com informações sobre entidades na área e possíveis problemas.
            
        Exemplo:
            {{ check_area_entities('Living Room') }}
        """
        if not area_name_or_id:
            return {"error": "É necessário fornecer um nome ou ID de área"}
        
        area_reg = area_registry.async_get(hass)
        ent_reg = entity_registry.async_get(hass)
        
        # Encontrar área por nome ou ID
        area = None
        area_id = area_name_or_id
        
        # Se não for um ID, procurar pelo nome
        if not area_name_or_id.startswith(("area_", "0123456789abcdef")):
            for a_id, a in area_reg.areas.items():
                if a.name.lower() == area_name_or_id.lower():
                    area = a
                    area_id = a_id
                    break
        else:
            area = area_reg.async_get_area(area_id)
            
        if not area:
            return {"error": f"Área '{area_name_or_id}' não encontrada"}
            
        # Contar entidades por domínio
        domain_counts = {}
        entities = []
        
        for entity in ent_reg.entities.values():
            if entity.disabled:
                continue
                
            if entity.area_id == area_id:
                domain = entity.domain
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
                entities.append(entity.entity_id)
        
        # Verificar se há entidades de clima na área
        climate_entities = [e for e in entities if e.startswith("climate.")]
        sensor_entities = [e for e in entities if e.startswith("sensor.")]
        binary_sensor_entities = [e for e in entities if e.startswith("binary_sensor.")]
        
        # Verificar se há sensores de temperatura e umidade
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
