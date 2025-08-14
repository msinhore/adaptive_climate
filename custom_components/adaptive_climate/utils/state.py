from __future__ import annotations


def has_meaningful_user_change(new_state, old_state) -> bool:
    """Return True if the state change affects user-controlled settings.

    Considers HVAC mode, target temperature (single or range), fan, swing, preset.
    Ignores telemetry-only updates.
    """
    if not new_state or not old_state:
        return False

    if new_state.state != old_state.state:
        return True

    attr_names = (
        "temperature",
        "target_temperature",
        "target_temp",
        "target_temp_low",
        "target_temp_high",
        "fan_mode",
        "swing_mode",
        "preset_mode",
    )
    for attr in attr_names:
        if new_state.attributes.get(attr) != old_state.attributes.get(attr):
            return True
    return False



