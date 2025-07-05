# Adaptive Climate

> **Warning**
> 
> Adaptive Climate is under active development. Features and behavior may change, and some functions may not work correctly in all scenarios. Use with caution and report any issues you encounter.

A Home Assistant integration that implements ASHRAE 55 Adaptive Thermal Comfort standards for intelligent climate control.

## What it does

Adaptive Climate intelligently manages your climate system using a scientific, adaptive approach. It:

- Continuously monitors indoor temperature, outdoor temperature, radiant temperature (if available), and occupancy sensors.
- Detects the current season based on your latitude and date, adapting comfort logic for summer and winter.
- Uses user-configurable minimum and maximum comfort temperature ranges.
- Applies the ASHRAE 55-2020 Adaptive Thermal Comfort model to determine the optimal comfort zone for your environment.
- Automatically sets your AC or heater to the most appropriate mode (cool, heat, fan, or off) to maintain comfort and save energy.
- Dynamically controls fan speed (air velocity) to improve comfort, even without changing the setpoint temperature.
- Turns off the climate system when not needed (e.g., when the space is unoccupied or already within the comfort zone).
- Integrates all available sensor data (temperature, humidity, radiant temperature, occupancy, etc.) for precise, science-based comfort decisions.
- Ensures all actions are based on international comfort standards, not just fixed setpoints.

Instead of fixed temperature setpoints, Adaptive Climate adapts to weather, season, and occupancy to improve comfort and reduce energy consumption, providing a truly intelligent and scientific climate control experience.

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
- Uses pythermalcomfort library algorithms for scientific accuracy
- Updates every minute or when sensor values change
- Stores 7-day outdoor temperature history for running mean calculations
- Uses CoordinatorEntity pattern for efficient data management
- Compatible with Python 3.13+ through patched implementation

## Scientific Citation

This integration implements adaptive thermal comfort calculations based on the pythermalcomfort library. If you use this integration in research or academic work, please cite:

**Tartarini, F., Schiavon, S., 2020.**  
*pythermalcomfort: A Python package for thermal comfort research.*  
SoftwareX 12, 100578.  
https://doi.org/10.1016/j.softx.2020.100578

The adaptive comfort calculations follow ASHRAE Standard 55-2020 implementations as provided by the Center for the Built Environment, UC Berkeley.

## Acknowledgments

- **pythermalcomfort**: Scientific thermal comfort algorithms ([GitHub](https://github.com/CenterForTheBuiltEnvironment/pythermalcomfort))
- **ASHRAE Standard 55-2020**: Thermal Environmental Conditions for Human Occupancy
- **CBE Comfort Tool**: Reference implementation ([comfort.cbe.berkeley.edu](https://comfort.cbe.berkeley.edu/))

## Support

- [Issues](https://github.com/msinhore/adaptive_climate/issues): Bug reports and feature requests
- [Discussions](https://github.com/msinhore/adaptive_climate/discussions): Questions and community support

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Architecture Diagram

<div style="height: 420px;">

```mermaid
graph TD
    subgraph Sensors
        OUT["Outdoor Temp Sensor"]
        IN["Indoor Temp Sensor"]
        RAD["Radiant Temp Sensor"]
        OUT_HUM["Outdoor Humidity Sensor"]
        IN_HUM["Indoor Humidity Sensor"]
        OCC["Occupancy Sensor"]
    end
    USER["User Settings (Comfort Range, Preferences)"]
    SEASON["Season Detector (Latitude + Date)"]
    ASHRAE["ASHRAE 55-2020 Comfort Model"]
    AC["Climate Device (AC/Heater/Fan)"]
    HA["Adaptive Climate Integration"]

    OUT --> HA
    IN --> HA
    RAD --> HA
    OUT_HUM --> HA
    IN_HUM --> HA
    OCC --> HA
    USER --> HA
    SEASON --> HA
    ASHRAE --> HA
    HA --> AC
    AC -- "State Feedback" --> HA
```
</div>