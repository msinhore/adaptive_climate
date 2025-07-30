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