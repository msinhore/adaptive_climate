"""Binary sensor platform for Adaptive Climate."""

from __future__ import annotations
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
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
    coordinator = hass.data[DOMAIN]["coordinators"][config_entry.entry_id]
    async_add_entities([ASHRAEComplianceSensor(coordinator, config_entry)])
    _LOGGER.info("Added ASHRAE compliance binary sensor for Adaptive Climate")


class ASHRAEComplianceSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for ASHRAE 55 compliance."""

    def __init__(self, coordinator: AdaptiveClimateCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.config_entry = config_entry
        entry_id = config_entry.entry_id.replace("-", "_")
        area = coordinator.config.get('name', 'Adaptive Climate')

        self._attr_unique_id = f"{entry_id}_ashrae_compliance"
        self._attr_name = f"{area} ASHRAE Compliance"
        self._attr_icon = "mdi:check-circle-outline"
        self._attr_entity_id = f"binary_sensor.{area.lower().replace(' ', '_')}_ashrae_compliance"
        
        _LOGGER.debug(f"[{area}] Binary sensor initialized: {self._attr_name}")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            name="Adaptive Climate",
            manufacturer="Adaptive Climate",
            model="ASHRAE 55 Adaptive Comfort",
            sw_version=VERSION,
            configuration_url="https://github.com/msinhore/adaptive-climate",
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if ASHRAE compliant."""
        data = self.coordinator.data
        if not data:
            return None
        
        ashrae_compliant = data.get("ashrae_compliant")
        _LOGGER.debug(f"[{self.coordinator.device_name}] ASHRAE compliance: {ashrae_compliant}")
        return ashrae_compliant

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        data = self.coordinator.data
        is_available = (
            self.coordinator.last_update_success and 
            data and 
            data.get("status") != "entities_unavailable"
        )
        _LOGGER.debug(f"[{self.coordinator.device_name}] Binary sensor available: {is_available}")
        return is_available

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic attributes."""
        data = self.coordinator.data
        if not data:
            return {}

        attrs = {
            "indoor_temperature": data.get("indoor_temperature"),
            "outdoor_temperature": data.get("outdoor_temperature"),
            "adaptive_comfort_temp": round(data.get("adaptive_comfort_temp", 0), 1),
            "comfort_temp_min": round(data.get("comfort_temp_min", 0), 1),
            "comfort_temp_max": round(data.get("comfort_temp_max", 0), 1),
            "ashrae_compliant": data.get("ashrae_compliant"),
            "running_mean_temp": data.get("running_mean_temp"),
            "indoor_humidity": data.get("indoor_humidity"),
            "outdoor_humidity": data.get("outdoor_humidity"),
        }

        # Add control actions if available
        control_actions = data.get("control_actions")
        if control_actions:
            attrs.update({
                "target_temperature": control_actions.get("set_temperature"),
                "target_hvac_mode": control_actions.get("set_hvac_mode"),
                "target_fan_mode": control_actions.get("set_fan_mode"),
                "action_reason": control_actions.get("reason"),
            })

        _LOGGER.debug(f"[{self.coordinator.device_name}] Binary sensor attributes: {attrs}")
        return attrs

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return True
