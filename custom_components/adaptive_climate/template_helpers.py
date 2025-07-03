"""Additional template helpers for Adaptive Climate."""
from __future__ import annotations

import logging
from typing import Any, Optional, Union, List

from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE

_LOGGER = logging.getLogger(__name__)


def safe_state(entity) -> str:
    """Safely get the state of an entity or return a placeholder.
    
    Args:
        entity: The entity state object, can be None
        
    Returns:
        The state as a string, or 'unavailable' if the entity doesn't exist
    """
    if entity is None:
        return STATE_UNAVAILABLE
        
    try:
        return entity.state
    except AttributeError:
        return STATE_UNAVAILABLE


def safe_states_list(entities_list: List[Any]) -> List[Any]:
    """Process a list of entity state objects to handle None values.
    
    This function is useful for templates that process a list of entities
    and some of them might not exist, which would cause errors with selectattr etc.
    
    Args:
        entities_list: A list of entity state objects, some might be None
        
    Returns:
        A list of entity state objects, with None values filtered out
    """
    if not entities_list:
        return []
        
    # Filter out None values
    return [e for e in entities_list if e is not None]
