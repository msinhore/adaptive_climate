"""Template helpers for Adaptive Climate."""
from __future__ import annotations

import logging
from typing import Any, Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import template

from .area_helper import get_entities_by_area_and_domain

_LOGGER = logging.getLogger(__name__)


@callback
def async_register_template_functions(hass: HomeAssistant) -> None:
    """Register custom template functions for Adaptive Climate."""
    template.attach_function_to_template(
        hass, 
        "area_domain_entities", 
        _area_domain_entities_function(hass)
    )


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
