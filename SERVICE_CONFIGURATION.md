# Adaptive Climate Integration - Service-Based Configuration

## Overview

This modernized version of the Adaptive Climate integration follows HA 2025.7+ best practices by consolidating all configuration parameters as attributes of the main binary sensor entities, with configuration management handled through Home Assistant services rather than proliferating control entities.

## What Changed

### Before (Old Approach)
- Multiple Number, Switch, Select, and Button entities cluttered the device page
- Each parameter had its own entity (20+ entities total)
- Configuration via entity controls and OptionsFlow
- Absolute min/max temperature entities (non-standard)

### After (New Approach)
- **Clean device page**: Only 4 essential entities visible
  - `binary_sensor.{name}_ashrae_compliance` (main status + all config as attributes)
  - `binary_sensor.{name}_natural_ventilation_optimal` (ventilation recommendations)
  - `sensor.{name}_adaptive_comfort_temperature` (calculated comfort temp)
  - `sensor.{name}_outdoor_running_mean` (7-day outdoor average)
- **All configuration as attributes**: 19+ parameters visible in the main binary sensor attributes
- **Service-based management**: 4 services for complete control
- **Standard ASHRAE limits**: Only user-configurable min/max comfort temp (18-30°C)

## Available Services

### 1. `adaptive_climate.set_parameter`
Set any configurable parameter:
```yaml
service: adaptive_climate.set_parameter
data:
  entity_id: binary_sensor.adaptive_climate_living_room_ashrae_compliance
  parameter: min_comfort_temp
  value: 19.5
```

### 2. `adaptive_climate.reset_parameter`
Reset a parameter to its default value:
```yaml
service: adaptive_climate.reset_parameter
data:
  entity_id: binary_sensor.adaptive_climate_living_room_ashrae_compliance
  parameter: comfort_category
```

### 3. `adaptive_climate.set_manual_override`
Temporarily override with manual temperature control:
```yaml
service: adaptive_climate.set_manual_override
data:
  entity_id: binary_sensor.adaptive_climate_living_room_ashrae_compliance
  temperature: 22.5
  duration_hours: 2
```

### 4. `adaptive_climate.clear_manual_override`
Return to adaptive control:
```yaml
service: adaptive_climate.clear_manual_override
data:
  entity_id: binary_sensor.adaptive_climate_living_room_ashrae_compliance
```

## Configurable Parameters

All parameters are visible as attributes on the single binary sensor and editable via services:

### Temperature Limits (18-30°C range for safety)
- `min_comfort_temp`: Minimum comfort temperature (default: 18.0°C)
- `max_comfort_temp`: Maximum comfort temperature (default: 30.0°C)
- `temperature_change_threshold`: Minimum change to trigger adjustment (default: 0.5°C)

### ASHRAE Comfort Settings
- `comfort_category`: I/II/III (default: "II")
- `comfort_precision_mode`: Tighter control (default: false)
- `use_operative_temperature`: Use operative vs air temp (default: false)

### Air Movement
- `air_velocity`: Indoor air speed (default: 0.1 m/s)
- `adaptive_air_velocity`: Enable adaptive fan control (default: false)
- `natural_ventilation_threshold`: Temp diff for natural vent (default: 2.0°C)
- `natural_ventilation_enable`: Enable natural vent features (default: true)

### Occupancy & Energy Saving
- `setback_temperature_offset`: Unoccupied offset (default: 2.0°C)
- `prolonged_absence_minutes`: Minutes before setback (default: 60)
- `auto_shutdown_minutes`: Minutes before shutdown (default: 180)
- `auto_shutdown_enable`: Enable auto shutdown (default: false)
- `energy_save_mode`: Enable energy saving (default: true)
- `use_occupancy_features`: Use occupancy sensor (default: true)

### Advanced Comfort Zone Tuning
- `comfort_temp_min_offset`: Negative offset for min range (default: -2.5°C)
- `comfort_temp_max_offset`: Positive offset for max range (default: 2.5°C)
- `humidity_comfort_enable`: Enable humidity corrections (default: true)

## Usage Examples

### Quick Parameter Changes
```yaml
# Make system more aggressive (smaller threshold)
service: adaptive_climate.set_parameter
data:
  entity_id: binary_sensor.adaptive_climate_bedroom_ashrae_compliance
  parameter: temperature_change_threshold
  value: 0.2

# Switch to Category I (most precise)
service: adaptive_climate.set_parameter
data:
  entity_id: binary_sensor.adaptive_climate_bedroom_ashrae_compliance
  parameter: comfort_category
  value: "I"

# Enable auto shutdown after 3 hours
service: adaptive_climate.set_parameter
data:
  entity_id: binary_sensor.adaptive_climate_bedroom_ashrae_compliance
  parameter: auto_shutdown_enable
  value: true

service: adaptive_climate.set_parameter
data:
  entity_id: binary_sensor.adaptive_climate_bedroom_ashrae_compliance
  parameter: auto_shutdown_minutes
  value: 180
```

### Automation Example
```yaml
automation:
  - alias: "Bedtime comfort adjustment"
    trigger:
      platform: time
      at: "22:00:00"
    action:
      - service: adaptive_climate.set_parameter
        data:
          entity_id: binary_sensor.adaptive_climate_bedroom_ashrae_compliance
          parameter: comfort_category
          value: "I"  # More precise control for sleep
      - service: adaptive_climate.set_parameter
        data:
          entity_id: binary_sensor.adaptive_climate_bedroom_ashrae_compliance
          parameter: max_comfort_temp
          value: 24.0  # Cooler max for sleep
```

## Migration Notes

If upgrading from the old entity-based version:
1. **Remove old automations** that controlled Number/Switch entities
2. **Update scripts** to use the new services
3. **Check templates** that referenced old entity states
4. **Configuration will be preserved** but moved to service-based management

## Benefits

- **Cleaner UI**: Device page shows only essential status information
- **Better UX**: All configuration in one place (binary sensor attributes)
- **Standards compliance**: Follows HA 2025.7+ integration patterns
- **Service-oriented**: Proper HA service architecture
- **Safety**: Built-in 18-30°C limits prevent dangerous temperatures
- **Flexibility**: All parameters still fully configurable via services
- **Future-proof**: Aligns with Home Assistant's architectural direction
