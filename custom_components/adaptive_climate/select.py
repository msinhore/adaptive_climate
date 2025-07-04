"""Select platform for Adaptive Climate."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .bridge_entity import create_bridge_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Adaptive Climate select entities."""
    # Add bridge entities for UI helpers
    bridge_entities = create_bridge_entities(hass, config_entry, "select")
    async_add_entities(bridge_entities)
