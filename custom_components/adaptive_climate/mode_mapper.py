"""
Mode mapper for HVAC and fan mode compatibility.

This module provides mapping functions to convert calculated HVAC and fan modes
to modes supported by specific climate devices. It handles various naming
conventions and provides fallback mechanisms for compatibility.

Compatible with:
- Various HVAC system naming conventions
- Fan mode variations across different manufacturers
- Automatic fallback to supported modes
"""

import logging
from typing import List, Dict, Any, Optional

_LOGGER = logging.getLogger(__name__)

# Fan mode equivalents for different manufacturers
FAN_MODE_EQUIVALENTS = {
    "off": ["off", "Off", "OFF"],
    "auto": ["auto", "Auto", "AUTO"],
    "quiet": ["quiet", "Quiet", "silent", "Silence", "night", "Night", "sleep"],
    "lowest": ["lowest", "min", "minimum", "level1", "ultralow", "1"],
    "low": ["low", "Low", "level1", "1", "slow"],
    "mediumlow": ["mediumlow", "medium low", "level2", "2", "medlow"],
    "mid": ["mid", "Mid", "medium", "Medium", "med", "middle", "level3", "3"],
    "mediumhigh": ["mediumhigh", "medium high", "level4", "4", "medhigh"],
    "high": ["high", "High", "level5", "5", "fast"],
    "highest": ["highest", "max", "maximum", "top", "superhigh", "powerful", "turbo", "Turbo", "strong", "Strong"],
}

# HVAC mode equivalents for different manufacturers
HVAC_MODE_EQUIVALENTS = {
    "auto": ["auto", "heat_cool", "Heat/Cool", "heatcool", "Auto", "AUTO"],
    "cool": ["cool", "Cool", "COOL", "cooling"],
    "heat": ["heat", "Heat", "HEAT", "heating"],
    "dry": ["dry", "Dry", "dehumidify", "DRY"],
    "humidify": ["humidify", "Humidify", "humidification", "HUMIDIFY"], 
    "fan_only": ["fan_only", "fan", "Fan only", "Fan", "fanonly", "FAN"],
    "off": ["off", "Off", "OFF", "stop"],
}

def map_mode(
    calculated: str, 
    supported: List[str], 
    equivalents: Dict[str, List[str]],
    device_name: Optional[str] = None
) -> str:
    """
    Map calculated mode to supported mode using multiple strategies.
    
    Args:
        calculated: The calculated mode to map
        supported: List of supported modes by the device
        equivalents: Dictionary of mode equivalents
        device_name: Optional device name for logging
        
    Returns:
        Mapped mode that is supported by the device
        
    Strategy:
        1. Direct match (case-insensitive)
        2. Equivalent match using aliases
        3. Partial match (substring)
        4. Fallback to first supported mode
    """
    device_prefix = f"[{device_name}] " if device_name else ""
    
    if not calculated or not supported:
        _LOGGER.warning(f"{device_prefix}Invalid input: calculated='{calculated}', supported={supported}")
        return calculated if calculated else (supported[0] if supported else "off")
    
    calculated_lower = calculated.lower().strip()
    supported_lower = [m.lower().strip() for m in supported]
    
    _LOGGER.debug(f"{device_prefix}Mapping mode: calculated='{calculated}' to supported={supported}")
    
    # Strategy 1: Direct match (case-insensitive)
    if calculated_lower in supported_lower:
        mapped_mode = supported[supported_lower.index(calculated_lower)]
        _LOGGER.debug(f"{device_prefix}Direct match found: '{calculated}' -> '{mapped_mode}'")
        return mapped_mode
    
    # Strategy 2: Equivalent match using aliases
    for key, aliases in equivalents.items():
        if calculated_lower == key or calculated_lower in [alias.lower() for alias in aliases]:
            for alias in aliases:
                alias_lower = alias.lower()
                if alias_lower in supported_lower:
                    mapped_mode = supported[supported_lower.index(alias_lower)]
                    _LOGGER.debug(f"{device_prefix}Equivalent match found: '{calculated}' -> '{mapped_mode}' (via '{alias}')")
                    return mapped_mode
    
    # Strategy 3: Partial match (substring)
    for mode in supported:
        mode_lower = mode.lower()
        if (calculated_lower in mode_lower or 
            mode_lower in calculated_lower or
            any(word in mode_lower for word in calculated_lower.split())):
            _LOGGER.debug(f"{device_prefix}Partial match found: '{calculated}' -> '{mode}'")
            return mode
    
    # Strategy 4: Fallback to first supported mode
    fallback_mode = supported[0] if supported else calculated
    _LOGGER.warning(f"{device_prefix}No match found for '{calculated}', using fallback: '{fallback_mode}'")
    return fallback_mode

