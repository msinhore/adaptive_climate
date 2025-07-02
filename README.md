# Adaptive Climate - ASHRAE 55 Custom Component

[![GitHub Release](https://img.shields.io/github/v/release/msinhore/adaptive-climate?style=for-the-badge)](https://github.com/msinhore/adaptive-climate/releases)
[![GitHub Activity](https://img.shields.io/github/commit-activity/y/msinhore/adaptive-climate?style=for-the-badge)](https://github.com/msinhore/adaptive-climate/commits/main)
[![License](https://img.shields.io/github/license/msinhore/adaptive-climate.svg?style=for-the-badge)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![Community Forum](https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge)](https://community.home-assistant.io)

A Home Assistant custom component that implements ASHRAE 55 adaptive comfort model for intelligent climate control with energy-saving features and natural ventilation detection.

**Development Version: 0.1.0**

## Overview

This component transforms your Home Assistant into an intelligent climate control system based on the ASHRAE 55 adaptive comfort standard. It automatically adjusts target temperatures based on outdoor conditions, detects optimal natural ventilation opportunities, and implements occupancy-based energy-saving strategies.

## Key Features

### ASHRAE 55 Adaptive Comfort Model
- Calculates optimal comfort temperatures using the adaptive model: `18.9 + 0.255 × Outdoor Temperature`
- Supports three comfort categories (I, II, III) with different tolerance levels
- Accounts for air velocity and humidity corrections
- Uses operative temperature when radiant temperature sensors are available

### Intelligent Climate Control
- Automatic HVAC mode optimization based on outdoor conditions
- Natural ventilation detection and recommendation  
- Adaptive fan speed control based on comfort requirements
- Manual override with automatic timeout functionality

### Energy Efficiency
- Occupancy-based setback with configurable temperature offsets
- Automatic system shutdown during extended absence periods
- Dynamic comfort zones that adapt to seasonal changes
- Natural ventilation prioritization when conditions are suitable

### Advanced Monitoring
- Real-time ASHRAE 55 compliance monitoring
- Diagnostic sensors for comfort temperature, ranges, and outdoor running mean
- Comprehensive logging for system optimization
- Rich attributes for integration with Home Assistant automations

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant
2. Go to **Integrations** → **⋮** → **Custom repositories**
3. Add repository URL: `https://github.com/msinhore/adaptive-climate`
4. Category: **Integration**
5. Search for "Adaptive Climate" and install
6. Restart Home Assistant

### Manual Installation

1. Download the latest release from GitHub
2. Extract to `custom_components/adaptive_climate/` in your config directory
3. Restart Home Assistant

## Configuration

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

### Basic Configuration

- **Name**: Unique name for your adaptive climate controller
- **Area**: Select the area to filter relevant entities
- **Climate Entity**: Target HVAC system or smart thermostat
- **Indoor Temperature Sensor**: Primary indoor temperature measurement
- **Outdoor Temperature Sensor**: External temperature for adaptive calculations
- **Comfort Category**: ASHRAE 55 category (I=±2°C, II=±3°C, III=±4°C)

### Advanced Options

- **Occupancy Sensor**: Motion or presence detection for energy savings
- **Humidity Sensor**: Indoor humidity for enhanced comfort calculations
- **Radiant Temperature Sensor**: For operative temperature calculations
- **Natural Ventilation Control**: Enable intelligent ventilation management
- **Adaptive Fan Speed**: Automatic fan speed optimization
- **Precision Mode**: High-accuracy calculations for critical environments

### Limits & Timeouts

- **Temperature Limits**: Minimum/maximum bounds for safety
- **Setback Settings**: Unoccupied temperature offsets and timers
- **Auto-off Timer**: Extended absence shutdown delay
- **Override Timeout**: Manual override automatic expiration

## Usage Examples

### Basic Smart Thermostat Control

The component automatically adjusts your thermostat based on outdoor temperature:

```yaml
# When outdoor temp = 20°C, comfort temp = 24.0°C
# When outdoor temp = 25°C, comfort temp = 25.3°C
# When outdoor temp = 30°C, comfort temp = 26.6°C
```

### Energy-Saving Automations

```yaml
automation:
  - alias: "Natural Ventilation Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.adaptive_climate_natural_ventilation_optimal
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Perfect weather for natural ventilation! Consider opening windows."

  - alias: "Comfort Zone Status"
    trigger:
      - platform: state
        entity_id: binary_sensor.adaptive_climate_ashrae_compliance
        to: "off"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.adaptive_climate
        data:
          temperature: "{{ state_attr('climate.adaptive_climate', 'comfort_temperature') }}"
```

### Dashboard Integration

```yaml
type: entities
entities:
  - entity: climate.adaptive_climate
  - entity: sensor.adaptive_climate_comfort_temperature
    name: "Optimal Temperature"
  - entity: sensor.adaptive_climate_comfort_range_min
    name: "Comfort Range Min"
  - entity: sensor.adaptive_climate_comfort_range_max  
    name: "Comfort Range Max"
  - entity: binary_sensor.adaptive_climate_ashrae_compliance
    name: "In Comfort Zone"
  - entity: binary_sensor.adaptive_climate_natural_ventilation_optimal
    name: "Natural Ventilation OK"
```

## Diagnostic Sensors

The component automatically creates diagnostic sensors:

| Sensor | Description | Unit |
|--------|-------------|------|
| `comfort_temperature` | ASHRAE 55 calculated optimal temperature | °C |
| `comfort_range_min` | Lower bound of comfort zone | °C |  
| `comfort_range_max` | Upper bound of comfort zone | °C |
| `outdoor_running_mean` | 7-day running mean of outdoor temperature | °C |
| `ashrae_compliance` | Current compliance with ASHRAE 55 standard | boolean |
| `natural_ventilation_optimal` | Natural ventilation recommended | boolean |

## Services

### `adaptive_climate.clear_override`
Clears any manual temperature override and returns to adaptive control.

### `adaptive_climate.set_comfort_category`
Changes the ASHRAE 55 comfort category.

```yaml
service: adaptive_climate.set_comfort_category
target:
  entity_id: climate.adaptive_climate
data:
  category: "I"  # I, II, or III
```

### `adaptive_climate.update_calculations`
Forces immediate recalculation of comfort parameters.

### `adaptive_climate.set_temporary_override`
Sets a temporary manual override with automatic expiration.

```yaml
service: adaptive_climate.set_temporary_override
target:
  entity_id: climate.adaptive_climate
data:
  temperature: 22
  duration: 3600  # seconds
```

## Compatibility

- **Home Assistant**: 2025.6.0+
- **Python**: 3.12+
- **HACS**: 2.0.0+
- **SmartIR**: Full compatibility with IR-controlled devices
- **Generic Thermostats**: Works with any Home Assistant climate entity

## Troubleshooting

### Common Issues

1. **Entity Not Found**: Ensure all selected entities exist and are available
2. **No Temperature Changes**: Check temperature change threshold settings
3. **HVAC Not Responding**: Verify climate entity supports the required services
4. **Occupancy Not Working**: Ensure occupancy sensor is properly configured

### Debug Logging

Add the following to your `configuration.yaml` for debug logging:

```yaml
logger:
  logs:
    custom_components.adaptive_climate: debug
```

## Support

- **Issues**: [GitHub Issues](https://github.com/msinhore/adaptive-climate/issues)
- **Discussions**: [GitHub Discussions](https://github.com/msinhore/adaptive-climate/discussions)
- **Community**: [Home Assistant Community Forum](https://community.home-assistant.io)

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests for any improvements.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Based on ASHRAE 55-2020 Adaptive Comfort Model
- Inspired by the CBE Thermal Comfort Tool
- Home Assistant community for testing and feedback

---

**Development Version**: 0.1.0
