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

A Home Assistant integration implementing ASHRAE 55 Adaptive Thermal Comfort for intelligent climate control with advanced HVAC and fan mode management.

---

## 🚀 Features

### **Core Functionality**
- 🔍 **ASHRAE 55 Adaptive Comfort**: Automatically adjusts comfort temperature using adaptive thermal comfort calculations, based on scientific standards.
- 🌡️ **Temperature and Humidity Monitoring**: Uses indoor/outdoor temperature sensors, and optionally humidity sensors, for precision climate control.
- 📊 **Running Mean Outdoor Temperature**: Tracks and computes historical outdoor temperatures to apply adaptive comfort adjustments.
- 🏖️ **Automatic Season Detection**: Dynamically detects seasons (summer, winter, spring, autumn) for contextual HVAC decisions.

### **Advanced HVAC Control**
- 🌀 **HVAC Mode Management**: Automatically adjusts climate modes (cool, heat, fan_only, dry, off) based on real-time calculations.
- 🎛️ **Selective Mode Control**: Enable/disable specific HVAC modes (cool, heat, fan_only, dry) for device-specific control.
- 🌪️ **Fan Speed Management**: Automatic fan speed adjustment with configurable min/max limits.
- 📈 **Energy Save Mode**: Optimizes energy usage without compromising comfort. Must be explicitly enabled by the user.

### **Smart Control & Detection**
- 🕹️ **Manual Override Detection**: Detects and respects manual user interventions, pausing automatic control when user takes manual control.
- 🛑 **User Power-off Handling**: If the user manually powers off the climate device, automatic control pauses until user powers it back on.
- 🔄 **Persistent State Memory**: Retains last states and control history across Home Assistant restarts.
- ⚡ **Optimized Startup**: Immediate control cycle during startup for faster response when auto mode is enabled.

### **Advanced Services**
- 🎯 **Manual Override Services**: Set and clear manual temperature overrides with optional duration.
- 📊 **Comfort Category Control**: Dynamically change comfort settings via services.
- ⏱️ **Temporary Override**: Time-limited temperature changes for specific periods.
- 🔄 **Calculation Updates**: Force recalculation and control updates via services.

### **Enhanced Debugging**
- 📝 **Device Identification**: All logs include device name for better identification.
- 🔍 **Detailed Calculation Logs**: Comprehensive logging of comfort calculation inputs and decisions.
- 🎯 **Action Mapping Logs**: Detailed logs showing how calculated modes are mapped to device capabilities.
- 📊 **State Change Tracking**: Enhanced logging of device state changes and control decisions.

### **User Experience**
- ⚙️ **Fully UI Configurable**: All configuration via Home Assistant options flow.
- 🌍 **Multi-language Support**: UI and entities available in multiple languages.
- 📱 **Reduced Logbook Verbosity**: Essential logs only, focused on AC changes and mode transitions.

---

## 📊 Entities Provided

### **Binary Sensors**
- **ASHRAE Compliance**: Indicates if current conditions meet ASHRAE 55 comfort standards

### **Select Entities**
- **Comfort Category**: Choose between Category I (90% satisfaction) or II (80% satisfaction)

### **Switch Entities**
- **Energy Save Mode**: Enable/disable energy optimization mode
- **Auto Mode**: Enable/disable automatic climate control

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

### **Required Configuration**
- **Climate Entity**: Your main HVAC/climate device
- **Indoor Temperature Sensor**: Sensor for indoor temperature monitoring
- **Outdoor Temperature Sensor**: Sensor for outdoor temperature monitoring

### **Optional Configuration**
- **Indoor Humidity Sensor**: Sensor for indoor humidity monitoring
- **Outdoor Humidity Sensor**: Sensor for outdoor humidity monitoring

### **Advanced Configuration Options**

#### **Comfort Settings**
| Option | Description | Default | Range |
|--------|-------------|---------|-------|
| **ASHRAE 55 Comfort Category** | Category I (90% satisfaction) or II (80% satisfaction) for stricter or looser comfort bounds | I | I/II |
| **Minimum Comfort Temperature** | Lower limit for calculated comfort temperature | 21°C | 10-30°C |
| **Maximum Comfort Temperature** | Upper limit for calculated comfort temperature | 27°C | 15-35°C |
| **Temperature Change Threshold** | Minimum temperature delta to trigger a new setpoint change | 0.5°C | 0.1-5.0°C |
| **Override Temperature** | Manual adjustment applied to the calculated comfort temperature | 0°C | -2.0 to 2.0°C |

#### **Control Thresholds**
| Option | Description | Default | Range |
|--------|-------------|---------|-------|
| **Aggressive Cooling Threshold** | Defines how strongly the system responds to overheating | 2.0°C | 0.5-10.0°C |
| **Aggressive Heating Threshold** | Defines how strongly the system responds to overcooling | 2.0°C | 0.5-10.0°C |

#### **HVAC Mode Control**
| Option | Description | Default |
|--------|-------------|---------|
| **Enable Cool Mode** | Allow the system to use cooling mode | ✅ Enabled |
| **Enable Heat Mode** | Allow the system to use heating mode | ✅ Enabled |
| **Enable Fan Mode** | Allow the system to use fan-only mode | ✅ Enabled |
| **Enable Dry Mode** | Allow the system to use dehumidification mode | ✅ Enabled |

