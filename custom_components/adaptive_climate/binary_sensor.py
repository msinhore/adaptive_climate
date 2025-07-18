"""Binary sensor platform for Adaptive Climate."""

from __future__ import annotations
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION
from .coordinator import AdaptiveClimateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Adaptive Climate binary sensor."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([ASHRAEComplianceSensor(coordinator, config_entry)])


class ASHRAEComplianceSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for ASHRAE 55 compliance."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.config_entry = config_entry
        entry_id = config_entry.entry_id.replace("-", "_")
        area = config_entry.data.get('name', 'Adaptive Climate')

        self._attr_unique_id = f"{entry_id}_ashrae_compliance"
        self._attr_name = f"{area} ASHRAE Compliance"
        self._attr_icon = "mdi:check-circle-outline"
        self._attr_entity_id = f"binary_sensor.{area.lower().replace(' ', '_')}_ashrae_compliance"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Adaptive Climate",
            "manufacturer": "Adaptive Climate",
            "model": "ASHRAE 55 Adaptive Comfort",
            "sw_version": VERSION,
            "configuration_url": "https://github.com/msinhore/adaptive-climate",
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if ASHRAE compliant."""
        data = self.coordinator.data
        return data.get("ashrae_compliant") if data else False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        data = self.coordinator.data
        return self.coordinator.last_update_success and data and data.get("status") != "entities_unavailable"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic attributes only."""
        data = self.coordinator.data
        if not data:
            return {}

        attrs = {
            "indoor_temperature": data.get("indoor_temperature"),
            "outdoor_temperature": data.get("outdoor_temperature"),
            "running_mean_indoor_temp": data.get("running_mean_indoor_temp"),
            "running_mean_outdoor_temp": data.get("running_mean_outdoor_temp"),
            "adaptive_comfort_temp": round(data.get("adaptive_comfort_temp", 0), 1),
            "comfort_temp_min": round(data.get("comfort_temp_min", 0), 1),
            "comfort_temp_max": round(data.get("comfort_temp_max", 0), 1),
            "ashrae_compliant": data.get("ashrae_compliant"),
        }

        # Include effective min/max if available
        effective_min = data.get("effective_comfort_min")
        effective_max = data.get("effective_comfort_max")
        if effective_min is not None:
            attrs["effective_comfort_min"] = round(effective_min, 1)
        if effective_max is not None:
            attrs["effective_comfort_max"] = round(effective_max, 1)

        return attrs