def map_fan_mode(
    calculated_fan: str, 
    supported_fan_modes: List[str],
    device_name: Optional[str] = None
) -> str:
    """
    Map calculated fan mode to supported fan mode.
    
    Args:
        calculated_fan: The calculated fan mode
        supported_fan_modes: List of supported fan modes by the device
        device_name: Optional device name for logging
        
    Returns:
        Mapped fan mode that is supported by the device
    """
    device_prefix = f"[{device_name}] " if device_name else ""
    
    if not supported_fan_modes:
        _LOGGER.warning(f"{device_prefix}No supported fan modes provided, returning calculated: '{calculated_fan}'")
        return calculated_fan
    
    mapped_mode = map_mode(calculated_fan, supported_fan_modes, FAN_MODE_EQUIVALENTS, device_name)
    
    # Special handling for "highest" mode
    if calculated_fan.lower() == "highest" and "highest" not in [m.lower() for m in supported_fan_modes]:
        if "high" in [m.lower() for m in supported_fan_modes]:
            high_mode = next(m for m in supported_fan_modes if m.lower() == "high")
            _LOGGER.debug(f"{device_prefix}Mapped 'highest' to 'high' as fallback")
            return high_mode
    
    _LOGGER.debug(f"{device_prefix}Fan mode mapping: '{calculated_fan}' -> '{mapped_mode}'")
    return mapped_mode

def map_hvac_mode(
    calculated_hvac: str, 
    supported_hvac_modes: List[str],
    device_name: Optional[str] = None
) -> str:
    """
    Map calculated HVAC mode to supported HVAC mode.
    
    Args:
        calculated_hvac: The calculated HVAC mode
        supported_hvac_modes: List of supported HVAC modes by the device
        device_name: Optional device name for logging
        
    Returns:
        Mapped HVAC mode that is supported by the device
    """
    device_prefix = f"[{device_name}] " if device_name else ""
    
    if not supported_hvac_modes:
        _LOGGER.warning(f"{device_prefix}No supported HVAC modes provided, returning calculated: '{calculated_hvac}'")
        return calculated_hvac
    
    # Check if device only supports heating (like radiators)
    has_heat = any("heat" in mode.lower() for mode in supported_hvac_modes)
    has_cool = any("cool" in mode.lower() for mode in supported_hvac_modes)
    has_auto = any("auto" in mode.lower() for mode in supported_hvac_modes)
    has_off = any("off" in mode.lower() for mode in supported_hvac_modes)
    
    # Special handling for heating-only devices (like radiators)
    if has_heat and not has_cool:
        _LOGGER.debug(f"{device_prefix}Heating-only device detected")
        
        if calculated_hvac.lower() in ["cool", "dry", "fan_only"]:
            # For cooling requests on heating-only device, turn off
            if has_off:
                _LOGGER.debug(f"{device_prefix}Cooling requested on heating-only device, turning off")
                return next(m for m in supported_hvac_modes if "off" in m.lower())
            else:
                # If no off mode, use auto if available
                if has_auto:
                    _LOGGER.debug(f"{device_prefix}Cooling requested on heating-only device, using auto")
                    return next(m for m in supported_hvac_modes if "auto" in m.lower())
        
        elif calculated_hvac.lower() == "heat":
            # Heating requested - use heat mode
            if has_heat:
                _LOGGER.debug(f"{device_prefix}Heating requested on heating-only device")
                return next(m for m in supported_hvac_modes if "heat" in m.lower())
        
        elif calculated_hvac.lower() == "off":
            # Off requested
            if has_off:
                return next(m for m in supported_hvac_modes if "off" in m.lower())
            else:
                # If no off mode, use auto
                if has_auto:
                    _LOGGER.debug(f"{device_prefix}Off requested but not supported, using auto")
                    return next(m for m in supported_hvac_modes if "auto" in m.lower())
    
    mapped_mode = map_mode(calculated_hvac, supported_hvac_modes, HVAC_MODE_EQUIVALENTS, device_name)
    
    # Special handling for "auto" mode
    if calculated_hvac.lower() == "auto":
        # Check if device supports heat_cool instead of auto
        if "heat_cool" in [m.lower() for m in supported_hvac_modes] and "auto" not in [m.lower() for m in supported_hvac_modes]:
            heat_cool_mode = next(m for m in supported_hvac_modes if m.lower() == "heat_cool")
            _LOGGER.debug(f"{device_prefix}Mapped 'auto' to 'heat_cool' as equivalent")
            return heat_cool_mode
    
    _LOGGER.debug(f"{device_prefix}HVAC mode mapping: '{calculated_hvac}' -> '{mapped_mode}'")
    return mapped_mode