#### **Fan Speed Control**
| Option | Description | Default | Options |
|--------|-------------|---------|---------|
| **Minimum Fan Speed** | Lowest fan speed the system can use | Low | Low/Mid/High/Highest |
| **Maximum Fan Speed** | Highest fan speed the system can use | High | Low/Mid/High/Highest |

#### **System Control**
| Option | Description | Default |
|--------|-------------|---------|
| **Enable Energy Save Mode** | Reduces HVAC usage by prioritizing ventilation and comfort tolerance | ✅ Enabled |
| **Enable Auto Mode** | Enables autonomous operation. Disable for fully manual control | ✅ Enabled |

---

## 🔧 Services

### **Configuration Services**

#### `adaptive_climate.set_parameter`
Set a configurable parameter for Adaptive Climate.

**Parameters:**
- `entity_id`: Adaptive Climate binary sensor entity ID
- `parameter`: Configuration parameter to set
- `value`: New value for the parameter

**Available Parameters:**
- `min_comfort_temp`: Minimum Comfort Temperature (18-30°C)
- `max_comfort_temp`: Maximum Comfort Temperature (18-30°C)
- `temperature_change_threshold`: Temperature Change Threshold (0.1-5.0°C)
- `override_temperature`: Override Temperature (-2.0 to 2.0°C)
- `comfort_category`: Comfort Category (I/II)
- `energy_save_mode`: Energy Save Mode (boolean)
- `auto_mode_enable`: Auto Mode Enable (boolean)

#### `adaptive_climate.reset_parameter`
Reset a parameter to its default value.

**Parameters:**
- `entity_id`: Adaptive Climate binary sensor entity ID
- `parameter`: Configuration parameter to reset

### **Override Services**

#### `adaptive_climate.set_manual_override`
Set manual temperature override with optional duration.

**Parameters:**
- `entity_id`: Adaptive Climate binary sensor entity ID
- `temperature`: Target temperature for override (10-40°C)
- `duration_hours`: Override duration in hours (0 = permanent until cleared)

#### `adaptive_climate.clear_manual_override`
Clear manual override and restore automatic control.

**Parameters:**
- `entity_id`: Adaptive Climate binary sensor entity ID

#### `adaptive_climate.set_temporary_override`
Set temporary temperature override for a specific duration.

**Parameters:**
- `entity_id`: Adaptive Climate binary sensor entity ID
- `temperature`: Target temperature for override (10-40°C)
- `duration_minutes`: Override duration in minutes (1-1440)

### **Control Services**

#### `adaptive_climate.set_comfort_category`
Dynamically change comfort category setting.

**Parameters:**
- `entity_id`: Adaptive Climate binary sensor entity ID
- `category`: Comfort category (I or II)

#### `adaptive_climate.update_calculations`
Force recalculation and control updates.

**Parameters:**
- `entity_id`: Adaptive Climate binary sensor entity ID

---

## 📈 How It Works

<img width="2561" height="1101" alt="image" src="https://github.com/user-attachments/assets/98451b40-a040-4420-993d-5d64a851d31e" />

### **Process Flow**
1. **Continuous Monitoring**: Monitors temperatures and humidity in real-time
2. **ASHRAE 55 Calculation**: Calculates adaptive comfort targets using scientific standards
3. **Season Detection**: Automatically detects current season for contextual decisions
4. **HVAC Mode Selection**: Chooses optimal HVAC mode based on comfort needs and device capabilities
5. **Fan Speed Optimization**: Adjusts fan speed within configured limits
6. **Device Control**: Applies calculated settings to climate device
7. **Override Detection**: Monitors for manual user interventions
8. **State Persistence**: Saves control history across restarts

### **Key Features**
- **Adaptive Comfort**: Uses ASHRAE 55 standard for scientific comfort calculations
- **Device Compatibility**: Maps calculated modes to device-supported modes
- **Energy Optimization**: Reduces energy usage when explicitly enabled
- **User Respect**: Never overrides manual user control
- **Fast Startup**: Immediate control cycle when auto mode is enabled

---

## 🔍 Debugging & Logging

### **Enhanced Debug Information**
- **Device Identification**: All logs include device name for easy identification
- **Calculation Details**: Comprehensive logging of comfort calculation inputs and results
- **Action Mapping**: Detailed logs showing mode mapping to device capabilities
- **State Changes**: Enhanced tracking of device state changes and control decisions

### **Logbook Optimization**
- **Reduced Verbosity**: Focused on essential information only
- **Concise Messages**: Clear, informative logbook entries
- **Essential Events**: AC changes and manual/auto mode transitions

---

## ℹ️ Notes

- **Single Device Support**: Currently supports one climate entity (multi-device support planned for v2.x)
- **User Control Priority**: Never powers on devices after user shutdown
- **Dynamic Adaptation**: Adapts to external and internal conditions, not fixed setpoints
- **Backward Compatibility**: All existing configurations continue to work without changes

---

## 🏛️ Standards & References

- **ASHRAE Standard 55-2020** - Thermal Environmental Conditions for Human Occupancy
- **pythermalcomfort** library for scientific adaptive comfort calculations

---

## 📄 License

MIT License – see [LICENSE](LICENSE).
