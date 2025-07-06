from typing import Literal, Dict, Any, Optional
from .pythermalcomfort_patched import adaptive_ashrae

HVACMode = Literal["cool", "heat", "fan_only", "dry", "humidify", "off"]
FanMode = Literal["low", "mid", "high", "very_high", "off"]
ComfortCategory = Literal["I", "II", "III"]

CATEGORY_TOLERANCE = {
    "I": 1.0,
    "II": 2.5,
    "III": 3.5,
}

AIR_VELOCITY_MAP = {
    "low": 0.15,
    "mid": 0.30,
    "high": 0.45,
    "very_high": 0.6,
}

ASHRAE_55_TEMP_MIN = 10.0
ASHRAE_55_TEMP_MAX = 33.5

def calculate_hvac_and_fan(
    indoor_temp: float,
    outdoor_temp: float,
    min_temp: float,
    max_temp: float,
    season: str,
    category: ComfortCategory = "II",
    air_velocity: FanMode = "low",
    mean_radiant_temp: Optional[float] = None,
    indoor_humidity: Optional[float] = None,
    outdoor_humidity: Optional[float] = None,
    running_mean_outdoor_temp: Optional[float] = None,
    energy_save_mode: bool = True,
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

    tolerance = CATEGORY_TOLERANCE.get(category, 2.5)

    # Calculate ASHRAE adaptive comfort
    ashrae_result = adaptive_ashrae(
        tdb=indoor_temp,
        tr=mean_radiant_temp or indoor_temp,
        t_running_mean=running_mean_outdoor_temp or outdoor_temp,
        v=AIR_VELOCITY_MAP.get(air_velocity, 0.1)
    )

    comfort_temp = ashrae_result.tmp_cmf
    fan = "off"
    hvac_mode = "off"

    # Summer logic with dry mode
    if season == "summer":
        if indoor_humidity is not None and indoor_humidity > 70:
            hvac_mode = "dry"
            fan = "low"
        elif indoor_temp < comfort_temp:
            if energy_save_mode:
                hvac_mode = "off"
                fan = "off"
            else:
                hvac_mode = "cool"
                fan = "low"
        else:
            hvac_mode = "cool"
            if indoor_temp < (max_temp - (tolerance / 2)):
                fan = "low"
            elif indoor_temp > (max_temp - (tolerance / 2)):
                fan = "mid"
            if indoor_temp > max_temp:
                fan = "high"
            if indoor_temp > outdoor_temp:
                fan = "very_high"

    # Winter logic with humidify mode
    elif season == "winter":
        if indoor_humidity is not None and indoor_humidity < 30:
            hvac_mode = "humidify"
            fan = "low"
        elif indoor_temp < comfort_temp:
            hvac_mode = "heat"
            if indoor_temp < min_temp:
                fan = "high"
            elif indoor_temp < (min_temp + (tolerance / 2)):
                fan = "mid"
            else:
                fan = "low"
        elif indoor_temp > comfort_temp:
            hvac_mode = "off"
            fan = "off"
        else:
            hvac_mode = "off"
            fan = "off"

    # Spring and Autumn logic with dry mode
    elif season in ["spring", "autumn"]:
        if indoor_humidity is not None and indoor_humidity > 70:
            hvac_mode = "dry"
            fan = "low"
        elif indoor_temp < min_temp:
            hvac_mode = "heat"
            fan = "mid"
        elif indoor_temp > max_temp:
            hvac_mode = "cool"  # ou fan_only se preferir economia
            fan = "high"
        else:
            hvac_mode = "off"
            fan = "off"

    return {
        "comfort_temp": comfort_temp,
        "hvac_mode": hvac_mode,
        "fan": fan,
        "ashrae_compliant": ashrae_result.acceptability_80,
        "comfort_min_ashrae": ashrae_result.tmp_cmf_80_low,
        "comfort_max_ashrae": ashrae_result.tmp_cmf_80_up,
        "indoor_humidity": indoor_humidity,
        "outdoor_humidity": outdoor_humidity,
        "humidity_adjustment": 0.0,  # placeholder para futuras integrações PMV/PPD
    }