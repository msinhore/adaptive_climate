from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from custom_components.adaptive_climate.utils.mode import map_fan_mode, map_hvac_mode, validate_mode_compatibility


def build_result_params(sensor_data: Dict[str, Any], comfort: Dict[str, Any], actions: Dict[str, Any], running_mean_temp: Optional[float]) -> Dict[str, Any]:
    comfort_temp = comfort.get("comfort_temp")
    comfort_min = comfort.get("comfort_min_ashrae")
    comfort_max = comfort.get("comfort_max_ashrae")
    return {
        "adaptive_comfort_temp": (round(comfort_temp, 2) if comfort_temp is not None else None),
        "comfort_temp_min": (round(comfort_min, 2) if comfort_min is not None else None),
        "comfort_temp_max": (round(comfort_max, 2) if comfort_max is not None else None),
        "indoor_temperature": (round(sensor_data["indoor_temp"], 2) if sensor_data["indoor_temp"] is not None else None),
        "outdoor_temperature": (round(sensor_data["outdoor_temp"], 2) if sensor_data["outdoor_temp"] is not None else None),
        "indoor_humidity": (round(sensor_data["indoor_humidity"], 2) if sensor_data["indoor_humidity"] is not None else None),
        "outdoor_humidity": (round(sensor_data["outdoor_humidity"], 2) if sensor_data["outdoor_humidity"] is not None else None),
        "running_mean_temp": (round(running_mean_temp, 2) if running_mean_temp is not None else None),
        "control_actions": actions,
        "ashrae_compliant": comfort.get("ashrae_compliant"),
        "last_updated": datetime.now(),
    }


def calculate_exponential_running_mean(history: List[Tuple[datetime, float]], alpha: float = 0.8) -> Optional[float]:
    if not history:
        return None
    temps = sorted(history, key=lambda x: x[0])
    running_mean: Optional[float] = None
    for _, temp in temps:
        if running_mean is None:
            running_mean = temp
        else:
            running_mean = (1 - alpha) * temp + alpha * running_mean
    return running_mean


def determine_actions(
    comfort: Dict[str, Any],
    device_name: str,
    supported_hvac_modes: List[str],
    supported_fan_modes: List[str],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    temperature = round(float(comfort.get("target_temp", 25)))
    hvac_mode = comfort.get("hvac_mode")
    fan_mode = comfort.get("fan_mode")

    user_min = config.get("min_comfort_temp")
    user_max = config.get("max_comfort_temp")
    if user_min is not None or user_max is not None:
        try:
            if user_min is not None:
                temperature = max(int(float(user_min)), temperature)
            if user_max is not None:
                temperature = min(int(float(user_max)), temperature)
        except Exception:
            pass

    try:
        indoor_now = comfort.get("indoor_temperature")
        hysteresis = float(config.get("temperature_change_threshold", 0.5))
        if indoor_now is not None:
            if user_max is not None and indoor_now >= float(user_max) + hysteresis:
                hvac_mode = "cool"
            elif user_min is not None and indoor_now <= float(user_min) - hysteresis:
                hvac_mode = "heat"
    except Exception:
        pass

    # Apply user overrides for HVAC intent when configured
    try:
        intent = (hvac_mode or "").lower()
        intent_key_map = {
            "cool": "hvac_mode_for_cooling",
            "heat": "hvac_mode_for_heating",
            "dry": "hvac_mode_for_drying",
            "fan_only": "hvac_mode_for_fan_only",
        }
        if intent in intent_key_map:
            override_key = intent_key_map[intent]
            override_value = config.get(override_key)
            if isinstance(override_value, str) and override_value:
                if override_value == "disable":
                    # Skip this intent: fall back according to energy_save_mode
                    energy_save = bool(config.get("energy_save_mode", True))
                    hvac_mode = "off" if energy_save else "fan_only"
                else:
                    # Force the selected device mode if supported; otherwise keep intent
                    if any(override_value.lower() == m.lower() for m in supported_hvac_modes):
                        hvac_mode = next(m for m in supported_hvac_modes if m.lower() == override_value.lower())
    except Exception:
        pass

    validation = validate_mode_compatibility(hvac_mode, fan_mode, supported_hvac_modes, supported_fan_modes, device_name)
    if not validation["hvac_valid"]:
        hvac_mode = validation["hvac_suggestion"]
    if not validation["fan_valid"]:
        fan_mode = validation["fan_suggestion"]

    hvac_mode = map_hvac_mode(str(hvac_mode), supported_hvac_modes, device_name) if supported_hvac_modes else hvac_mode
    fan_mode = map_fan_mode(str(fan_mode), supported_fan_modes, device_name) if supported_fan_modes else fan_mode

    if fan_mode == "highest" and "highest" not in [m.lower() for m in supported_fan_modes] and "high" in [m.lower() for m in supported_fan_modes]:
        fan_mode = next(m for m in supported_fan_modes if m.lower() == "high")

    return {
        "set_temperature": temperature,
        "set_hvac_mode": hvac_mode,
        "set_fan_mode": fan_mode,
        "override_temperature": config.get("override_temperature", 0),
        "reason": f"Calculated hvac mode: {hvac_mode}, temperature: {temperature}, fan mode: {fan_mode}.",
    }


