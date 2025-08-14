from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

_LOGGER = logging.getLogger(__name__)

FAN_MODE_EQUIVALENTS = {
    "off": ["off", "Off", "OFF"],
    "auto": ["auto", "Auto", "AUTO"],
    "quiet": [
        "quiet",
        "Quiet",
        "silent",
        "Silence",
        "night",
        "Night",
        "sleep",
    ],
    "lowest": ["lowest", "min", "minimum", "level1", "ultralow", "1"],
    "low": ["low", "Low", "level1", "1", "slow"],
    "mediumlow": ["mediumlow", "medium low", "level2", "2", "medlow"],
    "mid": ["mid", "Mid", "medium", "Medium", "med", "middle", "level3", "3"],
    "mediumhigh": ["mediumhigh", "medium high", "level4", "4", "medhigh"],
    "high": ["high", "High", "level5", "5", "fast"],
    "highest": [
        "highest",
        "max",
        "maximum",
        "top",
        "superhigh",
        "powerful",
        "turbo",
        "Turbo",
        "strong",
        "Strong",
    ],
}

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
    calculated: str, supported: List[str], equivalents: Dict[str, List[str]], device_name: Optional[str] = None
) -> str:
    device_prefix = f"[{device_name}] " if device_name else ""
    if not calculated or not supported:
        _LOGGER.warning(
            f"{device_prefix}Invalid input: calculated='{calculated}', supported={supported}"
        )
        return calculated if calculated else (supported[0] if supported else "off")

    calculated_lower = calculated.lower().strip()
    supported_lower = [m.lower().strip() for m in supported]

    _LOGGER.debug(
        f"{device_prefix}Mapping mode: calculated='{calculated}' to supported={supported}"
    )

    if calculated_lower in supported_lower:
        mapped_mode = supported[supported_lower.index(calculated_lower)]
        _LOGGER.debug(
            f"{device_prefix}Direct match found: '{calculated}' -> '{mapped_mode}'"
        )
        return mapped_mode

    for key, aliases in equivalents.items():
        if calculated_lower == key or calculated_lower in [alias.lower() for alias in aliases]:
            for alias in aliases:
                alias_lower = alias.lower()
                if alias_lower in supported_lower:
                    mapped_mode = supported[supported_lower.index(alias_lower)]
                    _LOGGER.debug(
                        f"{device_prefix}Equivalent match found: '{calculated}' -> '{mapped_mode}' (via '{alias}')"
                    )
                    return mapped_mode

    for mode in supported:
        mode_lower = mode.lower()
        if calculated_lower in mode_lower or mode_lower in calculated_lower or any(
            word in mode_lower for word in calculated_lower.split()
        ):
            _LOGGER.debug(
                f"{device_prefix}Partial match found: '{calculated}' -> '{mode}'"
            )
            return mode

    fallback_mode = supported[0] if supported else calculated
    _LOGGER.warning(
        f"{device_prefix}No match found for '{calculated}', using fallback: '{fallback_mode}'"
    )
    return fallback_mode


def map_fan_mode(calculated_fan: str, supported_fan_modes: List[str], device_name: Optional[str] = None) -> str:
    if not supported_fan_modes:
        _LOGGER.warning(
            f"[{device_name}] No supported fan modes provided, returning calculated: '{calculated_fan}'"
        )
        return calculated_fan
    mapped_mode = map_mode(calculated_fan, supported_fan_modes, FAN_MODE_EQUIVALENTS, device_name)
    if calculated_fan and calculated_fan.lower() == "highest" and "highest" not in [m.lower() for m in supported_fan_modes]:
        if "high" in [m.lower() for m in supported_fan_modes]:
            return next(m for m in supported_fan_modes if m.lower() == "high")
    return mapped_mode


