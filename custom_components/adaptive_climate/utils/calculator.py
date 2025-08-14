from __future__ import annotations

import logging
from typing import Any, Dict, Literal, Optional, Tuple

from .ashrae55 import adaptive_ashrae

_LOGGER = logging.getLogger(__name__)
HVACMode = Literal["cool", "heat", "fan_only", "dry", "off"]
FanMode = Literal["low", "mid", "high", "highest", "off"]
ComfortCategory = Literal["I", "II"]

CATEGORY_TOLERANCE = {"I": 2.5, "II": 3.5}

AIR_VELOCITY_MAP = {
    "off": 0.0,
    "low": 0.15,
    "mid": 0.30,
    "high": 0.45,
    "highest": 0.60,
}

ASHRAE_55_TEMP_MIN = 10.0
ASHRAE_55_TEMP_MAX = 33.5

SEASON_THRESHOLDS = {
    "summer": {"cool": 0.3, "warm": 0.7},
    "winter": {"cool": 0.7, "warm": 0.3},
    "spring": {"cool": 0.5, "warm": 0.5},
    "autumn": {"cool": 0.5, "warm": 0.5},
}


class ComfortCalculator:
    """Calculate comfort temperatures using ASHRAE 55-2020 standard."""

    def _bounded_temp(self, target: float, min_t: float, max_t: float) -> float:
        return max(min_t, min(target, max_t))

    def _limit_fan_speed(self, fan_speed: str, max_fan_speed: str, min_fan_speed: str) -> str:
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
        device_name: Optional[str] = None,
    ) -> Any:
        return adaptive_ashrae(
            tdb=indoor_temp,
            tr=indoor_temp,
            t_running_mean=running_mean_temp or outdoor_temp,
            v=AIR_VELOCITY_MAP.get(air_velocity, 0.1),
            device_name=device_name,
        )

    def _extract_comfort_limits(self, ashrae_result: Any, category: ComfortCategory) -> Tuple[float, float, float]:
        if category == "I":
            return (ashrae_result.tmp_cmf, ashrae_result.tmp_cmf_90_low, ashrae_result.tmp_cmf_90_up)
        return (ashrae_result.tmp_cmf, ashrae_result.tmp_cmf_80_low, ashrae_result.tmp_cmf_80_up)

    # The rest of ComfortCalculator is moved verbatim from the original calculator.py
    # to keep behavior identical while relocating to utils.
    # fmt: off
    def calculate_hvac_and_fan(self, indoor_temp: float, outdoor_temp: float, min_temp: float, max_temp: float, season: str, category: ComfortCategory = "I", air_velocity: FanMode = "low", indoor_humidity: Optional[float] = None, outdoor_humidity: Optional[float] = None, running_mean_temp: Optional[float] = None, energy_save_mode: bool = True, device_name: str = "Adaptive Climate", aggressive_cooling_threshold: Optional[float] = 2.0, aggressive_heating_threshold: Optional[float] = 2.0, enable_fan_mode: bool = True, enable_cool_mode: bool = True, enable_heat_mode: bool = True, enable_dry_mode: bool = True, enable_off_mode: bool = True, max_fan_speed: str = "high", min_fan_speed: str = "low", override_temperature: float = 0.0, temperature_change_threshold: float = 0.5, user_comfort_min: Optional[float] = None, user_comfort_max: Optional[float] = None) -> Dict[str, Any]:
        # Sanitize device limits in case the climate platform exposes bogus values (e.g., 0–1°C)
        try:
            device_min = float(min_temp)
        except Exception:
            device_min = 16.0
        try:
            device_max = float(max_temp)
        except Exception:
            device_max = 30.0
        if device_min >= device_max or device_min < 5.0 or device_max > 40.0 or (device_max - device_min) < 5.0:
            _LOGGER.debug(
                f"[{device_name}] Detected unrealistic device limits ({min_temp}°C - {max_temp}°C). "
                f"Using safe defaults 16.0°C - 30.0°C."
            )
            device_min = 16.0
            device_max = 30.0
        # Replace incoming values with sanitized ones for the rest of the calculation
        min_temp = device_min
        max_temp = device_max
        _LOGGER.debug(f"[{device_name}] Starting comfort calculation with inputs:")
        _LOGGER.debug(f"[{device_name}]   - Indoor temp: {indoor_temp:.2f}°C")
        _LOGGER.debug(f"[{device_name}]   - Outdoor temp: {outdoor_temp:.2f}°C")
        _LOGGER.debug(f"[{device_name}]   - Device setpoint min: {min_temp:.2f}°C")
        _LOGGER.debug(f"[{device_name}]   - Device setpoint max: {max_temp:.2f}°C")
        if user_comfort_min is not None or user_comfort_max is not None:
            _LOGGER.debug(
                f"[{device_name}]   - User comfort bounds: "
                f"{(user_comfort_min if user_comfort_min is not None else '-')}-"
                f"{(user_comfort_max if user_comfort_max is not None else '-')}°C"
            )
        _LOGGER.debug(f"[{device_name}]   - Season: {season}")
        _LOGGER.debug(f"[{device_name}]   - Category: {category}")
        # Clamp running mean temp to ASHRAE valid range to avoid calculation errors
        effective_running_mean = (
            running_mean_temp if running_mean_temp is not None else outdoor_temp
        )
        if effective_running_mean is not None:
            effective_running_mean = max(
                ASHRAE_55_TEMP_MIN, min(effective_running_mean, ASHRAE_55_TEMP_MAX)
            )

        _LOGGER.debug(
            f"[{device_name}]   - Running mean temp: {effective_running_mean:.2f}°C"
            if effective_running_mean is not None
            else f"[{device_name}]   - Running mean temp: None"
        )

        outdoor_temp = max(ASHRAE_55_TEMP_MIN, min(outdoor_temp, ASHRAE_55_TEMP_MAX))
        if indoor_humidity is not None:
            indoor_humidity = max(0, min(indoor_humidity, 100))
        if outdoor_humidity is not None:
            outdoor_humidity = max(0, min(outdoor_humidity, 100))

        ashrae_result = self.calculate_ashrae(
            indoor_temp,
            outdoor_temp,
            air_velocity,
            effective_running_mean,
            device_name=device_name,
        )
        comfort_temp, min_comfort_temp, max_comfort_temp = self._extract_comfort_limits(ashrae_result, category)

        # Effective bounds = device limits intersect user comfort bounds (if provided)
        effective_min_bound = min_temp
        effective_max_bound = max_temp
        if user_comfort_min is not None:
            effective_min_bound = max(effective_min_bound, float(user_comfort_min))
        if user_comfort_max is not None:
            effective_max_bound = min(effective_max_bound, float(user_comfort_max))
        if effective_min_bound > effective_max_bound:
            # If user bounds are contradictory, fall back to device bounds
            effective_min_bound = min_temp
            effective_max_bound = max_temp

        ranges = self._determine_temperature_ranges(indoor_temp, min_comfort_temp, comfort_temp, max_comfort_temp, season)

        hvac_mode, fan, temperature = self._determine_hvac_and_fan_mode(
            ranges,
            season,
            energy_save_mode,
            indoor_temp,
            outdoor_temp,
            comfort_temp,
            min_comfort_temp,
            max_comfort_temp,
            effective_min_bound,
            effective_max_bound,
            aggressive_cooling_threshold,
            aggressive_heating_threshold,
            enable_fan_mode,
            enable_cool_mode,
            enable_heat_mode,
            enable_dry_mode,
            enable_off_mode,
            max_fan_speed,
            min_fan_speed,
            override_temperature,
            temperature_change_threshold,
        )

        if override_temperature != 0.0:
            original_temperature = temperature
            temperature += override_temperature
            temperature = max(min_temp, min(temperature, max_temp))
            _LOGGER.debug(f"[{device_name}] Applied temperature override: {original_temperature:.2f}°C + {override_temperature:.2f}°C = {temperature:.2f}°C")

        _LOGGER.debug(f"[{device_name}] Temperature ranges: below_min={ranges['below_min']}, slightly_cool={ranges['slightly_cool']}, comfortably_cool={ranges['comfortably_cool']}, comfortably_warm={ranges['comfortably_warm']}, slightly_warm={ranges['slightly_warm']}, above_max={ranges['above_max']}")
        _LOGGER.debug(f"[{device_name}] Calculated comfort parameters:")
        _LOGGER.debug(f"[{device_name}]   - Comfort temp: {comfort_temp:.2f}°C")
        _LOGGER.debug(f"[{device_name}]   - Min comfort temp: {min_comfort_temp:.2f}°C")
        _LOGGER.debug(f"[{device_name}]   - Max comfort temp: {max_comfort_temp:.2f}°C")
        _LOGGER.debug(f"[{device_name}]   - Target temperature: {temperature:.2f}°C")
        _LOGGER.debug(f"[{device_name}]   - HVAC mode: {hvac_mode}")
        _LOGGER.debug(f"[{device_name}]   - Fan mode: {fan}")

        return {
            "season": season,
            "category": category,
            "comfort_temp": round(
                max(effective_min_bound, min(comfort_temp, effective_max_bound)), 2
            ),
            "hvac_mode": hvac_mode,
            "fan_mode": fan,
            "target_temp": round(temperature, 2),
            "ashrae_compliant": ashrae_result.acceptability_90 if category == "I" else ashrae_result.acceptability_80,
            "comfort_min_ashrae": round(min_comfort_temp, 2),
            "comfort_max_ashrae": round(max_comfort_temp, 2),
            "tr": round(indoor_temp, 2),
            "running_mean_temp": (
                round(effective_running_mean, 2)
                if effective_running_mean is not None
                else None
            ),
            "humidity_adjustment": 0.0,
            # New explicit names for clarity (kept alongside legacy keys)
            "ashrae_min_temperature": round(min_comfort_temp, 2),
            "ashrae_max_temperature": round(max_comfort_temp, 2),
            "ashrae_comfort_temperature": round(comfort_temp, 2),
            "user_min_temperature": (
                round(user_comfort_min, 2) if user_comfort_min is not None else None
            ),
            "user_max_temperature": (
                round(user_comfort_max, 2) if user_comfort_max is not None else None
            ),
        }

    def calculate(self, **kwargs) -> Dict[str, Any]:
        return self.calculate_hvac_and_fan(**kwargs)

    def _determine_temperature_ranges(self, temperature_for_calc: float, min_comfort_temp: float, comfort_temp: float, max_comfort_temp: float, season: str) -> Dict[str, bool]:
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

    def _is_temperature_change_significant(self, current_temp: float, target_temp: float, threshold: float) -> bool:
        if current_temp is None or target_temp is None:
            return True
        return abs(current_temp - target_temp) >= threshold

    def _should_take_action(self, current_temp: float, comfort_temp: float, threshold: float, action_type: str = "general") -> bool:
        if current_temp is None:
            return True
        temp_diff = abs(current_temp - comfort_temp)
        if action_type in ("equilibrium", "cooling", "heating"):
            return temp_diff >= threshold
        return temp_diff >= threshold

    # fmt: on

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
        enable_off_mode: bool,
        max_fan_speed: str,
        min_fan_speed: str,
        override_temperature: float,
        temperature_change_threshold: float,
    ) -> Tuple[str, str, float]:
        """Seasonal decision tree restored (summer/winter/transition) with thresholds.

        Preserves: user/device bounds, temperature_change_threshold hysteresis, energy_save_mode,
        and enable_* flags. Fan levels are limited by user min/max fan settings.
        """

        def clamp_temp(value: float) -> float:
            return max(min_temp, min(value, max_temp))

        def fallback_when_disabled(preferred: str, fan_level: str) -> Tuple[str, str, float]:
            # When a path is disabled, prefer dry/fan/off depending on capabilities and energy_save_mode
            if preferred == "cool" and enable_dry_mode:
                return ("dry", self._limit_fan_speed(fan_level, max_fan_speed, min_fan_speed), clamp_temp(comfort_temp))
            if enable_fan_mode:
                return ("fan_only", self._limit_fan_speed(fan_level, max_fan_speed, min_fan_speed), clamp_temp(comfort_temp))
            if enable_off_mode:
                return ("off", "auto", clamp_temp(comfort_temp))
            return ("fan_only", "auto", clamp_temp(comfort_temp))

        def equilibrium_choice() -> Tuple[str, str, float]:
            # Around comfort → prefer off/fan-only
            if energy_save_mode and enable_off_mode:
                return ("off", "auto", clamp_temp(comfort_temp))
            if enable_fan_mode:
                return ("fan_only", self._limit_fan_speed("low", max_fan_speed, min_fan_speed), clamp_temp(comfort_temp))
            return ("off" if enable_off_mode else "fan_only", "auto", clamp_temp(comfort_temp))

        def summer_mode() -> Tuple[str, str, float]:
            # Warm side tends to cooling
            if ranges.get("above_max") or ranges.get("slightly_warm") or ranges.get("comfortably_warm"):
                if enable_cool_mode:
                    # Stronger action when far above upper comfort
                    high_load = ranges.get("above_max") and indoor_temp >= (max_comfort_temp + aggressive_cooling_threshold)
                    fan_level = "high" if high_load else ("mid" if ranges.get("slightly_warm") else "low")
                    delta = 2 if high_load else 1
                    fan = self._limit_fan_speed(fan_level, max_fan_speed, min_fan_speed)
                    if self._should_take_action(indoor_temp, comfort_temp, temperature_change_threshold, "cooling"):
                        return ("cool", fan, clamp_temp(comfort_temp - delta))
                    return ("cool", fan, clamp_temp(comfort_temp))
                return fallback_when_disabled("cool", "mid")
            # Cool/near range → equilibrium or heating if clearly below
            if ranges.get("below_min") or ranges.get("slightly_cool") or ranges.get("comfortably_cool"):
                if enable_heat_mode:
                    # Only nudge towards comfort; never overshoot
                    delta = 2 if (ranges.get("below_min") and indoor_temp <= (min_comfort_temp - aggressive_heating_threshold)) else 1
                    fan = self._limit_fan_speed("mid" if ranges.get("slightly_cool") else "low", max_fan_speed, min_fan_speed)
                    if self._should_take_action(indoor_temp, comfort_temp, temperature_change_threshold, "heating"):
                        return ("heat", fan, clamp_temp(comfort_temp + delta))
                    return ("heat", fan, clamp_temp(comfort_temp))
                return equilibrium_choice()
            return equilibrium_choice()

        def winter_mode() -> Tuple[str, str, float]:
            # Cool side tends to heating
            if ranges.get("below_min") or ranges.get("slightly_cool") or ranges.get("comfortably_cool"):
                if enable_heat_mode:
                    delta = 2 if (ranges.get("below_min") and indoor_temp <= (min_comfort_temp - aggressive_heating_threshold)) else 1
                    fan = self._limit_fan_speed("mid" if ranges.get("slightly_cool") else "low", max_fan_speed, min_fan_speed)
                    if self._should_take_action(indoor_temp, comfort_temp, temperature_change_threshold, "heating"):
                        return ("heat", fan, clamp_temp(comfort_temp + delta))
                    return ("heat", fan, clamp_temp(comfort_temp))
                return fallback_when_disabled("heat", "mid")
            # Warm side → prefer off when saving energy, otherwise allow cool lightly
            if ranges.get("above_max") or ranges.get("slightly_warm") or ranges.get("comfortably_warm"):
                if energy_save_mode and enable_off_mode:
                    return ("off", "off", clamp_temp(comfort_temp))
                if enable_cool_mode:
                    fan = self._limit_fan_speed("low", max_fan_speed, min_fan_speed)
                    if self._should_take_action(indoor_temp, comfort_temp, temperature_change_threshold, "cooling"):
                        return ("cool", fan, clamp_temp(comfort_temp - 1))
                    return ("cool", fan, clamp_temp(comfort_temp))
                return equilibrium_choice()
            return equilibrium_choice()

        def transition_mode() -> Tuple[str, str, float]:
            # Shoulder seasons: be conservative, use fan_only when close to comfort
            if energy_save_mode:
                if ranges.get("comfortably_cool") or ranges.get("comfortably_warm"):
                    return ("fan_only" if enable_fan_mode else ("off" if enable_off_mode else "fan_only"),
                            self._limit_fan_speed("low", max_fan_speed, min_fan_speed) if enable_fan_mode else "off",
                            clamp_temp(comfort_temp))
                if ranges.get("slightly_cool"):
                    if enable_heat_mode:
                        return ("heat", self._limit_fan_speed("low", max_fan_speed, min_fan_speed), clamp_temp(comfort_temp))
                    return fallback_when_disabled("heat", "low")
                if ranges.get("slightly_warm"):
                    if enable_cool_mode:
                        return ("cool", self._limit_fan_speed("low", max_fan_speed, min_fan_speed), clamp_temp(comfort_temp))
                    return fallback_when_disabled("cool", "low")
                if ranges.get("below_min"):
                    if enable_heat_mode:
                        return ("heat", self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), clamp_temp(comfort_temp))
                    return fallback_when_disabled("heat", "mid")
                if ranges.get("above_max"):
                    if enable_cool_mode:
                        return ("cool", self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), clamp_temp(comfort_temp))
                    return fallback_when_disabled("cool", "mid")
                return equilibrium_choice()
            # No energy save → allow small ±1°C nudges
            if ranges.get("comfortably_cool") or ranges.get("comfortably_warm"):
                return ("fan_only" if enable_fan_mode else ("off" if enable_off_mode else "fan_only"),
                        self._limit_fan_speed("low", max_fan_speed, min_fan_speed) if enable_fan_mode else "off",
                        clamp_temp(comfort_temp))
            if ranges.get("slightly_cool"):
                if enable_heat_mode:
                    return ("heat", self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), clamp_temp(comfort_temp + 1))
                return fallback_when_disabled("heat", "mid")
            if ranges.get("slightly_warm"):
                if enable_cool_mode:
                    return ("cool", self._limit_fan_speed("mid", max_fan_speed, min_fan_speed), clamp_temp(comfort_temp - 1))
                return fallback_when_disabled("cool", "mid")
            if ranges.get("below_min"):
                if enable_heat_mode:
                    high = indoor_temp <= (min_comfort_temp - aggressive_heating_threshold)
                    return ("heat", self._limit_fan_speed("high" if high else "mid", max_fan_speed, min_fan_speed), clamp_temp(comfort_temp + (2 if high else 2)))
                return fallback_when_disabled("heat", "high")
            if ranges.get("above_max"):
                if enable_cool_mode:
                    return ("cool", self._limit_fan_speed("high", max_fan_speed, min_fan_speed), clamp_temp(comfort_temp - 2))
                return fallback_when_disabled("cool", "high")
            return equilibrium_choice()

        season_key = (season or "").lower()
        if season_key == "summer":
            return summer_mode()
        if season_key == "winter":
            return winter_mode()
        # spring/autumn or unknown
        return transition_mode()