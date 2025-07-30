import math
from typing import Literal, Dict, Any, Optional, Tuple
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

ASHRAE_55_TEMP_MIN = 10.0
ASHRAE_55_TEMP_MAX = 33.5

# Season configuration for temperature ranges
SEASON_THRESHOLDS = {
    "summer": {"cool": 0.3, "warm": 0.7},
    "winter": {"cool": 0.7, "warm": 0.3},
    "spring": {"cool": 0.5, "warm": 0.5},
    "autumn": {"cool": 0.5, "warm": 0.5},
}


class ComfortCalculator:
    """Calculate comfort temperatures using ASHRAE 55-2020 standard."""

    def __init__(self) -> None:
        """Initialize the calculator."""
        pass

    def _bounded_temp(self, target: float, min_t: float, max_t: float) -> float:
        """Bound temperature between min and max values."""
        return max(min_t, min(target, max_t))

    def _limit_fan_speed(self, fan_speed: str, max_fan_speed: str, min_fan_speed: str) -> str:
        """Limit fan speed based on user preferences."""
        fan_speed_order = ["low", "mid", "high", "highest"]
        max_index = fan_speed_order.index(max_fan_speed)
        min_index = fan_speed_order.index(min_fan_speed)
        
        current_index = fan_speed_order.index(fan_speed) if fan_speed in fan_speed_order else 0
        limited_index = max(min_index, min(current_index, max_index))
        return fan_speed_order[limited_index]

    def calculate_ashrae(
        self, 
        indoor_temp: float, 
        outdoor_temp: float, 
        air_velocity: str, 
        running_mean_temp: Optional[float],
        device_name: Optional[str] = None
    ) -> Any:
        """Calculate ASHRAE 55 adaptive comfort parameters."""
        return adaptive_ashrae(
            tdb=indoor_temp,
            tr=indoor_temp,
            t_running_mean=running_mean_temp or outdoor_temp,
            v=AIR_VELOCITY_MAP.get(air_velocity, 0.1),
            device_name=device_name
        )

    def _extract_comfort_limits(
        self, 
        ashrae_result: Any, 
        category: ComfortCategory
    ) -> Tuple[float, float, float]:
        """Extract comfort temperature limits based on category."""
        if category == "I":
            return (
                ashrae_result.tmp_cmf,
                ashrae_result.tmp_cmf_90_low,
                ashrae_result.tmp_cmf_90_up,
            )
        else:
            return (
                ashrae_result.tmp_cmf,
                ashrae_result.tmp_cmf_80_low,
                ashrae_result.tmp_cmf_80_up,
            )

    def calculate_hvac_and_fan(
        self,
        indoor_temp: float,
        outdoor_temp: float,
        min_temp: float,
        max_temp: float,
        season: str,
        category: ComfortCategory = "I",
        air_velocity: FanMode = "low",
        indoor_humidity: Optional[float] = None,
        outdoor_humidity: Optional[float] = None,
        running_mean_temp: Optional[float] = None,
        energy_save_mode: bool = True,
        device_name: str = "Adaptive Climate",
        aggressive_cooling_threshold: Optional[float] = 2.0,
        aggressive_heating_threshold: Optional[float] = 2.0,
        # New HVAC and Fan Control parameters
        enable_fan_mode: bool = True,
        enable_cool_mode: bool = True,
        enable_heat_mode: bool = True,
        enable_dry_mode: bool = True,
        max_fan_speed: str = "high",
        min_fan_speed: str = "low",
        # Temperature override parameter
        override_temperature: float = 0.0,
    ) -> Dict[str, Any]:
        """Calculate HVAC and fan mode based on comfort parameters."""
        
        _LOGGER.debug(f"[{device_name}] Starting comfort calculation with inputs:")
        _LOGGER.debug(f"[{device_name}]   - Indoor temp: {indoor_temp:.2f}°C")
        _LOGGER.debug(f"[{device_name}]   - Outdoor temp: {outdoor_temp:.2f}°C")
        _LOGGER.debug(f"[{device_name}]   - Min temp: {min_temp:.2f}°C")
        _LOGGER.debug(f"[{device_name}]   - Max temp: {max_temp:.2f}°C")
        _LOGGER.debug(f"[{device_name}]   - Season: {season}")
        _LOGGER.debug(f"[{device_name}]   - Category: {category}")
        _LOGGER.debug(f"[{device_name}]   - Running mean temp: {running_mean_temp:.2f}°C" if running_mean_temp is not None else f"[{device_name}]   - Running mean temp: None")
        
        # Validate and clamp outdoor temperature
        outdoor_temp = max(ASHRAE_55_TEMP_MIN, min(outdoor_temp, ASHRAE_55_TEMP_MAX))

        # Validate humidity values
        if indoor_humidity is not None:
            indoor_humidity = max(0, min(indoor_humidity, 100))
        if outdoor_humidity is not None:
            outdoor_humidity = max(0, min(outdoor_humidity, 100))

        # Calculate ASHRAE comfort parameters
        ashrae_result = self.calculate_ashrae(
            indoor_temp,
            outdoor_temp,
            air_velocity,
            running_mean_temp,
            device_name=device_name,
        )

        comfort_temp, min_comfort_temp, max_comfort_temp = self._extract_comfort_limits(ashrae_result, category)

        # Determine temperature ranges
        ranges = self._determine_temperature_ranges(
            indoor_temp, min_comfort_temp, comfort_temp, max_comfort_temp, season
        )

        # Determine HVAC and fan mode
        hvac_mode, fan, temperature = self._determine_hvac_and_fan_mode(
            ranges,
            season,
            energy_save_mode,
            indoor_temp,
            outdoor_temp,
            comfort_temp,
            min_comfort_temp,
            max_comfort_temp,
            min_temp,
            max_temp,
            aggressive_cooling_threshold,
            aggressive_heating_threshold,
            enable_fan_mode,
            enable_cool_mode,
            enable_heat_mode,
            enable_dry_mode,
            max_fan_speed,
            min_fan_speed,
            override_temperature,
        )

        # Apply temperature override to the final temperature
        if override_temperature != 0.0:
            original_temperature = temperature
            temperature += override_temperature
            # Ensure temperature stays within bounds
            temperature = max(min_temp, min(temperature, max_temp))
            _LOGGER.debug(f"[{device_name}] Applied temperature override: {original_temperature:.2f}°C + {override_temperature:.2f}°C = {temperature:.2f}°C")

        _LOGGER.debug(f"[{device_name}] Temperature ranges: "
                      f"below_min={ranges['below_min']}, "
                      f"slightly_cool={ranges['slightly_cool']}, "
                      f"comfortably_cool={ranges['comfortably_cool']}, "
                      f"comfortably_warm={ranges['comfortably_warm']}, "
                      f"slightly_warm={ranges['slightly_warm']}, "
                      f"above_max={ranges['above_max']}")

        _LOGGER.debug(f"[{device_name}] Calculated comfort parameters:")
        _LOGGER.debug(f"[{device_name}]   - Comfort temp: {comfort_temp:.2f}°C")
        _LOGGER.debug(f"[{device_name}]   - Min comfort temp: {min_comfort_temp:.2f}°C")
        _LOGGER.debug(f"[{device_name}]   - Max comfort temp: {max_comfort_temp:.2f}°C")
        _LOGGER.debug(f"[{device_name}]   - Target temperature: {temperature:.2f}°C")
        _LOGGER.debug(f"[{device_name}]   - HVAC mode: {hvac_mode}")
        _LOGGER.debug(f"[{device_name}]   - Fan mode: {fan}")

        result = {
            "season": season,
            "category": category,
            "comfort_temp": round(max(min_temp, min(comfort_temp, max_temp)), 2),  # 2 decimal places for logs
            "hvac_mode": hvac_mode,
            "fan_mode": fan,
            "target_temp": round(temperature, 2),  # 2 decimal places for logs
            "ashrae_compliant": ashrae_result.acceptability_90 if category == "I" else ashrae_result.acceptability_80,
            "comfort_min_ashrae": round(min_comfort_temp, 2),  # 2 decimal places for logs
            "comfort_max_ashrae": round(max_comfort_temp, 2),  # 2 decimal places for logs
            "tr": round(indoor_temp, 2),  # 2 decimal places for logs
            "running_mean_temp": round(running_mean_temp, 2) if running_mean_temp is not None else None,  # 2 decimal places for logs
            "humidity_adjustment": 0.0,
        }

        return result

    def calculate(self, **kwargs) -> Dict[str, Any]:
        """Main calculation method - alias for calculate_hvac_and_fan."""
        return self.calculate_hvac_and_fan(**kwargs)

    def _determine_temperature_ranges(
        self, 
        temperature_for_calc: float, 
        min_comfort_temp: float, 
        comfort_temp: float, 
        max_comfort_temp: float, 
        season: str
    ) -> Dict[str, bool]:
        """Determine temperature ranges based on season and comfort parameters."""
        thresholds = SEASON_THRESHOLDS.get(season, SEASON_THRESHOLDS["spring"])
        
        cool_zone_threshold = thresholds["cool"]
        warm_zone_threshold = thresholds["warm"]

        mid_min = min_comfort_temp + (comfort_temp - min_comfort_temp) * cool_zone_threshold
        mid_max = comfort_temp + (max_comfort_temp - comfort_temp) * warm_zone_threshold

        return {
            "below_min": temperature_for_calc <= min_comfort_temp,
            "slightly_cool": min_comfort_temp < temperature_for_calc <= mid_min,
            "comfortably_cool": mid_min < temperature_for_calc < comfort_temp,
            "comfortably_warm": comfort_temp <= temperature_for_calc <= mid_max,
            "slightly_warm": mid_max < temperature_for_calc <= max_comfort_temp,
            "above_max": temperature_for_calc > max_comfort_temp,
        }

    def _determine_hvac_and_fan_mode(
        self,
        ranges: Dict[str, bool],
        season: str,
        energy_save_mode: bool,
        indoor_temp: float,
        outdoor_temp: float,
        comfort_temp: float,
        min_comfort_temp: float,
        max_comfort_temp: float,
        min_temp: float,
        max_temp: float,
        aggressive_cooling_threshold: float,
        aggressive_heating_threshold: float,
        enable_fan_mode: bool,
        enable_cool_mode: bool,
        enable_heat_mode: bool,
        enable_dry_mode: bool,
        max_fan_speed: str,
        min_fan_speed: str,
        override_temperature: float,
    ) -> Tuple[str, str, float]:
        """Determine HVAC mode, fan mode, and target temperature."""
        
        hvac_mode = "off"
        fan = "off"
        temperature = comfort_temp

        # Check for thermal equilibrium - only turn off if very close to comfort temp
        equilibrium_delta = 0.5  # Reduced from 1.0 to be less restrictive
        
        # Season-specific equilibrium logic
        if season == "summer":
            # In summer: turn off AC when both indoor and outdoor are below comfort temp
            if (indoor_temp < comfort_temp and outdoor_temp < comfort_temp):
                _LOGGER.info(
                    f"Summer thermal equilibrium detected - temperatures below comfort "
                    f"(indoor={indoor_temp}°C, outdoor={outdoor_temp}°C, comfort={comfort_temp}°C). "
                    f"Turning HVAC off."
                )
                return "off", "off", comfort_temp
        elif season == "winter":
            # In winter: turn off AC when both indoor and outdoor are above comfort temp
            if (indoor_temp > comfort_temp and outdoor_temp > comfort_temp):
                _LOGGER.info(
                    f"Winter thermal equilibrium detected - temperatures above comfort "
                    f"(indoor={indoor_temp}°C, outdoor={outdoor_temp}°C, comfort={comfort_temp}°C). "
                    f"Turning HVAC off."
                )
                return "off", "off", comfort_temp
        else:  # spring or autumn
            # In transition seasons: use original logic for general equilibrium
            if (
                -equilibrium_delta <= (indoor_temp - outdoor_temp) <= equilibrium_delta and
                -equilibrium_delta <= (indoor_temp - comfort_temp) <= equilibrium_delta
            ):
                _LOGGER.info(
                    f"Transition season thermal equilibrium detected "
                    f"(indoor={indoor_temp}°C, comfort={comfort_temp}°C, outdoor={outdoor_temp}°C). "
                    f"Turning HVAC off."
                )
                return "off", "off", comfort_temp

        # Determine mode based on season
        if season == "summer":
            hvac_mode, fan, temperature = self._get_summer_mode(
                ranges, energy_save_mode, indoor_temp, comfort_temp, min_temp, max_temp,
                max_comfort_temp, aggressive_cooling_threshold,
                enable_fan_mode, enable_cool_mode, enable_dry_mode, max_fan_speed, min_fan_speed, override_temperature
            )
        elif season == "winter":
            hvac_mode, fan, temperature = self._get_winter_mode(
                ranges, energy_save_mode, indoor_temp, comfort_temp, min_temp, max_temp,
                min_comfort_temp, aggressive_heating_threshold,
                enable_fan_mode, enable_heat_mode, enable_dry_mode, max_fan_speed, min_fan_speed, override_temperature
            )
        else:  # spring or autumn
            hvac_mode, fan, temperature = self._get_transition_mode(
                ranges, energy_save_mode, comfort_temp, min_temp, max_temp,
                enable_fan_mode, enable_cool_mode, enable_heat_mode, enable_dry_mode, max_fan_speed, min_fan_speed, override_temperature
            )

        return hvac_mode, fan, temperature

    def _get_summer_mode(
        self,
        ranges: Dict[str, bool],
        energy_save_mode: bool,
        indoor_temp: float,
        comfort_temp: float,
        min_temp: float,
        max_temp: float,
        max_comfort_temp: float,
        aggressive_cooling_threshold: float,
        enable_fan_mode: bool,
        enable_cool_mode: bool,
        enable_dry_mode: bool,
        max_fan_speed: str,
        min_fan_speed: str,
        override_temperature: float,
    ) -> Tuple[str, str, float]:
        """Determine HVAC mode for summer season."""
        
        if not energy_save_mode:
            if ranges["below_min"]:
                return "off", "off", comfort_temp
            elif ranges["slightly_cool"]:
                return "fan_only" if enable_fan_mode else "off", self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), comfort_temp
            elif ranges["comfortably_cool"]:
                return "cool" if enable_cool_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("low", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp - 1, min_temp, max_temp)
            elif ranges["comfortably_warm"]:
                return "cool" if enable_cool_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp - 1, min_temp, max_temp)
            elif ranges["slightly_warm"]:
                return "cool" if enable_cool_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("high", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp - 2, min_temp, max_temp)
            elif ranges["above_max"]:
                if indoor_temp >= (max_comfort_temp + aggressive_cooling_threshold):
                    return "cool" if enable_cool_mode else ("dry" if enable_dry_mode else "off"), self._limit_fan_speed("highest", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp - 3, min_temp, max_temp)
                else:
                    return "cool" if enable_cool_mode else ("dry" if enable_dry_mode else "off"), self._limit_fan_speed("high", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp - 3, min_temp, max_temp)
        else:
            if ranges["below_min"]:
                return "off", "off", comfort_temp
            elif ranges["slightly_cool"]:
                return "fan_only" if enable_fan_mode else "off", self._limit_fan_speed("low", max_fan_speed, min_fan_speed), comfort_temp
            elif ranges["comfortably_cool"]:
                return "fan_only" if enable_fan_mode else "off", self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), comfort_temp
            elif ranges["comfortably_warm"]:
                return "cool" if enable_cool_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("low", max_fan_speed, min_fan_speed), comfort_temp
            elif ranges["slightly_warm"]:
                return "cool" if enable_cool_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), comfort_temp
            elif ranges["above_max"]:
                if indoor_temp >= (max_comfort_temp + aggressive_cooling_threshold):
                    return "cool" if enable_cool_mode else ("dry" if enable_dry_mode else "off"), self._limit_fan_speed("high", max_fan_speed, min_fan_speed), comfort_temp
                else:
                    return "cool" if enable_cool_mode else ("dry" if enable_dry_mode else "off"), self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), comfort_temp

        return "off", "off", comfort_temp

    def _get_winter_mode(
        self,
        ranges: Dict[str, bool],
        energy_save_mode: bool,
        indoor_temp: float,
        comfort_temp: float,
        min_temp: float,
        max_temp: float,
        min_comfort_temp: float,
        aggressive_heating_threshold: float,
        enable_fan_mode: bool,
        enable_heat_mode: bool,
        enable_dry_mode: bool,
        max_fan_speed: str,
        min_fan_speed: str,
        override_temperature: float,
    ) -> Tuple[str, str, float]:
        """Determine HVAC mode for winter season."""
        
        if energy_save_mode:
            if ranges["above_max"] or ranges["slightly_warm"] or ranges["comfortably_warm"]:
                return "off", "off", comfort_temp
            elif ranges["comfortably_cool"]:
                return "heat" if enable_heat_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("low", max_fan_speed, min_fan_speed), comfort_temp
            elif ranges["slightly_cool"]:
                return "heat" if enable_heat_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), comfort_temp
            elif ranges["below_min"]:
                if indoor_temp <= (min_comfort_temp - aggressive_heating_threshold):
                    return "heat" if enable_heat_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("high", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp + 2, min_temp, max_temp)
                else:
                    return "heat" if enable_heat_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp + 1, min_temp, max_temp)
        else:
            if ranges["above_max"] or ranges["slightly_warm"]:
                return "off", "off", comfort_temp
            elif ranges["comfortably_warm"]:
                return "heat" if enable_heat_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("low", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp + 1, min_temp, max_temp)
            elif ranges["comfortably_cool"]:
                return "heat" if enable_heat_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp + 1, min_temp, max_temp)
            elif ranges["slightly_cool"]:
                return "heat" if enable_heat_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("high", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp + 2, min_temp, max_temp)
            elif ranges["below_min"]:
                if indoor_temp <= (min_comfort_temp - aggressive_heating_threshold):
                    return "heat" if enable_heat_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("highest", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp + 3, min_temp, max_temp)
                else:
                    return "heat" if enable_heat_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("high", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp + 3, min_temp, max_temp)

        return "off", "off", comfort_temp

    def _get_transition_mode(
        self,
        ranges: Dict[str, bool],
        energy_save_mode: bool,
        comfort_temp: float,
        min_temp: float,
        max_temp: float,
        enable_fan_mode: bool,
        enable_cool_mode: bool,
        enable_heat_mode: bool,
        enable_dry_mode: bool,
        max_fan_speed: str,
        min_fan_speed: str,
        override_temperature: float,
    ) -> Tuple[str, str, float]:
        """Determine HVAC mode for spring/autumn seasons."""
        
        if energy_save_mode:
            if ranges["comfortably_cool"] or ranges["comfortably_warm"]:
                return "fan_only" if enable_fan_mode else "off", self._limit_fan_speed("low", max_fan_speed, min_fan_speed), comfort_temp
            elif ranges["slightly_cool"]:
                return "heat" if enable_heat_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("low", max_fan_speed, min_fan_speed), comfort_temp
            elif ranges["slightly_warm"]:
                return "cool" if enable_cool_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("low", max_fan_speed, min_fan_speed), comfort_temp
            elif ranges["below_min"]:
                return "heat" if enable_heat_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), comfort_temp
            elif ranges["above_max"]:
                return "cool" if enable_cool_mode else ("dry" if enable_dry_mode else "off"), self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), comfort_temp
        else:
            if ranges["comfortably_cool"] or ranges["comfortably_warm"]:
                return "fan_only" if enable_fan_mode else "off", self._limit_fan_speed("low", max_fan_speed, min_fan_speed), comfort_temp
            elif ranges["slightly_cool"]:
                return "heat" if enable_heat_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp + 1, min_temp, max_temp)
            elif ranges["slightly_warm"]:
                return "cool" if enable_cool_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp - 1, min_temp, max_temp)
            elif ranges["below_min"]:
                return "heat" if enable_heat_mode else ("fan_only" if enable_fan_mode else "off"), self._limit_fan_speed("high", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp + 2, min_temp, max_temp)
            elif ranges["above_max"]:
                return "cool" if enable_cool_mode else ("dry" if enable_dry_mode else "off"), self._limit_fan_speed("high", max_fan_speed, min_fan_speed), self._bounded_temp(comfort_temp - 2, min_temp, max_temp)

        return "off", "off", comfort_temp