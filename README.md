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

A Home Assistant integration implementing ASHRAE 55 Adaptive Thermal Comfort for intelligent climate control.

---

## 🚀 Features

- 🔍 **ASHRAE 55 Adaptive Comfort**: Automatically adjusts comfort temperature using adaptive thermal comfort calculations, based on scientific standards.

- 🌡️ **Temperature and Humidity Monitoring**: Uses indoor/outdoor temperature sensors, and optionally humidity sensors, for precision climate control.

- 📊 **Running Mean Outdoor Temperature**: Tracks and computes historical outdoor temperatures to apply adaptive comfort adjustments.

- 🏖️ **Automatic Season Detection**: Dynamically detects seasons (summer, winter, spring, autumn) for contextual HVAC decisions.

- 🌀 **HVAC and Fan Control**: Automatically adjusts climate modes (cool, heat, fan_only, dry, off) and fan speeds based on real-time calculations.

- 📈 **Energy Save Mode**: Optimizes energy usage without compromising comfort. Must be explicitly enabled by the user.

- 🕹️ **Manual Override Detection**: Detects and respects manual user interventions, pausing automatic control when user takes manual control.

- 🛑 **User Power-off Handling**: If the user manually powers off the climate device, automatic control pauses until user powers it back on.

- 🔄 **Persistent State Memory**: Retains last states and control history across Home Assistant restarts.

- ☀️ **Solar Radiation Adjustment**: Optional correction factor applied based on estimated solar radiation levels, useful for compensating solar heat gains through roofs or walls.

- 📝 **Detailed Logging**: Records comfort calculations, HVAC decisions, and control logic for transparency and debugging.

- ⚙️ **Fully UI Configurable**: All configuration via Home Assistant options flow.

- 🌍 **Multi-language Support**: UI and entities available in multiple languages.

---

## 📊 Entities Provided

- **Binary Sensor**: ASHRAE Compliance
- **Select**: Comfort Category (I or II)
- **Switches**:
  - Energy Save Mode
  - Auto Mode

---

## 📦 Installation

### Via HACS (Recommended)

1. Install [HACS](https://hacs.xyz/)
2. Add this repository as a custom integration
3. Install "Adaptive Climate"
4. Restart Home Assistant
5. Add integration via Settings → Devices & Services → Add Integration → Adaptive Climate

---

## ⚙️ Configuration

- **Required**:
  - Climate Entity
  - Indoor Temperature Sensor
  - Outdoor Temperature Sensor

- **Optional**:
  - Indoor Humidity Sensor
  - Outdoor Humidity Sensor

All other options, including solar radiation adjustment, are configurable via the Home Assistant UI.

### Configuration Options Explained

| Option                                  | Description |
|-----------------------------------------|-------------|
| **ASHRAE 55 Comfort Category**          | Category I (90% satisfaction) or II (80% satisfaction) for stricter or looser comfort bounds. |
| **Enable Energy Saving Mode**           | Reduces HVAC usage by prioritizing ventilation and comfort tolerance. Must be manually enabled. |
| **Enable Auto Mode**                    | Enables autonomous operation. Disable for fully manual control. |
| **Minimum Comfort Temperature (°C)**   | Lower limit for calculated comfort temperature (default: 18°C). |
| **Maximum Comfort Temperature (°C)**   | Upper limit for calculated comfort temperature (default: 28°C). |
| **Temperature Change Threshold (°C)**  | Minimum temperature delta to trigger a new setpoint change (default: 0.5°C). Prevents unnecessary changes. |
| **Override Temperature (°C)**          | Manual adjustment applied to the calculated comfort temperature (example: -1 for cooler targets). |
| **Aggressive Cooling Threshold (°C)**  | Defines how strongly the system responds to overheating (default: 2°C). |
| **Aggressive Heating Threshold (°C)**  | Defines how strongly the system responds to overcooling (default: 2°C). |
| **Radiation Adjustment Factor**        | Factor applied to adjust the comfort temperature based on estimated solar radiation impact. Useful to compensate for sunlight heating specific areas like roofs or walls. Example: 0.05 to slightly increase target temperature during strong sunlight. |

---

## 📈 How It Works

<img width="2561" height="1101" alt="image" src="https://github.com/user-attachments/assets/98451b40-a040-4420-993d-5d64a851d31e" />

- Continuously monitors temperatures and humidity.
- Calculates adaptive comfort targets using ASHRAE 55.
- Controls HVAC and fan modes to optimize comfort.
- Tracks outdoor temperature history for accurate adaptive calculations.
- Detects and respects manual interventions.
- Energy saving behaviors are applied when explicitly enabled.

---

## ℹ️ Notes

- Supports **one climate entity** (multi-device support planned for v2.x).
- Prioritizes user control: never powers on devices after user shutdown.
- Does not perform fixed setpoint control: adapts dynamically to external and internal conditions.

---

## 🏛️ Standards & References

- **ASHRAE Standard 55-2020** - Thermal Environmental Conditions for Human Occupancy.
- **pythermalcomfort** library for scientific adaptive comfort calculations.

---

## 📄 License

MIT License – see [LICENSE](LICENSE).
