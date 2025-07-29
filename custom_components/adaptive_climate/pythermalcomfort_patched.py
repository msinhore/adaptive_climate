"""
Patched pythermalcomfort for Home Assistant compatibility.
Extracted from pythermalcomfort library with Python 3.13.3 adaptations.

Original: https://github.com/CenterForTheBuiltEnvironment/pythermalcomfort
Fork: https://github.com/msinhore/pythermalcomfort

This implementation is based on:
Tartarini, F., Schiavon, S., 2020.
pythermalcomfort: A Python package for thermal comfort research.
SoftwareX 12, 100578.
https://doi.org/10.1016/j.softx.2020.100578

Compatible with:
- Pure Python implementation (no external dependencies)
- Python 3.13.3+
- All Home Assistant environments
"""

import math
import logging
from typing import NamedTuple, Union, Dict, Any, Optional

# No external dependencies - pure Python implementation
NUMBA_AVAILABLE = False

def jit(*args, **kwargs):
    """Fallback decorator that does nothing - pure Python execution."""
    def decorator(func):
        return func
    return decorator if args else decorator

_LOGGER = logging.getLogger(__name__)

class AdaptiveAshraeResult(NamedTuple):
    """Result from ASHRAE 55 adaptive comfort calculation."""
    tmp_cmf: float  # Comfort temperature
    tmp_cmf_80_low: float  # Lower bound 80% acceptability
    tmp_cmf_80_up: float   # Upper bound 80% acceptability
    tmp_cmf_90_low: float  # Lower bound 90% acceptability  
    tmp_cmf_90_up: float   # Upper bound 90% acceptability
    acceptability_80: bool # Within 80% acceptability
    acceptability_90: bool # Within 90% acceptability

# ASHRAE 55 constants
ASHRAE_55_TEMP_MIN = 10.0  # Minimum outdoor running mean temperature (°C)
ASHRAE_55_TEMP_MAX = 33.5  # Maximum outdoor running mean temperature (°C)

# ASHRAE 55 comfort equation constants
ASHRAE_55_BASE_TEMP = 18.9  # Base comfort temperature (°C)
ASHRAE_55_TEMP_COEFFICIENT = 0.255  # Temperature coefficient

# Acceptability limits
ACCEPTABILITY_80_RANGE = 3.5  # ±3.5°C for 80% acceptability
ACCEPTABILITY_90_RANGE = 2.5  # ±2.5°C for 90% acceptability

# Air velocity thresholds
AIR_VELOCITY_MIN = 0.1  # Minimum air velocity for cooling effect (m/s)
AIR_VELOCITY_HIGH = 0.2  # High air velocity threshold (m/s)

def _ashrae_55_adaptive_calculation(
    tdb: float,
    tr: float,
    t_running_mean: float,
    v: float
) -> tuple:
    """
    Core ASHRAE 55 adaptive comfort calculation.
    
    Based on ASHRAE Standard 55-2020, Section 5.4 Adaptive Model.
    
    Args:
        tdb: Dry bulb air temperature [°C]
        tr: Mean radiant temperature [°C]
        t_running_mean: Prevailing mean outdoor temperature [°C]
        v: Air velocity [m/s]
        
    Returns:
        Tuple with (t_cmf, tmp_80_low, tmp_80_up, tmp_90_low, tmp_90_up, acceptable_80, acceptable_90)
    """
    # ASHRAE 55-2020 adaptive comfort temperature equation
    # T_comfort = 18.9 + 0.255 * T_outdoor_running_mean
    t_cmf = ASHRAE_55_BASE_TEMP + ASHRAE_55_TEMP_COEFFICIENT * t_running_mean
    
    # Calculate operative temperature (average of air and radiant)
    t_op = (tdb + tr) / 2.0
    
    # Air velocity cooling effect (ASHRAE 55, Section 5.4.3)
    if v > AIR_VELOCITY_MIN:
        # Cooling effect from elevated air speed
        # Based on CBE Comfort Tool implementation
        if v > AIR_VELOCITY_HIGH:
            cooling_effect = 1.2 * math.log10(v * 10.0)
        else:
            cooling_effect = 0.6 * (v - AIR_VELOCITY_MIN) / AIR_VELOCITY_MIN
        t_op_adjusted = t_op + cooling_effect
    else:
        t_op_adjusted = t_op
    
    # ASHRAE 55 acceptability limits
    # 80% acceptability: ±3.5°C from comfort temperature
    tmp_80_low = t_cmf - ACCEPTABILITY_80_RANGE
    tmp_80_up = t_cmf + ACCEPTABILITY_80_RANGE
    
    # 90% acceptability: ±2.5°C from comfort temperature  
    tmp_90_low = t_cmf - ACCEPTABILITY_90_RANGE
    tmp_90_up = t_cmf + ACCEPTABILITY_90_RANGE
    
    # Check acceptability
    acceptable_80 = tmp_80_low <= t_op_adjusted <= tmp_80_up
    acceptable_90 = tmp_90_low <= t_op_adjusted <= tmp_90_up
    
    return (
        t_cmf,
        tmp_80_low,
        tmp_80_up,
        tmp_90_low, 
        tmp_90_up,
        acceptable_80,
        acceptable_90
    )

