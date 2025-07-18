import math
from typing import Literal, Dict, Any, Optional
from .pythermalcomfort_patched import adaptive_ashrae
import logging

_LOGGER = logging.getLogger(__name__)
HVACMode = Literal["cool", "heat", "fan_only", "dry", "off"]
FanMode = Literal["low", "mid", "high", "highest", "off"]
ComfortCategory = Literal["I", "II"]

CATEGORY_TOLERANCE = {
    "I": 2.5,
    "II": 3.5,
}

AIR_VELOCITY_MAP = {
    "off": 0.0,
    "low": 0.15,
    "mid": 0.30,
    "high": 0.45,
    "highest": 0.60,
}

# ASHRAE 55 temperature limits
# These are the minimum and maximum temperatures defined by ASHRAE 55 for adaptive comfort
# They are used to clamp outdoor temperatures to ensure they fall within the acceptable range.
# The values are based on the ASHRAE 55 standard for adaptive thermal comfort.
# Reference: https://www.ashrae.org/technical-resources/bookstore/ashrae-55-2020
ASHRAE_55_TEMP_MIN = 10.0
ASHRAE_55_TEMP_MAX = 33.5    

def calculate_hvac_and_fan(
    indoor_temp: float,
    outdoor_temp: float,
    min_temp: float,
    max_temp: float,
    season: str,
    category: ComfortCategory = "I",
    air_velocity: FanMode = "low",
    indoor_humidity: Optional[float] = None,
    outdoor_humidity: Optional[float] = None,
    running_mean_outdoor_temp: Optional[float] = None,
    running_mean_indoor_temp: Optional[float] = None,
    energy_save_mode: bool = True,
    device_name: str = "Adaptive Climate",
    override_temperature: float = 0,
    aggressive_cooling_threshold: Optional[float] = 2.0,
    aggressive_heating_threshold: Optional[float] = 2.0,
) -> Dict[str, Any]:

    """
    Calculate HVAC mode and fan speed based on season, ASHRAE comfort, and humidity.
    Returns:
        dict with comfort_temp, hvac_mode, fan, compliance and limits
    """

    # Clamp outdoor_temp to ASHRAE 55 valid range
    outdoor_temp = max(ASHRAE_55_TEMP_MIN, min(outdoor_temp, ASHRAE_55_TEMP_MAX))

    # Clamp humidity values between 0-100% for safety
    if indoor_humidity is not None:
        indoor_humidity = max(0, min(indoor_humidity, 100))
    if outdoor_humidity is not None:
        outdoor_humidity = max(0, min(outdoor_humidity, 100))

    # Calculate ASHRAE adaptive comfort
    # Use indoor_temp as tdb, mean_radiant_temp as tr, 
    # and running_mean_outdoor_temp as t_running_mean.
    ashrae_result = adaptive_ashrae(
        tdb=indoor_temp,
        tr=running_mean_indoor_temp or indoor_temp,
        t_running_mean=running_mean_outdoor_temp or outdoor_temp,
        v=AIR_VELOCITY_MAP.get(air_velocity, 0.1)
    )

    fan = "off"
    hvac_mode = "off"

    if category == "I":
        # For category I, use the 90% acceptability limits
        comfort_temp = ashrae_result.tmp_cmf + override_temperature
        min_comfort_temp = ashrae_result.tmp_cmf_90_low + override_temperature
        max_comfort_temp = ashrae_result.tmp_cmf_90_up + override_temperature
    else:
        # For category II, use the 80% acceptability limits
        comfort_temp = ashrae_result.tmp_cmf + override_temperature
        min_comfort_temp = ashrae_result.tmp_cmf_80_low + override_temperature
        max_comfort_temp = ashrae_result.tmp_cmf_80_up + override_temperature

    # Preserve ASHRAE 55 result
    original_comfort_temp = comfort_temp

    # Adaptive adjustment (based on indoor vs. outdoor delta)
    delta_indoor_outdoor = abs(indoor_temp - outdoor_temp)

    if delta_indoor_outdoor >= 5:
        comfort_temp = math.ceil(comfort_temp)
    elif delta_indoor_outdoor <= 1:
        comfort_temp = math.floor(comfort_temp)

    # Log adjustment
    _LOGGER.debug(
        f"[{device_name}] ASHRAE comfort_temp={original_comfort_temp:.2f}, "
        f"adaptive_adjusted_temp={comfort_temp:.2f}, "
        f"delta_indoor_outdoor={delta_indoor_outdoor:.2f}"
    )

    # Define dynamic thresholds for temperature zones based on season
    if season == "summer":
        cool_zone_threshold = 0.3
        warm_zone_threshold = 0.7
    elif season == "winter":
        cool_zone_threshold = 0.7
        warm_zone_threshold = 0.3
    else:  # spring or autumn
        cool_zone_threshold = 0.5
        warm_zone_threshold = 0.5

    # Calculate midpoints for temperature ranges
    mid_min = min_comfort_temp + (comfort_temp - min_comfort_temp) * cool_zone_threshold
    mid_max = comfort_temp + (max_comfort_temp - comfort_temp) * warm_zone_threshold

    # Define temperature ranges
    below_min = indoor_temp <= min_comfort_temp
    slightly_cool = min_comfort_temp < indoor_temp <= mid_min
    comfortably_cool = mid_min < indoor_temp < comfort_temp
    comfortably_warm = comfort_temp <= indoor_temp <= mid_max
    slightly_warm = mid_max < indoor_temp <= max_comfort_temp
    above_max = indoor_temp > max_comfort_temp
    
    # Clamp comfort_temp to user min/max config
    comfort_temp = max(min_temp, min(comfort_temp, max_temp))


    # Summer logic
    if season == "summer":
        if not energy_save_mode:
            if below_min:
                hvac_mode = "fan_only"
                fan = "low"
            elif slightly_cool:
                hvac_mode = "fan_only"
                fan = "mid"
            elif comfortably_cool:
                hvac_mode = "fan_only"
                fan = "high"
            elif comfortably_warm:
                hvac_mode = "cool"
                fan = "low"
            elif slightly_warm:
                hvac_mode = "cool"
                fan = "mid"
            elif above_max:
                if indoor_temp >= (max_comfort_temp + aggressive_cooling_threshold):
                    hvac_mode = "cool"
                    fan = "highest"
                else:
                    hvac_mode = "cool"
                    fan = "high"
        else:
            if below_min:
                hvac_mode = "off"
                fan = "off"
            elif slightly_cool:
                hvac_mode = "fan_only"
                fan = "low"
            elif comfortably_cool:
                hvac_mode = "fan_only"
                fan = "mid"
            elif comfortably_warm:
                hvac_mode = "fan_only"
                fan = "max"
            elif slightly_warm:
                hvac_mode = "cool"
                fan = "low"
            elif above_max:
                if indoor_temp >= (max_comfort_temp + aggressive_cooling_threshold):
                    hvac_mode = "cool"
                    fan = "high"
                else:
                    hvac_mode = "cool"
                    fan = "mid"

    # Winter logic
    elif season == "winter":
        if energy_save_mode:
            if above_max or slightly_warm or comfortably_warm:
                hvac_mode = "off"
                fan = "off"
            elif comfortably_cool:
                hvac_mode = "heat"
                fan = "low"
            elif slightly_cool:
                hvac_mode = "heat"
                fan = "mid"
            elif below_min and indoor_temp < (min_comfort_temp - aggressive_heating_threshold):
                hvac_mode = "heat"
                fan = "highest"
            elif below_min:
                hvac_mode = "heat"
                fan = "high"

        else:
            if below_min and indoor_temp < (min_comfort_temp - aggressive_heating_threshold):
                hvac_mode = "heat"
                fan = "highest"
            elif below_min and indoor_temp < (min_comfort_temp - 1):
                hvac_mode = "heat"
                fan = "high"
            elif below_min:
                hvac_mode = "heat"
                fan = "mid"
            elif slightly_cool:
                hvac_mode = "heat"
                fan = "low"
            elif comfortably_cool:
                hvac_mode = "off"
                fan = "off"
            elif comfortably_warm or slightly_warm or above_max:
                hvac_mode = "off"
                fan = "off"

    # Spring and Autumn logic with dry mode
    elif season in ["spring", "autumn"]:
        if not energy_save_mode:
            if below_min:
                hvac_mode = "heat"
                fan = "low"
            elif slightly_cool:
                hvac_mode = "heat"
                fan = "mid"
            elif comfortably_cool:
                hvac_mode = "fan_only"
                fan = "low"
            elif comfortably_warm:
                hvac_mode = "fan_only"
                fan = "low"
            elif slightly_warm:
                hvac_mode = "cool"
                fan = "mid"
            elif above_max:
                hvac_mode = "cool"
                fan = "high"
        else:
            if below_min:
                hvac_mode = "off"
                fan = "off"
            elif slightly_cool:
                hvac_mode = "heat"
                fan = "low"
            elif comfortably_cool or comfortably_warm:
                hvac_mode = "off"
                fan = "off"
            elif slightly_warm:
                hvac_mode = "cool"
                fan = "low"
            elif above_max:
                hvac_mode = "cool"
                fan = "mid"

    _LOGGER.debug(f"[{device_name}] Temperature ranges: "
                  f"below_min={below_min}, "
                  f"slightly_cool={slightly_cool}, "
                  f"comfortably_cool={comfortably_cool}, "
                  f"comfortably_warm={comfortably_warm}, "
                  f"slightly_warm={slightly_warm}, "
                  f"above_max={above_max}")

    if category == "I":
        return {
            "season": season,
            "category": category,
            "comfort_temp": comfort_temp,
            "hvac_mode": hvac_mode,
            "fan_mode": fan,
            "ashrae_compliant": ashrae_result.acceptability_90,
            "comfort_min_ashrae": round(ashrae_result.tmp_cmf_90_low, 2),
            "comfort_max_ashrae": round(ashrae_result.tmp_cmf_90_up, 2),
            "running_mean_indoor_temp": running_mean_indoor_temp,
            "running_mean_outdoor_temp": running_mean_outdoor_temp,
            "humidity_adjustment": 0.0,  # placeholder para futuras integrações PMV/PPD
        }
    else:
        return {
            "season": season,
            "category": category,
            "comfort_temp": comfort_temp,
            "hvac_mode": hvac_mode,
            "fan_mode": fan,
            "ashrae_compliant": ashrae_result.acceptability_80,
            "comfort_min_ashrae": round(ashrae_result.tmp_cmf_80_low, 2),
            "comfort_max_ashrae": round(ashrae_result.tmp_cmf_80_up, 2),
            "running_mean_indoor_temp": running_mean_indoor_temp,
            "running_mean_outdoor_temp": running_mean_outdoor_temp,
            "humidity_adjustment": 0.0,  # placeholder para futuras integrações PMV/PPD
        }

