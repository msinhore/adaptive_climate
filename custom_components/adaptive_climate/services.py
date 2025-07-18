"""Services for Adaptive Climate integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import (
    DOMAIN,
    DEFAULT_MIN_COMFORT_TEMP,
    DEFAULT_MAX_COMFORT_TEMP,
    DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
    DEFAULT_COMFORT_CATEGORY,
    DEFAULT_OVERRIDE_TEMPERATURE,
)
from .coordinator import AdaptiveClimateCoordinator

_LOGGER = logging.getLogger(__name__)

# Service names
SERVICE_SET_PARAMETER = "set_parameter"
SERVICE_RESET_PARAMETER = "reset_parameter"

# Parameter definitions with validation
EDITABLE_PARAMETERS = {
    # Temperature parameters (float, 18-30°C range)
    "min_comfort_temp": {
        "type": float,
        "min": 18.0,
        "max": 30.0,
        "default": DEFAULT_MIN_COMFORT_TEMP,
        "unit": "°C",
        "description": "Minimum comfort temperature limit"
    },
    "max_comfort_temp": {
        "type": float,
        "min": 18.0,
        "max": 30.0,
        "default": DEFAULT_MAX_COMFORT_TEMP,
        "unit": "°C",
        "description": "Maximum comfort temperature limit"
    },
    "temperature_change_threshold": {
        "type": float,
        "min": 0.1,
        "max": 5.0,
        "default": DEFAULT_TEMPERATURE_CHANGE_THRESHOLD,
        "unit": "°C",
        "description": "Minimum temperature change to trigger adjustment"
    },
    "override_temperature": {
        "type": float,
        "min": -2,
        "max": 2,
        "default": DEFAULT_OVERRIDE_TEMPERATURE,
        "unit": "°C",
        "description": "Override temperature for manual control"
    },
    # Category parameter
    "comfort_category": {
        "type": str,
        "options": ["I", "II"],
        "default": DEFAULT_COMFORT_CATEGORY,
        "description": "ASHRAE 55 comfort category (I=±2.5°C, II=±3.5°C)"
    },
    
    # Boolean parameters
    "energy_save_mode": {
        "type": bool,
        "default": True,
        "description": "Enable energy saving features"
    },
    "auto_mode_enable": {
        "type": bool,
        "default": True,
        "description": "Enable automatic mode for climate control"
    },
}

# Service schemas
SET_PARAMETER_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("parameter"): vol.In(EDITABLE_PARAMETERS.keys()),
        vol.Required("value"): vol.Any(str, int, float, bool),
    }
)

RESET_PARAMETER_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("parameter"): vol.In(EDITABLE_PARAMETERS.keys()),
    }
)

MANUAL_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("temperature"): vol.Coerce(float),
        vol.Optional("duration_hours", default=1): vol.Coerce(int),
    }
)

CLEAR_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
    }
)

async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Adaptive Climate."""
    
    async def async_set_parameter(call: ServiceCall) -> None:
        """Handle set_parameter service call."""
        entity_id = call.data["entity_id"]
        parameter = call.data["parameter"]
        value = call.data["value"]
        
        # Get the coordinator from the entity
        coordinator = await _get_coordinator_from_entity_id(hass, entity_id)
        if not coordinator:
            _LOGGER.error("Could not find coordinator for entity %s", entity_id)
            return
        
        # Validate parameter
        if parameter not in EDITABLE_PARAMETERS:
            _LOGGER.error("Unknown parameter: %s", parameter)
            return
        
        param_def = EDITABLE_PARAMETERS[parameter]
        
        # Type conversion and validation
        try:
            if param_def["type"] == float:
                value = float(value)
                if "min" in param_def and value < param_def["min"]:
                    raise ValueError(f"Value {value} below minimum {param_def['min']}")
                if "max" in param_def and value > param_def["max"]:
                    raise ValueError(f"Value {value} above maximum {param_def['max']}")
            elif param_def["type"] == int:
                value = int(value)
                if "min" in param_def and value < param_def["min"]:
                    raise ValueError(f"Value {value} below minimum {param_def['min']}")
                if "max" in param_def and value > param_def["max"]:
                    raise ValueError(f"Value {value} above maximum {param_def['max']}")
            elif param_def["type"] == bool:
                if isinstance(value, str):
                    value = value.lower() in ("true", "1", "on", "yes")
                else:
                    value = bool(value)
            elif param_def["type"] == str:
                value = str(value)
                if "options" in param_def and value not in param_def["options"]:
                    raise ValueError(f"Value {value} not in allowed options: {param_def['options']}")
        except (ValueError, TypeError) as err:
            _LOGGER.error("Invalid value for parameter %s: %s", parameter, err)
            return
        
        # Update configuration
        await coordinator.update_config({parameter: value})
        
        _LOGGER.info("Parameter %s updated to %s for %s", parameter, value, entity_id)
    
    async def async_reset_parameter(call: ServiceCall) -> None:
        """Handle reset_parameter service call."""
        entity_id = call.data["entity_id"]
        parameter = call.data["parameter"]
        
        coordinator = await _get_coordinator_from_entity_id(hass, entity_id)
        if not coordinator:
            _LOGGER.error("Could not find coordinator for entity %s", entity_id)
            return
        
        if parameter not in EDITABLE_PARAMETERS:
            _LOGGER.error("Unknown parameter: %s", parameter)
            return
        
        default_value = EDITABLE_PARAMETERS[parameter]["default"]
        await coordinator.update_config({parameter: default_value})
        
        _LOGGER.info("Parameter %s reset to default %s for %s", parameter, default_value, entity_id)
    
    async def async_set_manual_override(call: ServiceCall) -> None:
        """Handle manual override service call."""
        entity_id = call.data["entity_id"]
        temperature = call.data["temperature"]
        duration_hours = call.data.get("duration_hours", 1)
        
        coordinator = await _get_coordinator_from_entity_id(hass, entity_id)
        if not coordinator:
            _LOGGER.error("Could not find coordinator for entity %s", entity_id)
            return
        
        duration_seconds = duration_hours * 3600 if duration_hours > 0 else None
        await coordinator.set_manual_override(temperature, duration_seconds)
        
        _LOGGER.info("Manual override set to %.1f°C for %dh on %s", temperature, duration_hours, entity_id)
    
    async def async_clear_manual_override(call: ServiceCall) -> None:
        """Handle clear manual override service call."""
        entity_id = call.data["entity_id"]
        
        coordinator = await _get_coordinator_from_entity_id(hass, entity_id)
        if not coordinator:
            _LOGGER.error("Could not find coordinator for entity %s", entity_id)
            return
        
        await coordinator.clear_manual_override()
        
        _LOGGER.info("Manual override cleared for %s", entity_id)
    
    # Register services
    hass.services.async_register(
        DOMAIN, SERVICE_SET_PARAMETER, async_set_parameter, schema=SET_PARAMETER_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RESET_PARAMETER, async_reset_parameter, schema=RESET_PARAMETER_SCHEMA
    )
    
    _LOGGER.info("Adaptive Climate services registered")


async def _get_coordinator_from_entity_id(hass: HomeAssistant, entity_id: str) -> AdaptiveClimateCoordinator | None:
    """Get coordinator from entity ID."""
    # Extract entry_id from entity_id (format: domain.entry_id_suffix)
    parts = entity_id.split(".")
    if len(parts) != 2:
        return None
    
    entity_name = parts[1]
    
    # Find the entry_id by checking all adaptive climate entries
    for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
        if isinstance(coordinator, AdaptiveClimateCoordinator):
            # Check if this entity belongs to this coordinator
            if entity_name.startswith(entry_id):
                return coordinator
    
    return None


def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services."""
    hass.services.async_remove(DOMAIN, SERVICE_SET_PARAMETER)
    hass.services.async_remove(DOMAIN, SERVICE_RESET_PARAMETER)
 
    _LOGGER.info("Adaptive Climate services unloaded")