def adaptive_ashrae(
    tdb: float,
    tr: float,
    t_running_mean: float,
    v: float = 0.1,
    units: str = "SI",
    device_name: Optional[str] = None
) -> AdaptiveAshraeResult:
    """
    Calculate adaptive comfort temperature according to ASHRAE 55.
    
    This function implements the adaptive thermal comfort model from 
    ASHRAE Standard 55-2020, Section 5.4.
    
    Args:
        tdb: Dry bulb air temperature [°C]
        tr: Mean radiant temperature [°C]
        t_running_mean: Prevailing mean outdoor temperature [°C]
        v: Air velocity [m/s], default 0.1
        units: Temperature units, "SI" for Celsius (Fahrenheit not supported)
        device_name: Optional device name for logging
        
    Returns:
        AdaptiveAshraeResult with comfort temperature and acceptability data
        
    Raises:
        ValueError: If t_running_mean is outside valid ASHRAE 55 range
        
    References:
        ASHRAE Standard 55-2020: Thermal Environmental Conditions for Human Occupancy
        CBE Comfort Tool: https://comfort.cbe.berkeley.edu/
    """
    device_prefix = f"[{device_name}] " if device_name else ""
    
    # Input validation per ASHRAE 55
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
    
    # Validate other inputs
    if v < 0:
        error_msg = f"Air velocity {v} m/s cannot be negative"
        _LOGGER.error(f"{device_prefix}{error_msg}")
        raise ValueError(error_msg)
        
    # Sanity check for extreme conditions
    temp_diff = abs(tdb - tr)
    if temp_diff > 50:
        _LOGGER.warning(
            f"{device_prefix}Large difference between air temp ({tdb:.1f}°C) and "
            f"radiant temp ({tr:.1f}°C): {temp_diff:.1f}°C"
        )
    
    # Log calculation parameters
    _LOGGER.debug(
        f"{device_prefix}ASHRAE 55 calculation parameters: "
        f"tdb={tdb:.1f}°C, tr={tr:.1f}°C, t_running_mean={t_running_mean:.1f}°C, v={v:.2f}m/s"
    )
    
    # Perform calculation
    try:
        result = _ashrae_55_adaptive_calculation(tdb, tr, t_running_mean, v)
        
        ashrae_result = AdaptiveAshraeResult(
            tmp_cmf=float(result[0]),
            tmp_cmf_80_low=float(result[1]),
            tmp_cmf_80_up=float(result[2]),
            tmp_cmf_90_low=float(result[3]),
            tmp_cmf_90_up=float(result[4]),
            acceptability_80=bool(result[5]),
            acceptability_90=bool(result[6])
        )
        
        # Log results
        _LOGGER.debug(
            f"{device_prefix}ASHRAE 55 results: "
            f"comfort_temp={ashrae_result.tmp_cmf:.1f}°C, "
            f"80%_range=[{ashrae_result.tmp_cmf_80_low:.1f}-{ashrae_result.tmp_cmf_80_up:.1f}]°C, "
            f"90%_range=[{ashrae_result.tmp_cmf_90_low:.1f}-{ashrae_result.tmp_cmf_90_up:.1f}]°C, "
            f"acceptable_80={ashrae_result.acceptability_80}, "
            f"acceptable_90={ashrae_result.acceptability_90}"
        )
        
        return ashrae_result
        
    except Exception as e:
        error_msg = f"ASHRAE 55 adaptive comfort calculation failed: {e}"
        _LOGGER.error(f"{device_prefix}{error_msg}")
        raise RuntimeError(error_msg) from e

def adaptive_ashrae_80(
    tdb: float,
    tr: float, 
    t_running_mean: float,
    v: float = 0.1,
    device_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Simplified ASHRAE adaptive comfort for 80% acceptability.
    Returns dict format for backward compatibility.
    
    Args:
        tdb: Dry bulb air temperature [°C]
        tr: Mean radiant temperature [°C]
        t_running_mean: Prevailing mean outdoor temperature [°C]
        v: Air velocity [m/s], default 0.1
        device_name: Optional device name for logging
        
    Returns:
        Dict with comfort temperature and 80% acceptability data
    """
    result = adaptive_ashrae(tdb, tr, t_running_mean, v, device_name=device_name)
    
    return {
        "tmp_cmf": result.tmp_cmf,
        "tmp_cmf_80_low": result.tmp_cmf_80_low,
        "tmp_cmf_80_up": result.tmp_cmf_80_up,
        "acceptability_80": result.acceptability_80
    }

def adaptive_ashrae_90(
    tdb: float,
    tr: float,
    t_running_mean: float, 
    v: float = 0.1,
    device_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Simplified ASHRAE adaptive comfort for 90% acceptability.
    Returns dict format for backward compatibility.
    
    Args:
        tdb: Dry bulb air temperature [°C]
        tr: Mean radiant temperature [°C]
        t_running_mean: Prevailing mean outdoor temperature [°C]
        v: Air velocity [m/s], default 0.1
        device_name: Optional device name for logging
        
    Returns:
        Dict with comfort temperature and 90% acceptability data
    """
    result = adaptive_ashrae(tdb, tr, t_running_mean, v, device_name=device_name)
    
    return {
        "tmp_cmf": result.tmp_cmf,
        "tmp_cmf_90_low": result.tmp_cmf_90_low,
        "tmp_cmf_90_up": result.tmp_cmf_90_up,
        "acceptability_90": result.acceptability_90
    }

# Version info for compatibility
__version__ = "2.10.0-patched-ha-pure"

# Log successful import
_LOGGER.info("pythermalcomfort_patched loaded (pure Python - no external dependencies)")
