"""Device entities for Adaptive Climate integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity  
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, COMFORT_CATEGORIES


def async_setup_device_entities(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up device entities for Controls and Sensors tabs."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Create device info shared by all entities
    device_info = DeviceInfo(
        identifiers={(DOMAIN, config_entry.entry_id)},
        name=config_entry.title,
        manufacturer="Adaptive Climate",
        model="ASHRAE 55 Controller",
        sw_version="1.0.0",
        configuration_url=f"homeassistant://config/integrations/integration/{DOMAIN}",
    )
    
    entities = []
    
    # Controls (SwitchEntity, ButtonEntity, SelectEntity, NumberEntity)
    entities.extend([
        # Feature Switches
        AdaptiveClimateFeatureSwitch(coordinator, config_entry, device_info, "energy_save_mode", "Energy Save Mode"),
        AdaptiveClimateFeatureSwitch(coordinator, config_entry, device_info, "natural_ventilation_enable", "Natural Ventilation"),
        AdaptiveClimateFeatureSwitch(coordinator, config_entry, device_info, "adaptive_air_velocity", "Adaptive Air Velocity"),
        AdaptiveClimateFeatureSwitch(coordinator, config_entry, device_info, "humidity_comfort_enable", "Humidity Comfort"),
        AdaptiveClimateFeatureSwitch(coordinator, config_entry, device_info, "comfort_precision_mode", "Precision Mode"),
        AdaptiveClimateFeatureSwitch(coordinator, config_entry, device_info, "use_occupancy_features", "Occupancy Features"),
        AdaptiveClimateFeatureSwitch(coordinator, config_entry, device_info, "auto_shutdown_enable", "Auto Shutdown"),
        
        # Configuration Selects
        AdaptiveClimateComfortCategorySelect(coordinator, config_entry, device_info),
        
        # Configuration Numbers
        AdaptiveClimateConfigNumber(coordinator, config_entry, device_info, "min_comfort_temp", "Min Comfort Temperature", 15.0, 22.0, 0.1, "°C"),
        AdaptiveClimateConfigNumber(coordinator, config_entry, device_info, "max_comfort_temp", "Max Comfort Temperature", 25.0, 32.0, 0.1, "°C"),
        AdaptiveClimateConfigNumber(coordinator, config_entry, device_info, "temperature_change_threshold", "Temperature Threshold", 0.1, 3.0, 0.1, "°C"),
        AdaptiveClimateConfigNumber(coordinator, config_entry, device_info, "air_velocity", "Air Velocity", 0.0, 2.0, 0.1, "m/s"),
        AdaptiveClimateConfigNumber(coordinator, config_entry, device_info, "setback_temperature_offset", "Setback Offset", 1.0, 5.0, 0.1, "°C"),
        
        # Action Buttons  
        AdaptiveClimateActionButton(coordinator, config_entry, device_info, "reset_outdoor_history", "Reset Outdoor History"),
        AdaptiveClimateActionButton(coordinator, config_entry, device_info, "reconfigure_entities", "Reconfigure Entities"),
    ])
    
    # Sensors (SensorEntity)
    entities.extend([
        # Diagnostic Sensors
        AdaptiveClimateDiagnosticSensor(coordinator, config_entry, device_info, "current_comfort_temp", "Current Comfort Temperature", "°C"),
        AdaptiveClimateDiagnosticSensor(coordinator, config_entry, device_info, "outdoor_running_mean", "Outdoor Running Mean", "°C"),
        AdaptiveClimateDiagnosticSensor(coordinator, config_entry, device_info, "comfort_range_min", "Comfort Range Min", "°C"),
        AdaptiveClimateDiagnosticSensor(coordinator, config_entry, device_info, "comfort_range_max", "Comfort Range Max", "°C"),
        
        # Configuration Status Sensors
        AdaptiveClimateConfigSensor(coordinator, config_entry, device_info, "climate_entity", "Climate Entity"),
        AdaptiveClimateConfigSensor(coordinator, config_entry, device_info, "indoor_temp_sensor", "Indoor Temperature Sensor"),
        AdaptiveClimateConfigSensor(coordinator, config_entry, device_info, "outdoor_temp_sensor", "Outdoor Temperature Sensor"),
        AdaptiveClimateConfigSensor(coordinator, config_entry, device_info, "occupancy_sensor", "Occupancy Sensor"),
    ])
    
    async_add_entities(entities)


class AdaptiveClimateFeatureSwitch(SwitchEntity):
    """Switch entity for controlling adaptive climate features."""
    
    def __init__(self, coordinator, config_entry: ConfigEntry, device_info: DeviceInfo, option_key: str, name: str):
        """Initialize the switch."""
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._device_info = device_info
        self._option_key = option_key
        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_{option_key}"
        # Removed EntityCategory.CONFIG to show entities in Controls tab instead of Configuration
        # self._attr_entity_category = EntityCategory.CONFIG
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return self._device_info
    
    @property
    def is_on(self) -> bool:
        """Return if the switch is on."""
        return self.config_entry.options.get(self._option_key, False)
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        new_options = dict(self.config_entry.options)
        new_options[self._option_key] = True
        self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)
        
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        new_options = dict(self.config_entry.options)
        new_options[self._option_key] = False
        self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)


class AdaptiveClimateComfortCategorySelect(SelectEntity):
    """Select entity for comfort category selection."""
    
    def __init__(self, coordinator, config_entry: ConfigEntry, device_info: DeviceInfo):
        """Initialize the select."""
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._device_info = device_info
        self._attr_name = "Comfort Category"
        self._attr_unique_id = f"{config_entry.entry_id}_comfort_category"
        # Removed EntityCategory.CONFIG to show entities in Controls tab instead of Configuration
        # self._attr_entity_category = EntityCategory.CONFIG
        self._attr_options = ["I", "II", "III"]
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return self._device_info
    
    @property
    def current_option(self) -> str | None:
        """Return current option."""
        return self.config_entry.options.get("comfort_category", self.config_entry.data.get("comfort_category", "II"))
    
    async def async_select_option(self, option: str) -> None:
        """Select new option."""
        new_options = dict(self.config_entry.options)
        new_options["comfort_category"] = option
        self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)


class AdaptiveClimateConfigNumber(NumberEntity):
    """Number entity for configuration values."""
    
    def __init__(self, coordinator, config_entry: ConfigEntry, device_info: DeviceInfo, 
                 option_key: str, name: str, min_val: float, max_val: float, step: float, unit: str):
        """Initialize the number."""
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._device_info = device_info
        self._option_key = option_key
        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_{option_key}"
        # Removed EntityCategory.CONFIG to show entities in Controls tab instead of Configuration
        # self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return self._device_info
    
    @property
    def native_value(self) -> float | None:
        """Return current value."""
        return self.config_entry.options.get(self._option_key)
    
    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        new_options = dict(self.config_entry.options)
        new_options[self._option_key] = value
        self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)


class AdaptiveClimateActionButton(ButtonEntity):
    """Button entity for actions."""
    
    def __init__(self, coordinator, config_entry: ConfigEntry, device_info: DeviceInfo, action: str, name: str):
        """Initialize the button."""
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._device_info = device_info
        self._action = action
        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_{action}"
        # Removed EntityCategory.CONFIG to show entities in Controls tab instead of Configuration
        # self._attr_entity_category = EntityCategory.CONFIG
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return self._device_info
    
    async def async_press(self) -> None:
        """Handle button press."""
        if self._action == "reset_outdoor_history":
            # Reset outdoor temperature history
            if hasattr(self.coordinator, 'reset_outdoor_history'):
                await self.coordinator.reset_outdoor_history()
        elif self._action == "reconfigure_entities":
            # Remove and reconfigure - best approach for entity reconfiguration
            await self._reconfigure_entities()
    
    async def _reconfigure_entities(self) -> None:
        """Remove entry and trigger reconfiguration."""
        # This is the recommended approach for reconfiguring entities
        # since HA doesn't officially support entity reconfiguration in OptionsFlow
        entry_id = self.config_entry.entry_id
        title = self.config_entry.title
        
        # Store current data for potential recovery
        import json
        backup_data = {
            "data": dict(self.config_entry.data),
            "options": dict(self.config_entry.options),
            "title": title
        }
        
        # Store backup in hass.data temporarily
        if "adaptive_climate_backup" not in self.hass.data:
            self.hass.data["adaptive_climate_backup"] = {}
        self.hass.data["adaptive_climate_backup"][entry_id] = backup_data
        
        # Remove current entry
        await self.hass.config_entries.async_remove(entry_id)
        
        # Trigger flow discovery to show reconfiguration option
        self.hass.async_create_task(
            self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "reconfigure"},
                data={"previous_entry_id": entry_id}
            )
        )


class AdaptiveClimateDiagnosticSensor(SensorEntity):
    """Sensor entity for diagnostic information."""
    
    def __init__(self, coordinator, config_entry: ConfigEntry, device_info: DeviceInfo, 
                 sensor_key: str, name: str, unit: str | None = None):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._device_info = device_info
        self._sensor_key = sensor_key
        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_key}"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_native_unit_of_measurement = unit
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return self._device_info
    
    @property
    def native_value(self) -> Any:
        """Return sensor value."""
        if hasattr(self.coordinator, 'data') and self.coordinator.data:
            return self.coordinator.data.get(self._sensor_key)
        return None


class AdaptiveClimateConfigSensor(SensorEntity):
    """Sensor entity for configuration information."""
    
    def __init__(self, coordinator, config_entry: ConfigEntry, device_info: DeviceInfo, 
                 config_key: str, name: str):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._device_info = device_info
        self._config_key = config_key
        self._attr_name = name
        self._attr_unique_id = f"{config_entry.entry_id}_config_{config_key}"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return self._device_info
    
    @property
    def native_value(self) -> str | None:
        """Return config value."""
        value = self.config_entry.data.get(self._config_key)
        if value:
            # Return friendly name if it's an entity
            if "." in str(value):
                state = self.hass.states.get(value)
                if state:
                    return state.attributes.get("friendly_name", value)
            return str(value)
        return "Not configured"
