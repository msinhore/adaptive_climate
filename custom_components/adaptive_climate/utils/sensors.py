from __future__ import annotations

from typing import Optional

from homeassistant.core import HomeAssistant


NON_NUMERIC_STATES = {
    "unknown",
    "unavailable",
    "none",
    "nan",
    "inf",
    "-inf",
    "state_unknown",
}


def get_weather_entity_value(hass: HomeAssistant, entity_id: str, sensor_type: str) -> Optional[float]:
    """Get temperature or humidity value from weather entity attributes."""
    if not entity_id:
        return None
    
    state = hass.states.get(entity_id)
    if not state:
        return None
    
    # Weather entities store temperature and humidity in attributes
    if sensor_type in ["indoor_temp", "outdoor_temp"]:
        # Try temperature attribute first, then fall back to state
        temp_value = state.attributes.get("temperature")
        if temp_value is not None:
            try:
                value = float(temp_value)
                return value
            except (ValueError, TypeError):
                pass
    
    elif sensor_type in ["indoor_humidity", "outdoor_humidity"]:
        # Try humidity attribute first, then fall back to state
        humidity_value = state.attributes.get("humidity")
        if humidity_value is not None:
            try:
                value = float(humidity_value)
                return value
            except (ValueError, TypeError):
                pass
    
    # Fall back to state value if attributes don't have the data
    try:
        if str(state.state).lower() in NON_NUMERIC_STATES:
            return None
        return float(state.state)
    except (ValueError, TypeError):
        return None


def get_numeric_state_value(hass: HomeAssistant, entity_id: Optional[str]) -> Optional[float]:
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if not state:
        return None
    try:
        if str(state.state).lower() in NON_NUMERIC_STATES:
            return None
        return float(state.state)
    except (ValueError, TypeError):
        return None



