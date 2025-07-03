"""Logbook integration for Adaptive Climate."""
from __future__ import annotations

from typing import Callable

from homeassistant.components.logbook import (
    LOGBOOK_ENTRY_DOMAIN,
    LOGBOOK_ENTRY_ENTITY_ID,
    LOGBOOK_ENTRY_NAME,
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_SOURCE,
)
from homeassistant.const import ATTR_NAME
from homeassistant.core import HomeAssistant, callback, Event

from .const import DOMAIN, EVENT_ADAPTIVE_CLIMATE_MODE_CHANGE, EVENT_ADAPTIVE_CLIMATE_TARGET_TEMP


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict]], None],
) -> None:
    """Describe logbook events."""

    @callback
    def process_adaptive_climate_mode_change(event: Event) -> dict:
        """Process mode change events for logbook."""
        data = event.data
        entity_id = data.get("entity_id")
        name = data.get(ATTR_NAME)
        old_mode = data.get("old_mode", "unknown")
        new_mode = data.get("new_mode", "unknown")

        message = f"mudou de {old_mode} para {new_mode}"

        return {
            LOGBOOK_ENTRY_NAME: name or entity_id,
            LOGBOOK_ENTRY_MESSAGE: message,
            LOGBOOK_ENTRY_DOMAIN: DOMAIN,
            LOGBOOK_ENTRY_ENTITY_ID: entity_id,
            LOGBOOK_ENTRY_SOURCE: DOMAIN,
        }
    
    @callback
    def process_adaptive_climate_target_temp(event: Event) -> dict:
        """Process target temperature change events for logbook."""
        data = event.data
        entity_id = data.get("entity_id")
        name = data.get(ATTR_NAME)
        old_temp = data.get("old_temp", "unknown")
        new_temp = data.get("new_temp", "unknown")
        reason = data.get("reason", "unknown")

        message = f"temperatura alvo mudou de {old_temp}°C para {new_temp}°C (motivo: {reason})"

        return {
            LOGBOOK_ENTRY_NAME: name or entity_id,
            LOGBOOK_ENTRY_MESSAGE: message,
            LOGBOOK_ENTRY_DOMAIN: DOMAIN,
            LOGBOOK_ENTRY_ENTITY_ID: entity_id,
            LOGBOOK_ENTRY_SOURCE: DOMAIN,
        }

    # Register event processors
    async_describe_event(DOMAIN, EVENT_ADAPTIVE_CLIMATE_MODE_CHANGE, process_adaptive_climate_mode_change)
    async_describe_event(DOMAIN, EVENT_ADAPTIVE_CLIMATE_TARGET_TEMP, process_adaptive_climate_target_temp)
