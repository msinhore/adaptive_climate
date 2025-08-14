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