def map_hvac_mode(calculated_hvac: str, supported_hvac_modes: List[str], device_name: Optional[str] = None) -> str:
    if not supported_hvac_modes:
        _LOGGER.warning(
            f"[{device_name}] No supported HVAC modes provided, returning calculated: '{calculated_hvac}'"
        )
        return calculated_hvac

    hvac_lower = [mode.lower() for mode in supported_hvac_modes]
    has_heat = any("heat" in mode for mode in hvac_lower)
    has_cool = any("cool" in mode for mode in hvac_lower)
    has_auto = any("auto" in mode for mode in hvac_lower)
    has_off = any("off" in mode for mode in hvac_lower)

    if has_heat and not has_cool:
        if calculated_hvac.lower() in ["cool", "dry", "fan_only"]:
            if has_off:
                return next(m for m in supported_hvac_modes if "off" in m.lower())
            if has_auto:
                return next(m for m in supported_hvac_modes if "auto" in m.lower())
        if calculated_hvac.lower() == "heat" and has_heat:
            return next(m for m in supported_hvac_modes if "heat" in m.lower())
        if calculated_hvac.lower() == "off" and has_off:
            return next(m for m in supported_hvac_modes if "off" in m.lower())
        if calculated_hvac.lower() == "off" and has_auto:
            return next(m for m in supported_hvac_modes if "auto" in m.lower())

    mapped_mode = map_mode(calculated_hvac, supported_hvac_modes, HVAC_MODE_EQUIVALENTS, device_name)

    if calculated_hvac.lower() == "auto":
        if "heat_cool" in [m.lower() for m in supported_hvac_modes] and "auto" not in [m.lower() for m in supported_hvac_modes]:
            return next(m for m in supported_hvac_modes if m.lower() == "heat_cool")

    return mapped_mode


def get_supported_modes_info(
    supported_hvac_modes: List[str], supported_fan_modes: List[str], device_name: Optional[str] = None
) -> Dict[str, Any]:
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
    return info


def detect_device_capabilities(
    supported_hvac_modes: List[str], supported_fan_modes: List[str], device_name: Optional[str] = None
) -> Dict[str, bool]:
    hvac_lower = [mode.lower() for mode in supported_hvac_modes]
    is_cool = any(mode in ["cool", "auto", "heat_cool"] for mode in hvac_lower)
    is_heat = any(mode in ["heat", "auto", "heat_cool"] for mode in hvac_lower)
    is_fan = any(mode in ["fan_only", "fan"] for mode in hvac_lower) or len(supported_fan_modes) > 0
    is_dry = any(mode in ["dry", "dehumidify"] for mode in hvac_lower)
    if "auto" in hvac_lower:
        is_cool = True
        is_heat = True
    if any("heat_cool" in mode for mode in hvac_lower):
        is_cool = True
        is_heat = True
    return {"is_cool": is_cool, "is_heat": is_heat, "is_fan": is_fan, "is_dry": is_dry}


def validate_mode_compatibility(
    calculated_hvac: str,
    calculated_fan: str,
    supported_hvac_modes: List[str],
    supported_fan_modes: List[str],
    device_name: Optional[str] = None,
) -> Dict[str, Any]:
    capabilities = detect_device_capabilities(supported_hvac_modes, supported_fan_modes, device_name)
    hvac_valid = True
    fan_valid = True
    hvac_suggestion = calculated_hvac
    fan_suggestion = calculated_fan

    if calculated_hvac.lower() == "cool" and not capabilities["is_cool"]:
        hvac_valid = False
        hvac_suggestion = "off" if capabilities["is_heat"] else ("fan_only" if capabilities["is_fan"] else "off")
    elif calculated_hvac.lower() == "heat" and not capabilities["is_heat"]:
        hvac_valid = False
        hvac_suggestion = "off" if capabilities["is_cool"] else ("fan_only" if capabilities["is_fan"] else "off")
    elif calculated_hvac.lower() == "dry" and not capabilities["is_dry"]:
        hvac_valid = False
        hvac_suggestion = "off"
    elif calculated_hvac.lower() == "fan_only" and not capabilities["is_fan"]:
        hvac_valid = False
        hvac_suggestion = "off"

    if calculated_fan.lower() != "off" and not capabilities["is_fan"]:
        fan_valid = False
        fan_suggestion = "off"

    return {
        "hvac_valid": hvac_valid,
        "fan_valid": fan_valid,
        "hvac_suggestion": hvac_suggestion,
        "fan_suggestion": fan_suggestion,
        "capabilities": capabilities,
        "compatible": hvac_valid and fan_valid,
    }



