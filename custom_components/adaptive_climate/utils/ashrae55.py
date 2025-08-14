"""
ASHRAE 55 adaptive comfort calculation (pure Python, HA-friendly).

Renamed from pythermalcomfort_patched.py to ashrae55.py and moved to utils.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, NamedTuple, Optional


_LOGGER = logging.getLogger(__name__)


class AdaptiveAshraeResult(NamedTuple):
    """Result from ASHRAE 55 adaptive comfort calculation."""

    tmp_cmf: float
    tmp_cmf_80_low: float
    tmp_cmf_80_up: float
    tmp_cmf_90_low: float
    tmp_cmf_90_up: float
    acceptability_80: bool
    acceptability_90: bool


# ASHRAE 55 constants
ASHRAE_55_TEMP_MIN = 10.0
ASHRAE_55_TEMP_MAX = 33.5

# ASHRAE 55 comfort equation constants
ASHRAE_55_BASE_TEMP = 18.9
ASHRAE_55_TEMP_COEFFICIENT = 0.255

# Acceptability limits
ACCEPTABILITY_80_RANGE = 3.5
ACCEPTABILITY_90_RANGE = 2.5

# Air velocity thresholds
AIR_VELOCITY_MIN = 0.1
AIR_VELOCITY_HIGH = 0.2


def _ashrae_55_adaptive_calculation(tdb: float, tr: float, t_running_mean: float, v: float) -> tuple:
    """Core ASHRAE 55 adaptive comfort calculation."""

    # Comfort temperature (ASHRAE 55-2020, Section 5.4)
    t_cmf = ASHRAE_55_BASE_TEMP + ASHRAE_55_TEMP_COEFFICIENT * t_running_mean

    # Operative temperature
    t_op = (tdb + tr) / 2.0

    # Air velocity cooling effect
    if v > AIR_VELOCITY_MIN:
        if v > AIR_VELOCITY_HIGH:
            cooling_effect = 1.2 * math.log10(v * 10.0)
        else:
            cooling_effect = 0.6 * (v - AIR_VELOCITY_MIN) / AIR_VELOCITY_MIN
        t_op_adjusted = t_op + cooling_effect
    else:
        t_op_adjusted = t_op

    # Acceptability limits
    tmp_80_low = t_cmf - ACCEPTABILITY_80_RANGE
    tmp_80_up = t_cmf + ACCEPTABILITY_80_RANGE
    tmp_90_low = t_cmf - ACCEPTABILITY_90_RANGE
    tmp_90_up = t_cmf + ACCEPTABILITY_90_RANGE

    acceptable_80 = tmp_80_low <= t_op_adjusted <= tmp_80_up
    acceptable_90 = tmp_90_low <= t_op_adjusted <= tmp_90_up

    return (t_cmf, tmp_80_low, tmp_80_up, tmp_90_low, tmp_90_up, acceptable_80, acceptable_90)


def adaptive_ashrae(
    tdb: float,
    tr: float,
    t_running_mean: float,
    v: float = 0.1,
    units: str = "SI",
    device_name: Optional[str] = None,
) -> AdaptiveAshraeResult:
    """Calculate adaptive comfort temperature according to ASHRAE 55."""

    device_prefix = f"[{device_name}] " if device_name else ""

    if not (ASHRAE_55_TEMP_MIN <= t_running_mean <= ASHRAE_55_TEMP_MAX):
        error_msg = (
            f"Running mean outdoor temperature {t_running_mean:.1f}°C is outside "
            f"ASHRAE 55 valid range ({ASHRAE_55_TEMP_MIN}-{ASHRAE_55_TEMP_MAX}°C)"
        )
        _LOGGER.error(f"{device_prefix}{error_msg}")
        raise ValueError(error_msg)

    if units.upper() != "SI":
        error_msg = "Only SI units (Celsius) are supported"
        _LOGGER.error(f"{device_prefix}{error_msg}")
        raise ValueError(error_msg)

    if v < 0:
        error_msg = f"Air velocity {v} m/s cannot be negative"
        _LOGGER.error(f"{device_prefix}{error_msg}")
        raise ValueError(error_msg)

    temp_diff = abs(tdb - tr)
    if temp_diff > 50:
        _LOGGER.warning(
            f"{device_prefix}Large difference between air temp ({tdb:.1f}°C) and "
            f"radiant temp ({tr:.1f}°C): {temp_diff:.1f}°C"
        )

    _LOGGER.debug(
        f"{device_prefix}ASHRAE 55 calculation parameters: "
        f"tdb={tdb:.1f}°C, tr={tr:.1f}°C, t_running_mean={t_running_mean:.1f}°C, v={v:.2f}m/s"
    )

    try:
        result = _ashrae_55_adaptive_calculation(tdb, tr, t_running_mean, v)
        ashrae_result = AdaptiveAshraeResult(
            tmp_cmf=float(result[0]),
            tmp_cmf_80_low=float(result[1]),
            tmp_cmf_80_up=float(result[2]),
            tmp_cmf_90_low=float(result[3]),
            tmp_cmf_90_up=float(result[4]),
            acceptability_80=bool(result[5]),
            acceptability_90=bool(result[6]),
        )
        _LOGGER.debug(
            f"{device_prefix}ASHRAE 55 results: "
            f"comfort_temp={ashrae_result.tmp_cmf:.1f}°C, "
            f"80%_range=[{ashrae_result.tmp_cmf_80_low:.1f}-{ashrae_result.tmp_cmf_80_up:.1f}]°C, "
            f"90%_range=[{ashrae_result.tmp_cmf_90_low:.1f}-{ashrae_result.tmp_cmf_90_up:.1f}]°C, "
            f"acceptable_80={ashrae_result.acceptability_80}, "
            f"acceptable_90={ashrae_result.acceptability_90}"
        )
        return ashrae_result
    except Exception as e:  # noqa: BLE001
        error_msg = f"ASHRAE 55 adaptive comfort calculation failed: {e}"
        _LOGGER.error(f"{device_prefix}{error_msg}")
        raise RuntimeError(error_msg) from e


def adaptive_ashrae_80(
    tdb: float, tr: float, t_running_mean: float, v: float = 0.1, device_name: Optional[str] = None
) -> Dict[str, Any]:
    result = adaptive_ashrae(tdb, tr, t_running_mean, v, device_name=device_name)
    return {
        "tmp_cmf": result.tmp_cmf,
        "tmp_cmf_80_low": result.tmp_cmf_80_low,
        "tmp_cmf_80_up": result.tmp_cmf_80_up,
        "acceptability_80": result.acceptability_80,
    }


def adaptive_ashrae_90(
    tdb: float, tr: float, t_running_mean: float, v: float = 0.1, device_name: Optional[str] = None
) -> Dict[str, Any]:
    result = adaptive_ashrae(tdb, tr, t_running_mean, v, device_name=device_name)
    return {
        "tmp_cmf": result.tmp_cmf,
        "tmp_cmf_90_low": result.tmp_cmf_90_low,
        "tmp_cmf_90_up": result.tmp_cmf_90_up,
        "acceptability_90": result.acceptability_90,
    }


__version__ = "2.10.0-patched-ha-pure"

_LOGGER.info("ashrae55 utils loaded (pure Python - no external dependencies)")


