"""Logbook integration for Adaptive Climate."""
from __future__ import annotations

from collections.abc import Callable

import voluptuous as vol

from homeassistant.components.logbook import LOGBOOK_ENTRY_MESSAGE, LOGBOOK_ENTRY_NAME
from homeassistant.const import ATTR_NAME
from homeassistant.core import HomeAssistant, callback, Event

from .const import (
    DOMAIN,
    EVENT_ADAPTIVE_CLIMATE_MODE_CHANGE,
    EVENT_ADAPTIVE_CLIMATE_TARGET_TEMP,
)


@callback
def async_describe_events(hass: HomeAssistant, async_describe_event: Callable[[str, str, Callable[[Event], dict[str, str]]], None]) -> None:
    """Describe logbook events."""
    
    @callback
    def process_mode_change_event(event: Event) -> dict[str, str]:
        """Process adaptive climate mode change events for logbook."""
        data = event.data
        entity_id = data.get("entity_id")
        friendly_name = data.get(ATTR_NAME, entity_id)
        old_mode = data.get("old_mode", "unknown")
        new_mode = data.get("new_mode", "unknown")
        reason = data.get("reason", "adaptive control")

        return {
            LOGBOOK_ENTRY_NAME: friendly_name,
            LOGBOOK_ENTRY_MESSAGE: f"changed HVAC mode from {old_mode} to {new_mode} ({reason})",
        }

    @callback
    def process_target_temp_event(event: Event) -> dict[str, str]:
        """Process adaptive climate target temperature change events for logbook."""
        data = event.data
        entity_id = data.get("entity_id")
        friendly_name = data.get(ATTR_NAME, entity_id)
        old_temp = data.get("old_temp", "unknown")
        new_temp = data.get("new_temp", "unknown")
        reason = data.get("reason", "adaptive control")

        # Format temperatures with proper precision if they're numeric
        old_temp_str = f"{float(old_temp):.1f}" if isinstance(old_temp, (int, float)) else str(old_temp)
        new_temp_str = f"{float(new_temp):.1f}" if isinstance(new_temp, (int, float)) else str(new_temp)

        return {
            LOGBOOK_ENTRY_NAME: friendly_name,
            LOGBOOK_ENTRY_MESSAGE: f"changed target temperature from {old_temp_str}°C to {new_temp_str}°C ({reason})",
        }

    async_describe_event(
        DOMAIN, EVENT_ADAPTIVE_CLIMATE_MODE_CHANGE, process_mode_change_event
    )
    async_describe_event(
        DOMAIN, EVENT_ADAPTIVE_CLIMATE_TARGET_TEMP, process_target_temp_event
    )
