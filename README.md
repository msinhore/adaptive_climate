# Adaptive Climate

A Home Assistant integration that implements ASHRAE 55 Adaptive Thermal Comfort standards for intelligent climate control.

## What it does

Adaptive Climate automatically calculates optimal indoor temperatures based on outdoor conditions, following scientific comfort standards. Instead of fixed temperature setpoints, it adapts to weather patterns to improve comfort while reducing energy consumption.

## Problem it solves

Traditional thermostats use static temperature settings that don't account for:
- Seasonal adaptation (people feel comfortable at different temperatures in summer vs winter)
- Outdoor temperature influence on comfort perception
- Energy waste from over-heating or over-cooling
- Lack of scientific basis for temperature choices

## How it works

The integration:
1. Monitors indoor and outdoor temperatures
2. Calculates adaptive comfort zones using ASHRAE 55 standards
3. Provides 21 entities to control and monitor your climate system
4. Suggests optimal HVAC modes (heating, cooling, off) based on real comfort science
5. Tracks compliance with international comfort standards

## Installation

### Via HACS (Recommended)
1. Install [HACS](https://hacs.xyz/) if not already installed
2. Go to HACS → Integrations → ⋮ → Custom repositories
3. Add this repository URL and select "Integration"
4. Install "Adaptive Climate"
5. Restart Home Assistant
6. Go to Settings → Devices & Services → Add Integration → "Adaptive Climate"

### Manual Installation
1. Download the latest release
2. Extract to `custom_components/adaptive_climate/` in your HA config directory
3. Restart Home Assistant
4. Add via Settings → Devices & Services → Add Integration

## Configuration

### Required
- **Climate entity**: Your AC/heating system (e.g., `climate.living_room`)
- **Indoor temperature sensor**: Room temperature (e.g., `sensor.living_room_temperature`)
- **Outdoor temperature sensor**: Outside temperature (e.g., `sensor.outdoor_temperature`)

### Optional
- Indoor/outdoor humidity sensors
- Occupancy sensor
- Mean radiant temperature sensor
- Air velocity sensor

## What you get

### Information entities (6)
- **ASHRAE Compliance**: Binary sensor showing if current conditions meet comfort standards
- **Comfort sensors**: Calculated comfort temperature, HVAC recommendations, fan speeds, etc.

### Control entities (15)
- **Temperature controls**: Min/max comfort temperatures, thresholds
- **Feature toggles**: Energy saving, natural ventilation, precision mode
- **Comfort category**: ASHRAE categories I, II, or III (strictness levels)

## Usage

1. **Basic monitoring**: Check the compliance sensor to see if your space is comfortable
2. **Automatic control**: Use the HVAC recommendation sensor in automations
3. **Fine-tuning**: Adjust the 15 control entities via the device page or configuration options
4. **Energy saving**: Enable energy save mode for automatic setback temperatures

## Automation example

```yaml
automation:
  - alias: "Adaptive Climate Control"
    trigger:
      - platform: state
        entity_id: sensor.adaptive_climate_hvac_recommendation
    action:
      - service: climate.set_hvac_mode
        target:
          entity_id: climate.living_room
        data:
          hvac_mode: "{{ states('sensor.adaptive_climate_hvac_recommendation') }}"
```

## Supported languages

English, Portuguese (Brazil), Italian, French, Spanish, German

## Technical details

- Based on ASHRAE 55-2020 Adaptive Thermal Comfort model
- Updates every minute or when sensor values change
- Stores 7-day outdoor temperature history for running mean calculations
- Uses CoordinatorEntity pattern for efficient data management
- Fallback calculations when external libraries are unavailable

## Support

- [Issues](https://github.com/yourusername/adaptive_climate/issues): Bug reports and feature requests
- [Discussions](https://github.com/yourusername/adaptive_climate/discussions): Questions and community support

## License

MIT License - see [LICENSE](LICENSE) file for details.