# Adaptive Climate
[![hacs_badge](https://img.shields.io/badge/HACS-Default-blue.svg?style=flat-square)](https://github.com/hacs/integration)
[![CI](https://github.com/msinhore/adaptive_climate/actions/workflows/ci.yml/badge.svg)](https://github.com/msinhore/adaptive_climate/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/msinhore/adaptive_climate?label=release&sort=semver&logo=github)](https://github.com/msinhore/adaptive_climate/releases)
[![Downloads](https://img.shields.io/github/downloads/msinhore/adaptive_climate/total)](https://github.com/msinhore/adaptive_climate/releases)
[![Stars](https://img.shields.io/github/stars/msinhore/adaptive_climate?style=flat-square)](https://github.com/msinhore/adaptive_climate/stargazers)
[![Licence](https://img.shields.io/github/license/msinhore/adaptive_climate.svg)](https://github.com/msinhore/adaptive_climate/blob/main/LICENSE)
[![Last commit](https://img.shields.io/github/last-commit/msinhore/adaptive_climate.svg)](https://github.com/msinhore/adaptive_climate)
![Project Status](https://img.shields.io/badge/status-active-brightgreen.svg)


[<img width="170" height="37" alt="Buy me a coffee" src="https://github.com/user-attachments/assets/0ce08a2b-1bc6-4f16-91f0-70c273cf4d47" />](https://buymeacoffee.com/msinhore)

A Home Assistant integration that implements ASHRAE 55 Adaptive Thermal Comfort standards for intelligent climate control.

![image](https://github.com/user-attachments/assets/e09bceeb-1794-44cc-9d94-98ff4471c57f)

## 🚀 What it does

**Adaptive Climate** intelligently manages your climate system with a scientific adaptive approach. It offers:

🌡️ **Continuous Monitoring:** Tracks indoor temperature, outdoor temperature, radiant temperature (if available), and humidity sensors.  
🌎 **Automatic Season Detection:** Detects the current season based on your latitude and date, adapting comfort logic for summer, winter, spring, and autumn.  
🎯 **Configurable Comfort Ranges:** Sets minimum and maximum comfort temperature limits.  
📐 **ASHRAE 55-2020 Model:** Uses the Adaptive Thermal Comfort model to determine optimal comfort zones.  
🤖 **Automatic HVAC Control:** Adjusts AC or heating to cool, heat, fan, dry, or off to optimize comfort and energy savings.  
💨 **Dynamic Fan Speed:** Controls fan speed (air velocity) to improve comfort without changing temperature setpoints.  
🌱 **Energy Save Mode:** Disables HVAC in summer when indoor temperature is below the comfort minimum.  
⏳ **Auto Shutdown:** Turns off the climate system after a configurable absence time.  
🔄 **Auto Start:** Restarts the climate system automatically after presence returns, with configurable delay.  
🕹️ **User Override:** Any manual change (mode, temperature, fan) pauses automatic control for a user-defined time, with state persistence across restarts.  
🧠 **Full Sensor Integration:** Uses temperature, humidity, and radiant temperature data for science-based decisions.  
📊 **Running Mean Outdoor Temperature:** Stores outdoor temperature history for accurate adaptive calculations.  
🌐 **International Comfort Standards:** Actions are based on global standards, not just fixed setpoints.  
📝 **Advanced Logging:** Logs all comfort calculations, actions, and override events in detail.  
🛠️ **UI Configuration:** All options (comfort range, shutdown, override, etc.) are configurable via Home Assistant UI.  
🌍 **Multi-language Support:** Supports multiple languages for UI and entity names.  
💾 **State Persistence:** Maintains state (including overrides and system-off state) across Home Assistant restarts.  
🙋 **User Respect:** Never turns on the AC if the user turned it off manually.  
- **Pure Home Assistant Control:** Uses standard entities (selects, switches, binary sensors), no proprietary APIs.

Instead of fixed temperature setpoints, Adaptive Climate adapts to weather, season, and occupancy to improve comfort and reduce energy consumption, providing a truly intelligent and scientific climate control experience.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=msinhore&repository=adaptive_climate)

## Problem it solves

Traditional thermostats use static temperature settings that don't account for:

- Seasonal adaptation (people feel comfortable at different temperatures in summer vs winter)
- Outdoor temperature influence on comfort perception
- Energy waste from over-heating or over-cooling
- Lack of scientific basis for temperature choices

## How it works

The integration:

1. Monitors indoor and outdoor temperatures, humidity, and optional radiant temperature.
2. Calculates adaptive comfort zones using ASHRAE 55 standards and pythermalcomfort.
3. Provides real Home Assistant entities to control and monitor your climate system:
   - Binary sensor: ASHRAE compliance
	- **Select entity:** Comfort category (I, II, III)
	- **Number entities (8):** min/max comfort temps, air velocity, temperature change threshold, natural ventilation threshold, setback offset, auto shutdown minutes
	- **Switch entities (4):** energy save mode, natural ventilation enable, auto shutdown enable
4. Suggests optimal HVAC modes (heating, cooling, fan only, dry, humidify, off) based on real comfort science.
5. Tracks compliance with international comfort standards.

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
- Mean radiant temperature sensor
- Air velocity sensor

## 📊 Entities Provided

- **Binary Sensor:** ASHRAE Compliance  
- **Select:** Comfort Category (I or II)  
- **Switches:**  
  - Energy Save Mode  
  - Auto Mode  

All configuration is now handled via the UI options flow.

**Note:** Currently, only a single climate entity is supported as the controlled device. Support for multiple categorized devices (primary/auxiliary, summer/winter) is planned for version 2.x including switches and fan entities.

## Usage

1. **Basic monitoring**: Check the compliance sensor to see if your space is comfortable
2. **Automatic control**: Use the HVAC recommendation sensor in automations
3. **Fine-tuning**: Adjust the control entities via the device page or configuration options
4. **Energy saving**: Enable energy save mode for automatic HVAC off when comfort is met
5. **Manual override**: Set a manual temperature with expiry to temporarily override automatic control

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