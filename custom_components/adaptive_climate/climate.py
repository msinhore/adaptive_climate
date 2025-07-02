"""Climate platform for Adaptive Climate integration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_NAME,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .ashrae_calculator import AdaptiveComfortCalculator
from .const import (
    DOMAIN,
    UPDATE_INTERVAL_SHORT,
    UPDATE_INTERVAL_MEDIUM,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Adaptive Climate platform."""
    config = config_entry.data
    
    adaptive_climate = AdaptiveClimate(hass, config, config_entry.entry_id)
    async_add_entities([adaptive_climate])


class AdaptiveClimate(ClimateEntity, RestoreEntity):
    """Adaptive Climate entity based on ASHRAE 55 standard."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.AUTO,
        HVACMode.FAN_ONLY,
    ]
    _attr_fan_modes = ["auto", "low", "medium", "high"]
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, hass: HomeAssistant, config: dict[str, Any], entry_id: str) -> None:
        """Initialize the Adaptive Climate."""
        self.hass = hass
        self.config = config
        self._entry_id = entry_id
        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = f"{DOMAIN}_{entry_id}"
        
        # Device info for better HA 2025.6.0+ integration
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=config[CONF_NAME],
            manufacturer="Adaptive Climate",
            model="ASHRAE 55 Adaptive Comfort Controller",
            sw_version="2.0.0",
            configuration_url="https://github.com/msinhore/adaptive-climate",
        )
        
        # Initialize calculator
        self._calculator = AdaptiveComfortCalculator(config)
        
        # Climate entity references
        self._climate_entity_id = config["climate_entity"]
        self._indoor_temp_sensor_id = config["indoor_temp_sensor"]
        self._outdoor_temp_sensor_id = config["outdoor_temp_sensor"]
        self._occupancy_sensor_id = config.get("occupancy_sensor")
        self._mean_radiant_sensor_id = config.get("mean_radiant_temp_sensor")
        self._indoor_humidity_sensor_id = config.get("indoor_humidity_sensor")
        self._outdoor_humidity_sensor_id = config.get("outdoor_humidity_sensor")
        
        # State variables
        self._hvac_mode = HVACMode.OFF
        self._target_temperature = 22.0
        self._current_temperature = None
        self._fan_mode = "auto"
        self._hvac_action = HVACAction.OFF
        self._is_on = False
        
        # Tracking variables
        self._last_update = None
        self._last_sensor_update = None
        self._occupancy_last_changed = None
        self._update_tracker = None
        self._sensor_trackers = []
        
        # Control flags
        self._manual_override = False
        self._manual_override_time = None
        self._auto_shutdown_active = False

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        
        # Restore previous state
        if (old_state := await self.async_get_last_state()) is not None:
            if old_state.state != STATE_UNAVAILABLE:
                self._hvac_mode = HVACMode(old_state.state)
                self._is_on = old_state.state != HVACMode.OFF
                
            if old_state.attributes.get(ATTR_TEMPERATURE) is not None:
                self._target_temperature = float(old_state.attributes[ATTR_TEMPERATURE])
                
            if old_state.attributes.get("fan_mode") is not None:
                self._fan_mode = old_state.attributes["fan_mode"]
        
        # Set up sensor tracking
        await self._setup_sensor_tracking()
        
        # Set up periodic updates
        self._update_tracker = async_track_time_interval(
            self.hass,
            self._async_periodic_update,
            timedelta(minutes=UPDATE_INTERVAL_MEDIUM),
        )
        
        # Initial update
        await self._async_update_sensors()
        await self._async_update_climate_control()

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        if self._update_tracker:
            self._update_tracker()
        
        for tracker in self._sensor_trackers:
            tracker()
        self._sensor_trackers.clear()

    async def _setup_sensor_tracking(self) -> None:
        """Set up tracking for all sensor entities."""
        sensors_to_track = [
            self._climate_entity_id,
            self._indoor_temp_sensor_id,
            self._outdoor_temp_sensor_id,
        ]
        
        # Add optional sensors
        for sensor_id in [
            self._occupancy_sensor_id,
            self._mean_radiant_sensor_id,
            self._indoor_humidity_sensor_id,
            self._outdoor_humidity_sensor_id,
        ]:
            if sensor_id:
                sensors_to_track.append(sensor_id)
        
        # Track state changes
        tracker = async_track_state_change_event(
            self.hass,
            sensors_to_track,
            self._async_sensor_changed,
        )
        self._sensor_trackers.append(tracker)

    @callback
    async def _async_sensor_changed(self, event: Event) -> None:
        """Handle sensor state changes."""
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        
        if not new_state or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return
        
        _LOGGER.debug("Sensor %s changed to %s", entity_id, new_state.state)
        
        # Update sensors with short delay to batch multiple changes
        if not self._last_sensor_update or (
            dt_util.utcnow() - self._last_sensor_update
        ).total_seconds() > UPDATE_INTERVAL_SHORT * 60:
            await asyncio.sleep(1)  # Short delay to batch updates
            await self._async_update_sensors()
            await self._async_update_climate_control()

    async def _async_periodic_update(self, now: datetime) -> None:
        """Periodic update of climate control."""
        await self._async_update_sensors()
        await self._async_update_climate_control()

    async def _async_update_sensors(self) -> None:
        """Update all sensor readings."""
        try:
            # Get outdoor temperature
            outdoor_temp = await self._get_sensor_value(
                self._outdoor_temp_sensor_id, "temperature", 20.0
            )
            
            # Get indoor temperature
            indoor_temp = await self._get_sensor_value(
                self._indoor_temp_sensor_id, "temperature", 22.0
            )
            
            # Get optional sensors
            indoor_humidity = None
            if self._indoor_humidity_sensor_id:
                indoor_humidity = await self._get_sensor_value(
                    self._indoor_humidity_sensor_id, None, None
                )
            
            outdoor_humidity = None
            if self._outdoor_humidity_sensor_id:
                outdoor_humidity = await self._get_sensor_value(
                    self._outdoor_humidity_sensor_id, "humidity", None
                )
            
            mean_radiant_temp = None
            if self._mean_radiant_sensor_id:
                mean_radiant_temp = await self._get_sensor_value(
                    self._mean_radiant_sensor_id, None, None
                )
            
            # Get occupancy state
            occupancy_state = True
            if self._occupancy_sensor_id and self.config.get("use_occupancy_features", False):
                occupancy_state = await self._get_binary_sensor_state(
                    self._occupancy_sensor_id
                )
                
                # Track occupancy changes for absence detection
                if not occupancy_state and self._occupancy_last_changed is None:
                    self._occupancy_last_changed = dt_util.utcnow()
                elif occupancy_state:
                    self._occupancy_last_changed = None
                    self._auto_shutdown_active = False
            
            # Update calculator
            self._calculator.update_sensors(
                outdoor_temp=outdoor_temp,
                indoor_temp=indoor_temp,
                indoor_humidity=indoor_humidity,
                outdoor_humidity=outdoor_humidity,
                mean_radiant_temp=mean_radiant_temp,
                occupancy_state=occupancy_state,
            )
            
            self._last_sensor_update = dt_util.utcnow()
            _LOGGER.debug("Sensors updated: outdoor=%s°C, indoor=%s°C", outdoor_temp, indoor_temp)
            
        except Exception as e:
            _LOGGER.error("Error updating sensors: %s", e)

    async def _get_sensor_value(
        self, entity_id: str, attribute: str | None, default: float | None
    ) -> float | None:
        """Get sensor value, handling weather entities and attributes."""
        if not entity_id:
            return default
        
        state = self.hass.states.get(entity_id)
        if not state or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return default
        
        try:
            if entity_id.startswith("weather.") and attribute:
                return float(state.attributes.get(attribute, default or 0))
            else:
                return float(state.state)
        except (ValueError, TypeError):
            return default

    async def _get_binary_sensor_state(self, entity_id: str) -> bool:
        """Get binary sensor state."""
        if not entity_id:
            return True
        
        state = self.hass.states.get(entity_id)
        if not state or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return True
        
        return state.state == STATE_ON

    async def _async_update_climate_control(self) -> None:
        """Update climate control based on adaptive comfort calculations."""
        try:
            # Check for manual override timeout
            if self._manual_override and self._manual_override_time:
                if (dt_util.utcnow() - self._manual_override_time).total_seconds() > 3600:  # 1 hour
                    self._manual_override = False
                    self._manual_override_time = None
                    _LOGGER.info("Manual override expired, resuming adaptive control")
            
            if self._manual_override:
                _LOGGER.debug("Manual override active, skipping adaptive control")
                return
            
            # Check for auto shutdown conditions
            if await self._check_auto_shutdown():
                return
            
            # Get current climate state
            climate_state = self.hass.states.get(self._climate_entity_id)
            if not climate_state or climate_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                _LOGGER.warning("Climate entity %s is unavailable", self._climate_entity_id)
                return
            
            current_hvac_mode = climate_state.state
            current_temp = climate_state.attributes.get(ATTR_TEMPERATURE, 0)
            current_fan_mode = climate_state.attributes.get("fan_mode", "auto")
            
            # Get adaptive recommendations
            status = self._calculator.get_status_summary()
            recommended_hvac_mode = status["hvac_mode_recommendation"]
            target_temp = status["target_temp"]
            optimal_fan_speed = status["optimal_fan_speed"]
            
            # Check if natural ventilation is available
            if status["natural_ventilation_available"]:
                await self._turn_off_climate("Natural ventilation active")
                return
            
            # Update internal state
            self._target_temperature = target_temp
            self._current_temperature = status["indoor_temp"]
            
            # Apply climate control changes
            changes_made = []
            
            # Update HVAC mode if needed
            if recommended_hvac_mode != "off" and current_hvac_mode != recommended_hvac_mode:
                await self._set_hvac_mode(recommended_hvac_mode)
                changes_made.append(f"HVAC mode: {current_hvac_mode} → {recommended_hvac_mode}")
            
            # Update temperature if needed and not in off mode
            if (
                recommended_hvac_mode != "off"
                and abs(current_temp - target_temp) >= self.config.get("temperature_change_threshold", 1.0)
            ):
                await self._set_temperature(target_temp)
                changes_made.append(f"Temperature: {current_temp}°C → {target_temp}°C")
            
            # Update fan mode if adaptive air velocity is enabled
            if (
                self.config.get("adaptive_air_velocity", True)
                and optimal_fan_speed != "auto"
                and current_fan_mode != optimal_fan_speed
            ):
                await self._set_fan_mode(optimal_fan_speed)
                changes_made.append(f"Fan mode: {current_fan_mode} → {optimal_fan_speed}")
            
            # Log changes
            if changes_made:
                _LOGGER.info(
                    "Adaptive climate control applied: %s | Comfort zone: %.1f-%.1f°C | %s",
                    ", ".join(changes_made),
                    status["comfort_temp_min"],
                    status["comfort_temp_max"],
                    status["compliance_notes"],
                )
            
            self._last_update = dt_util.utcnow()
            self.async_write_ha_state()
            
        except Exception as e:
            _LOGGER.error("Error updating climate control: %s", e)

    async def _check_auto_shutdown(self) -> bool:
        """Check if auto shutdown should be triggered."""
        if not self.config.get("auto_shutdown_enable", False):
            return False
        
        if not self._occupancy_sensor_id or not self.config.get("use_occupancy_features", False):
            return False
        
        if self._occupancy_last_changed is None:
            return False
        
        auto_shutdown_minutes = self.config.get("auto_shutdown_minutes", 120)
        absence_duration = (dt_util.utcnow() - self._occupancy_last_changed).total_seconds() / 60
        
        if absence_duration >= auto_shutdown_minutes and not self._auto_shutdown_active:
            await self._turn_off_climate(f"Auto shutdown after {auto_shutdown_minutes} minutes of absence")
            self._auto_shutdown_active = True
            return True
        
        return self._auto_shutdown_active

    async def _turn_off_climate(self, reason: str) -> None:
        """Turn off the climate entity."""
        await self.hass.services.async_call(
            "climate",
            "turn_off",
            {"entity_id": self._climate_entity_id},
        )
        
        self._hvac_mode = HVACMode.OFF
        self._hvac_action = HVACAction.OFF
        self._is_on = False
        
        _LOGGER.info("Climate turned off: %s", reason)
        self.async_write_ha_state()

    async def _set_hvac_mode(self, mode: str) -> None:
        """Set HVAC mode on the climate entity."""
        await self.hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {"entity_id": self._climate_entity_id, "hvac_mode": mode},
        )
        
        self._hvac_mode = HVACMode(mode)
        self._is_on = mode != HVACMode.OFF

    async def _set_temperature(self, temperature: float) -> None:
        """Set temperature on the climate entity."""
        await self.hass.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": self._climate_entity_id, "temperature": temperature},
        )

    async def _set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode on the climate entity."""
        await self.hass.services.async_call(
            "climate",
            "set_fan_mode",
            {"entity_id": self._climate_entity_id, "fan_mode": fan_mode},
        )
        
        self._fan_mode = fan_mode

    # ClimateEntity implementation
    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return hvac operation ie. heat, cool mode."""
        return self._hvac_mode

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current running hvac operation."""
        return self._hvac_action

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._current_temperature

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting."""
        return self._fan_mode

    @property
    def is_on(self) -> bool | None:
        """Return true if on."""
        return self._is_on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        status = self._calculator.get_status_summary()
        
        return {
            "adaptive_comfort_temp": status["adaptive_comfort_temp"],
            "comfort_temp_min": status["comfort_temp_min"],
            "comfort_temp_max": status["comfort_temp_max"],
            "comfort_category": status["comfort_category"],
            "comfort_tolerance": status["comfort_tolerance"],
            "outdoor_temp": status["outdoor_temp"],
            "operative_temp": status["operative_temp"],
            "hvac_mode_recommendation": status["hvac_mode_recommendation"],
            "optimal_fan_speed": status["optimal_fan_speed"],
            "natural_ventilation_available": status["natural_ventilation_available"],
            "occupancy_state": status["occupancy_state"],
            "compliance_notes": status["compliance_notes"],
            "manual_override": self._manual_override,
            "auto_shutdown_active": self._auto_shutdown_active,
            "last_update": self._last_update.isoformat() if self._last_update else None,
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        _LOGGER.info("Manual HVAC mode change to %s - enabling override", hvac_mode)
        self._manual_override = True
        self._manual_override_time = dt_util.utcnow()
        
        await self._set_hvac_mode(hvac_mode)
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        
        _LOGGER.info("Manual temperature change to %.1f°C - enabling override", temperature)
        self._manual_override = True
        self._manual_override_time = dt_util.utcnow()
        
        self._target_temperature = temperature
        await self._set_temperature(temperature)
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        _LOGGER.info("Manual fan mode change to %s - enabling override", fan_mode)
        self._manual_override = True
        self._manual_override_time = dt_util.utcnow()
        
        await self._set_fan_mode(fan_mode)
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        _LOGGER.info("Manual turn on - enabling override")
        self._manual_override = True
        self._manual_override_time = dt_util.utcnow()
        self._auto_shutdown_active = False
        
        # Use recommended mode or auto
        status = self._calculator.get_status_summary()
        recommended_mode = status["hvac_mode_recommendation"]
        
        if recommended_mode != "off":
            await self._set_hvac_mode(recommended_mode)
        else:
            await self._set_hvac_mode(HVACMode.AUTO)
        
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        _LOGGER.info("Manual turn off - enabling override")
        self._manual_override = True
        self._manual_override_time = dt_util.utcnow()
        
        await self._turn_off_climate("Manual shutdown")
        self.async_write_ha_state()