def get_supported_modes_info(
    supported_hvac_modes: List[str],
    supported_fan_modes: List[str],
    device_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get information about supported modes for debugging.
    
    Args:
        supported_hvac_modes: List of supported HVAC modes
        supported_fan_modes: List of supported fan modes
        device_name: Optional device name for logging
        
    Returns:
        Dictionary with mode information
    """
    device_prefix = f"[{device_name}] " if device_name else ""
    
    info = {
        "hvac_modes": supported_hvac_modes,
        "fan_modes": supported_fan_modes,
        "hvac_count": len(supported_hvac_modes),
        "fan_count": len(supported_fan_modes),
        "has_auto": any("auto" in mode.lower() for mode in supported_hvac_modes),
        "has_heat_cool": any("heat_cool" in mode.lower() for mode in supported_hvac_modes),
        "has_off": any("off" in mode.lower() for mode in supported_hvac_modes),
        "has_high_fan": any("high" in mode.lower() for mode in supported_fan_modes),
        "has_highest_fan": any("highest" in mode.lower() for mode in supported_fan_modes),
    }
    
    _LOGGER.debug(f"{device_prefix}Supported modes info: {info}")
    return info

# Log successful import
_LOGGER.info("mode_mapper loaded successfully")

def detect_device_capabilities(
    supported_hvac_modes: List[str],
    supported_fan_modes: List[str],
    device_name: Optional[str] = None
) -> Dict[str, bool]:
    """
    Detect device capabilities based on supported modes.
    
    Args:
        supported_hvac_modes: List of supported HVAC modes
        supported_fan_modes: List of supported fan modes
        device_name: Optional device name for logging
        
    Returns:
        Dictionary with detected capabilities
    """
    device_prefix = f"[{device_name}] " if device_name else ""
    
    _LOGGER.debug(f"{device_prefix}Detecting device capabilities from modes:")
    _LOGGER.debug(f"{device_prefix}  - HVAC modes: {supported_hvac_modes}")
    _LOGGER.debug(f"{device_prefix}  - Fan modes: {supported_fan_modes}")
    
    # Convert to lowercase for easier comparison
    hvac_lower = [mode.lower() for mode in supported_hvac_modes]
    fan_lower = [mode.lower() for mode in supported_fan_modes]
    
    # Detect cooling capability
    is_cool = any(mode in ["cool", "auto", "heat_cool"] for mode in hvac_lower)
    
    # Detect heating capability
    is_heat = any(mode in ["heat", "auto", "heat_cool"] for mode in hvac_lower)
    
    # Detect fan capability
    is_fan = any(mode in ["fan_only", "fan"] for mode in hvac_lower) or len(supported_fan_modes) > 0
    
    # Detect dry capability
    is_dry = any(mode in ["dry", "dehumidify"] for mode in hvac_lower)
    
    # Special handling for devices with "auto" mode
    if "auto" in hvac_lower:
        # Auto mode can handle both cooling and heating
        is_cool = True
        is_heat = True
        _LOGGER.debug(f"{device_prefix}Auto mode detected - enabling both cool and heat capabilities")
    
    # Special handling for "heat_cool" mode
    if any("heat_cool" in mode for mode in hvac_lower):
        is_cool = True
        is_heat = True
        _LOGGER.debug(f"{device_prefix}Heat_cool mode detected - enabling both cool and heat capabilities")
    
    # Special handling for TRV/radiator devices - they can NEVER cool
    if device_name and any(keyword in device_name.lower() for keyword in ["trv", "radiator", "thermostat"]):
        is_cool = False
        is_fan = False
        is_dry = False
        _LOGGER.debug(f"{device_prefix}TRV/radiator device detected - disabling cooling, fan, and dry capabilities")
    
    capabilities = {
        "is_cool": is_cool,
        "is_heat": is_heat,
        "is_fan": is_fan,
        "is_dry": is_dry,
    }
    
    # Determine device type
    if is_cool and is_heat:
        device_type = "Heat/Cool (AC)"
    elif is_heat:
        device_type = "Heat Only (TRV/Heater)"
    elif is_cool:
        device_type = "Cool Only (AC)"
    elif is_fan:
        device_type = "Fan Only"
    else:
        device_type = "Unknown"
    
    _LOGGER.info(f"{device_prefix}Device capabilities detected:")
    _LOGGER.info(f"{device_prefix}  - Cooling: {is_cool}")
    _LOGGER.info(f"{device_prefix}  - Heating: {is_heat}")
    _LOGGER.info(f"{device_prefix}  - Fan: {is_fan}")
    _LOGGER.info(f"{device_prefix}  - Dry: {is_dry}")
    _LOGGER.info(f"{device_prefix}  - Device type: {device_type}")
    
    return capabilities

def validate_mode_compatibility(
    calculated_hvac: str,
    calculated_fan: str,
    supported_hvac_modes: List[str],
    supported_fan_modes: List[str],
    device_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validate if calculated modes are compatible with device capabilities.
    
    Args:
        calculated_hvac: The calculated HVAC mode
        calculated_fan: The calculated fan mode
        supported_hvac_modes: List of supported HVAC modes
        supported_fan_modes: List of supported fan modes
        device_name: Optional device name for logging
        
    Returns:
        Dictionary with validation results and suggestions
    """
    device_prefix = f"[{device_name}] " if device_name else ""
    
    # Detect capabilities
    capabilities = detect_device_capabilities(supported_hvac_modes, supported_fan_modes, device_name)
    
    # Validate HVAC mode
    hvac_valid = True
    hvac_suggestion = calculated_hvac
    
    if calculated_hvac.lower() == "cool" and not capabilities["is_cool"]:
        hvac_valid = False
        if capabilities["is_heat"]:
            hvac_suggestion = "off"  # Turn off if cooling not supported
        else:
            hvac_suggestion = "fan_only" if capabilities["is_fan"] else "off"
        _LOGGER.warning(f"{device_prefix}Cooling requested but device doesn't support cooling")
    
    elif calculated_hvac.lower() == "heat" and not capabilities["is_heat"]:
        hvac_valid = False
        if capabilities["is_cool"]:
            hvac_suggestion = "off"  # Turn off if heating not supported
        else:
            hvac_suggestion = "fan_only" if capabilities["is_fan"] else "off"
        _LOGGER.warning(f"{device_prefix}Heating requested but device doesn't support heating")
    
    elif calculated_hvac.lower() == "dry" and not capabilities["is_dry"]:
        hvac_valid = False
        hvac_suggestion = "off"
        _LOGGER.warning(f"{device_prefix}Dry mode requested but device doesn't support dry mode")
    
    elif calculated_hvac.lower() == "fan_only" and not capabilities["is_fan"]:
        hvac_valid = False
        hvac_suggestion = "off"
        _LOGGER.warning(f"{device_prefix}Fan mode requested but device doesn't support fan mode")
    
    # Validate fan mode
    fan_valid = True
    fan_suggestion = calculated_fan
    
    if calculated_fan.lower() != "off" and not capabilities["is_fan"]:
        fan_valid = False
        fan_suggestion = "off"
        _LOGGER.warning(f"{device_prefix}Fan mode requested but device doesn't support fan modes")
    
    validation_result = {
        "hvac_valid": hvac_valid,
        "fan_valid": fan_valid,
        "hvac_suggestion": hvac_suggestion,
        "fan_suggestion": fan_suggestion,
        "capabilities": capabilities,
        "compatible": hvac_valid and fan_valid,
    }
    
    _LOGGER.debug(f"{device_prefix}Mode validation result: {validation_result}")
    return validation_result