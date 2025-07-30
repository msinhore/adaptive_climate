"""Services for Adaptive Climate integration."""
from __future__ import annotations

import logging
from typing import Any, Optional

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
SERVICE_SET_MANUAL_OVERRIDE = "set_manual_override"
SERVICE_CLEAR_MANUAL_OVERRIDE = "clear_manual_override"
SERVICE_SET_COMFORT_CATEGORY = "set_comfort_category"
SERVICE_UPDATE_CALCULATIONS = "update_calculations"
SERVICE_SET_TEMPORARY_OVERRIDE = "set_temporary_override"
SERVICE_REDETECT_CAPABILITIES = "redetect_capabilities"

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

SET_COMFORT_CATEGORY_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("category"): vol.In(["I", "II"]),
    }
)

UPDATE_CALCULATIONS_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
    }
)

SET_TEMPORARY_OVERRIDE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("temperature"): vol.Coerce(float),
        vol.Optional("duration_minutes", default=30): vol.Coerce(int),
    }
)

REDETECT_CAPABILITIES_SCHEMA = vol.Schema(
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
        
        device_name = coordinator.device_name
        _LOGGER.debug(f"[{device_name}] Setting parameter: {parameter} = {value}")
        
        # Validate parameter
        if parameter not in EDITABLE_PARAMETERS:
            _LOGGER.error(f"[{device_name}] Unknown parameter: {parameter}")
            return
        
        param_def = EDITABLE_PARAMETERS[parameter]
        
        # Type conversion and validation
        try:
            validated_value = _validate_parameter_value(parameter, value, param_def)
        except ValueError as err:
            _LOGGER.error(f"[{device_name}] Invalid value for parameter {parameter}: {err}")
            return
        
        # Update configuration
        await coordinator.update_config({parameter: validated_value})
        
        _LOGGER.info(f"[{device_name}] Parameter {parameter} updated to {validated_value}")
    
    async def async_reset_parameter(call: ServiceCall) -> None:
        """Handle reset_parameter service call."""
        entity_id = call.data["entity_id"]
        parameter = call.data["parameter"]
        
        coordinator = await _get_coordinator_from_entity_id(hass, entity_id)
        if not coordinator:
            _LOGGER.error("Could not find coordinator for entity %s", entity_id)
            return
        
        device_name = coordinator.device_name
        _LOGGER.debug(f"[{device_name}] Resetting parameter: {parameter}")
        
        if parameter not in EDITABLE_PARAMETERS:
            _LOGGER.error(f"[{device_name}] Unknown parameter: {parameter}")
            return
        
        default_value = EDITABLE_PARAMETERS[parameter]["default"]
        await coordinator.update_config({parameter: default_value})
        
        _LOGGER.info(f"[{device_name}] Parameter {parameter} reset to default: {default_value}")
    
    async def async_set_manual_override(call: ServiceCall) -> None:
        """Handle manual override service call."""
        entity_id = call.data["entity_id"]
        temperature = call.data["temperature"]
        duration_hours = call.data.get("duration_hours", 1)
        
        coordinator = await _get_coordinator_from_entity_id(hass, entity_id)
        if not coordinator:
            _LOGGER.error("Could not find coordinator for entity %s", entity_id)
            return
        
        device_name = coordinator.device_name
        _LOGGER.debug(f"[{device_name}] Setting manual override: {temperature}°C for {duration_hours}h")
        
        duration_seconds = duration_hours * 3600 if duration_hours > 0 else None
        await coordinator.set_manual_override(temperature, duration_seconds)
        
        _LOGGER.info(f"[{device_name}] Manual override set to {temperature:.1f}°C for {duration_hours}h")
    
    async def async_clear_manual_override(call: ServiceCall) -> None:
        """Handle clear manual override service call."""
        entity_id = call.data["entity_id"]
        
        coordinator = await _get_coordinator_from_entity_id(hass, entity_id)
        if not coordinator:
            _LOGGER.error("Could not find coordinator for entity %s", entity_id)
            return
        
        device_name = coordinator.device_name
        _LOGGER.debug(f"[{device_name}] Clearing manual override")
        
        await coordinator.clear_manual_override()
        
        _LOGGER.info(f"[{device_name}] Manual override cleared")
    
    async def async_set_comfort_category(call: ServiceCall) -> None:
        """Handle set comfort category service call."""
        entity_id = call.data["entity_id"]
        category = call.data["category"]
        
        coordinator = await _get_coordinator_from_entity_id(hass, entity_id)
        if not coordinator:
            _LOGGER.error("Could not find coordinator for entity %s", entity_id)
            return
        
        device_name = coordinator.device_name
        _LOGGER.debug(f"[{device_name}] Setting comfort category: {category}")
        
        await coordinator.update_comfort_category(category)
        
        _LOGGER.info(f"[{device_name}] Comfort category set to: {category}")
    
    async def async_update_calculations(call: ServiceCall) -> None:
        """Handle update calculations service call."""
        entity_id = call.data["entity_id"]
        
        coordinator = await _get_coordinator_from_entity_id(hass, entity_id)
        if not coordinator:
            _LOGGER.error("Could not find coordinator for entity %s", entity_id)
            return
        
        device_name = coordinator.device_name
        _LOGGER.debug(f"[{device_name}] Updating calculations")
        
        await coordinator.run_control_cycle()
        
        _LOGGER.info(f"[{device_name}] Calculations updated")
    
    async def async_set_temporary_override(call: ServiceCall) -> None:
        """Handle temporary override service call."""
        entity_id = call.data["entity_id"]
        temperature = call.data["temperature"]
        duration_minutes = call.data.get("duration_minutes", 30)
        
        coordinator = await _get_coordinator_from_entity_id(hass, entity_id)
        if not coordinator:
            _LOGGER.error("Could not find coordinator for entity %s", entity_id)
            return
        
        device_name = coordinator.device_name
        _LOGGER.debug(f"[{device_name}] Setting temporary override: {temperature}°C for {duration_minutes}min")
        
        duration_seconds = duration_minutes * 60 if duration_minutes > 0 else None
        await coordinator.set_manual_override(temperature, duration_seconds)
        
        _LOGGER.info(f"[{device_name}] Temporary override set to {temperature:.1f}°C for {duration_minutes}min")
    
    async def async_redetect_capabilities(call: ServiceCall) -> None:
        """Handle redetect capabilities service call."""
        entity_id = call.data["entity_id"]
        
        coordinator = await _get_coordinator_from_entity_id(hass, entity_id)
        if not coordinator:
            _LOGGER.error("Could not find coordinator for entity %s", entity_id)
            return
        
        device_name = coordinator.device_name
        _LOGGER.debug(f"[{device_name}] Re-detecting device capabilities")
        
        capabilities = await coordinator.redetect_device_capabilities()
        
        _LOGGER.info(f"[{device_name}] Device capabilities re-detected: {capabilities}")
    
    # Register services
    services_to_register = [
        (SERVICE_SET_PARAMETER, async_set_parameter, SET_PARAMETER_SCHEMA),
        (SERVICE_RESET_PARAMETER, async_reset_parameter, RESET_PARAMETER_SCHEMA),
        (SERVICE_SET_MANUAL_OVERRIDE, async_set_manual_override, MANUAL_OVERRIDE_SCHEMA),
        (SERVICE_CLEAR_MANUAL_OVERRIDE, async_clear_manual_override, CLEAR_OVERRIDE_SCHEMA),
        (SERVICE_SET_COMFORT_CATEGORY, async_set_comfort_category, SET_COMFORT_CATEGORY_SCHEMA),
        (SERVICE_UPDATE_CALCULATIONS, async_update_calculations, UPDATE_CALCULATIONS_SCHEMA),
        (SERVICE_SET_TEMPORARY_OVERRIDE, async_set_temporary_override, SET_TEMPORARY_OVERRIDE_SCHEMA),
        (SERVICE_REDETECT_CAPABILITIES, async_redetect_capabilities, REDETECT_CAPABILITIES_SCHEMA),
    ]
    
    for service_name, service_func, schema in services_to_register:
        hass.services.async_register(DOMAIN, service_name, service_func, schema=schema)
    
    _LOGGER.info("Adaptive Climate services registered successfully")


def _validate_parameter_value(parameter: str, value: Any, param_def: dict) -> Any:
    """
    Validate and convert parameter value according to its definition.
    
    Args:
        parameter: Parameter name
        value: Value to validate
        param_def: Parameter definition from EDITABLE_PARAMETERS
        
    Returns:
        Validated and converted value
        
    Raises:
        ValueError: If value is invalid
    """
    try:
        if param_def["type"] == float:
            converted_value = float(value)
            if "min" in param_def and converted_value < param_def["min"]:
                raise ValueError(f"Value {converted_value} below minimum {param_def['min']}")
            if "max" in param_def and converted_value > param_def["max"]:
                raise ValueError(f"Value {converted_value} above maximum {param_def['max']}")
            return converted_value
            
        elif param_def["type"] == int:
            converted_value = int(value)
            if "min" in param_def and converted_value < param_def["min"]:
                raise ValueError(f"Value {converted_value} below minimum {param_def['min']}")
            if "max" in param_def and converted_value > param_def["max"]:
                raise ValueError(f"Value {converted_value} above maximum {param_def['max']}")
            return converted_value
            
        elif param_def["type"] == bool:
            if isinstance(value, str):
                return value.lower() in ("true", "1", "on", "yes")
            else:
                return bool(value)
                
        elif param_def["type"] == str:
            converted_value = str(value)
            if "options" in param_def and converted_value not in param_def["options"]:
                raise ValueError(f"Value {converted_value} not in allowed options: {param_def['options']}")
            return converted_value
            
        else:
            return value
            
    except (ValueError, TypeError) as err:
        raise ValueError(f"Invalid value for parameter {parameter}: {err}")


async def _get_coordinator_from_entity_id(hass: HomeAssistant, entity_id: str) -> Optional[AdaptiveClimateCoordinator]:
    """
    Get coordinator from entity ID.
    
    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to find coordinator for
        
    Returns:
        Coordinator instance or None if not found
    """
    # Extract entry_id from entity_id (format: domain.entry_id_suffix)
    parts = entity_id.split(".")
    if len(parts) != 2:
        _LOGGER.error(f"Invalid entity_id format: {entity_id}")
        return None
    
    entity_name = parts[1]
    
    # Find the entry_id by checking all adaptive climate entries
    coordinators = hass.data.get(DOMAIN, {}).get("coordinators", {})
    
    for entry_id, coordinator in coordinators.items():
        if isinstance(coordinator, AdaptiveClimateCoordinator):
            # Check if this entity belongs to this coordinator
            if entity_name.startswith(entry_id):
                _LOGGER.debug(f"Found coordinator for entity {entity_id}: {coordinator.device_name}")
                return coordinator
    
    _LOGGER.error(f"No coordinator found for entity: {entity_id}")
    return None


def async_unload_services(hass: HomeAssistant) -> None:
    """Unload all Adaptive Climate services."""
    services_to_unload = [
        SERVICE_SET_PARAMETER,
        SERVICE_RESET_PARAMETER,
        SERVICE_SET_MANUAL_OVERRIDE,
        SERVICE_CLEAR_MANUAL_OVERRIDE,
        SERVICE_SET_COMFORT_CATEGORY,
        SERVICE_UPDATE_CALCULATIONS,
        SERVICE_SET_TEMPORARY_OVERRIDE,
        SERVICE_REDETECT_CAPABILITIES,
    ]
    
    for service_name in services_to_unload:
        hass.services.async_remove(DOMAIN, service_name)
 
    _LOGGER.info("Adaptive Climate services unloaded successfully")
