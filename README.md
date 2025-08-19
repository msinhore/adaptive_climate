# Adaptive Climate
[![hacs_badge](https://img.shields.io/badge/HACS-Default-blue.svg?style=flat-square)](https://github.com/hacs/integration)
[![CI](https://github.com/msinhore/adaptive_climate/actions/workflows/ci.yml/badge.svg)](https://github.com/msinhore/adaptive_climate/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/msinhore/adaptive_climate?label=release&sort=semver&logo=github)](https://github.com/msinhore/adaptive_climate/releases)
[![Downloads](https://img.shields.io/github/downloads/msinhore/adaptive_climate/total)](https://github.com/msinhore/adaptive_climate/releases)
[![Stars](https://img.shields.io/github/stars/msinhore/adaptive_climate?style=flat-square)](https://github.com/msinhore/adaptive_climate/stargazers)
[![Licence](https://img.shields.io/github/license/msinhore/adaptive_climate.svg)](https://github.com/msinhore/adaptive_climate/blob/main/LICENSE)
[![Last commit](https://img.shields.io/github/last-commit/msinhore/adaptive_climate.svg)](https://github.com/msinhore/adaptive_climate)
![Project Status](https://img.shields.io/badge/status-active-brightgreen.svg)

[<img width="170" height="37" alt="Buy me a coffee" src="https://github.com/user-attachments/assets/0ce08a2b-1c6-4f16-91f0-70c273cf4d47" />](https://buymeacoffee.com/msinhore)

A Home Assistant integration implementing ASHRAE 55 Adaptive Thermal Comfort for intelligent climate control with advanced HVAC and fan mode management, featuring multi-device support and area-based automation.

---

## 🌟 **Features**

### **Core Functionality**
- 🔍 **ASHRAE 55 Adaptive Comfort**: Automatically adjusts comfort temperature using adaptive thermal comfort calculations, based on scientific standards.
- 🌡️ **Temperature and Humidity Monitoring**: Uses indoor/outdoor temperature sensors or weather entities, and optionally humidity sensors, for precision climate control.
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
- 🔧 **Device Capability Re-detection**: Force re-detection of device capabilities.

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

### **Configuration Methods**

Adaptive Climate now offers three flexible setup methods to accommodate different user preferences and scenarios:

#### **1. Area-Based Setup (Recommended)**
**Best for**: Users with multiple climate devices in the same area (e.g., living room with AC and ceiling fan)
- Select an area and the system automatically discovers all climate devices
- Creates individual configurations for each device while sharing sensor data
- Perfect for coordinated climate control within rooms

#### **2. Bulk Multi-Device Setup**
**Best for**: Users with multiple climate devices across different areas sharing the same sensors
- Select multiple climate entities manually
- Apply consistent settings across all devices
- Ideal for whole-home climate management

#### **3. Single Device Setup**
**Best for**: Simple single-device configurations or fine-tuned individual control
- Configure one climate device at a time
- Full control over individual device settings
- Perfect for testing or specific device requirements

#### **UI Configuration (Recommended)**
1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Adaptive Climate"
3. Choose your preferred setup method:
   - **Area Setup**: Select an area and let the system discover devices
   - **Bulk Setup**: Select multiple climate devices manually
   - **Single Setup**: Configure one device at a time
4. Follow the setup wizard to configure your integration

#### **YAML Configuration**
You can also configure Adaptive Climate via YAML in your `configuration.yaml`:

```yaml
# Example YAML configuration with multiple devices
adaptive_climate:
  # Primary living room configuration
  - entity: climate.living_room_ac
    name: "Living Room Adaptive Climate"
    indoor_temp_sensor: sensor.living_room_temperature
    outdoor_temp_sensor: sensor.outdoor_temperature
    indoor_humidity_sensor: sensor.living_room_humidity
    outdoor_humidity_sensor: sensor.outdoor_humidity
    
    # Comfort settings
    comfort_category: "I"  # I or II
    min_comfort_temp: 21.0
    max_comfort_temp: 27.0
    temperature_change_threshold: 0.5
    override_temperature: 0.0
    
    # Control settings
    energy_save_mode: true
    auto_mode_enable: true
    aggressive_cooling_threshold: 2.0
    aggressive_heating_threshold: 2.0
    
    # HVAC mode control
    enable_fan_mode: true
    enable_cool_mode: true
    enable_heat_mode: true
    enable_dry_mode: true
    enable_off_mode: true
    
    # Fan speed control
    max_fan_speed: "high"
    min_fan_speed: "low"
    
    # Area orchestration
    participate_area_orchestration: true
    # Automatic device selection
    auto_device_selection: true

  # Bedroom configuration
  - entity: climate.bedroom_ac
    name: "Bedroom Adaptive Climate"
    indoor_temp_sensor: sensor.bedroom_temperature
    outdoor_temp_sensor: sensor.outdoor_temperature
    comfort_category: "II"
    energy_save_mode: false
    participate_area_orchestration: false
    auto_device_selection: false

  # Kitchen configuration with shared sensors
  - entity: climate.kitchen_ac
    name: "Kitchen Adaptive Climate"
    indoor_temp_sensor: sensor.living_room_temperature  # Shared sensor
    outdoor_temp_sensor: sensor.outdoor_temperature     # Shared sensor
    comfort_category: "I"
    temperature_change_threshold: 1.0
    auto_device_selection: true
```

### **Required Configuration**
- **Climate Entity**: Your main HVAC/climate device
- **Indoor Temperature Sensor**: Sensor or weather entity for indoor temperature monitoring
- **Outdoor Temperature Sensor**: Sensor or weather entity for outdoor temperature monitoring

### **Optional Configuration**
- **Indoor Humidity Sensor**: Sensor for indoor humidity monitoring
- **Outdoor Humidity Sensor**: Sensor for outdoor humidity monitoring
- **Area Orchestration**: Enable coordination between devices in the same area

### **Configuration Precedence**
- **YAML takes precedence**: If a device is configured via YAML, UI configuration for the same entity will be ignored
- **Multiple devices**: You can mix YAML and UI configurations for different devices
- **Migration**: You can migrate from UI to YAML or vice versa by removing the old configuration first

> 📖 **For detailed YAML configuration documentation, see [YAML_CONFIGURATION.md](YAML_CONFIGURATION.md)**
> 📝 **See [example_configuration.yaml](example_configuration.yaml) for a complete configuration example**

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
| **Enable Off Mode** | Allow the system to turn off the AC when not needed | ✅ Enabled |

#### **Area Orchestration**
| Option | Description | Default |
|--------|-------------|---------|
| **Participate in Area Orchestration** | Enable coordination with other climate devices in the same area | ❌ Disabled |
| **Automatic Device Selection** | Automatically select best devices based on type and season | ❌ Disabled |

### **Automatic Device Selection Configuration**
The `auto_device_selection` option enables intelligent device selection based on device capabilities and current conditions:

**When Enabled (`auto_device_selection: true`)**:
- **Automatic Optimization**: System automatically selects the best climate devices for each season
- **Type-Based Selection**: Prioritizes devices based on their capabilities (heat_only, cool_only, dual, fan_dry_only)
- **Seasonal Intelligence**: Adapts device selection based on winter, summer, or shoulder seasons
- **Manual Override**: Ignores user-configured `primary_climates` and `secondary_climates` settings

**When Disabled (`auto_device_selection: false`)**:
- **Manual Control**: Uses user-configured device roles
- **Predictable Behavior**: Maintains consistent device assignments
- **Full Control**: User has complete control over which devices act as primary/secondary

**Device Selection Logic**:
- **Winter**: Prioritizes `heat_only` or `dual` devices with heating capabilities
- **Summer**: Prioritizes `cool_only` or `dual` devices with cooling capabilities  
- **Shoulder Seasons**: Uses `dual` devices or `fan_dry_only` based on comfort needs
- **Capability Ranking**: Considers device features like temperature control and HVAC mode support

**Configuration Examples**:
```yaml
# Automatic device selection (recommended for multi-device setups)
auto_device_selection: true

# Manual device selection (traditional approach)
auto_device_selection: false
primary_climates: ["climate.living_room_ac"]
secondary_climates: ["climate.bedroom_ac"]
```

### **Enable Off Mode Configuration**
The `enable_off_mode` option controls whether the system can turn off the air conditioning when it's not needed for comfort. This is particularly useful for:

- **Preventing Short Cycling**: When disabled, the system will use fan-only mode instead of turning off completely, which can help prevent rapid on/off cycles
- **Maintaining Air Circulation**: Some users prefer to keep the fan running for better air circulation even when heating/cooling isn't needed
- **Equipment Protection**: For sensitive HVAC equipment that shouldn't be turned off frequently

**Configuration Examples:**
```yaml
# Standard configuration (AC can turn off)
enable_off_mode: true

# Conservative configuration (AC stays on with fan)
enable_off_mode: false
```

**Behavior:**
- **`enable_off_mode: true`**: System can turn AC completely off when comfort conditions are met
- **`enable_off_mode: false`**: System will use fan-only mode instead of turning off, maintaining air circulation

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

#### `adaptive_climate.redetect_capabilities`
Force re-detection of device capabilities (cooling, heating, fan, dry modes).

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

### **Multi-Device Coordination**
- **Area-Based Discovery**: Automatically finds climate devices within Home Assistant areas
- **Independent Control**: Each device operates independently with its own settings
- **Shared Sensors**: Multiple devices can share temperature and humidity sensors
- **Coordinated Operation**: Optional area orchestration for coordinated climate control

### **Key Features**
- **Adaptive Comfort**: Uses ASHRAE 55 standard for scientific comfort calculations
- **Device Compatibility**: Maps calculated modes to device-supported modes
- **Energy Optimization**: Reduces energy usage when explicitly enabled
- **User Respect**: Never overrides manual user control
- **Fast Startup**: Immediate control cycle when auto mode is enabled
- **Scalable Architecture**: Supports from single devices to whole-home climate management

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

## 🔧 Recent Fixes & Improvements

### **Multi-Device & Area Detection (v1.4.0)**
**New Features**:
- **Area-Based Setup**: Automatically discover and configure climate devices within Home Assistant areas
- **Bulk Multi-Device Setup**: Configure multiple climate devices simultaneously with shared settings
- **Enhanced Single Device Setup**: Simplified configuration for individual devices
- **Area Orchestration**: Optional coordination between devices in the same area
- **Shared Sensor Support**: Multiple devices can share temperature and humidity sensors
- **Automatic Device Selection**: Intelligent device selection based on type and season (NEW in v1.4.0)

**Benefits**:
- ✅ Faster setup for multi-device homes
- ✅ Automatic device discovery within areas
- ✅ Consistent configuration across multiple devices
- ✅ Flexible sensor sharing options
- ✅ Improved user experience for complex setups

### **Automatic Device Selection (v1.4.0)**
**New Feature**: Added `auto_device_selection` configuration option for intelligent device selection based on device capabilities and seasonal conditions.

**Key Capabilities**:
- **Seasonal Optimization**: Automatically selects the best devices for winter (heating), summer (cooling), and shoulder seasons
- **Type-Based Intelligence**: Prioritizes devices based on their capabilities (heat_only, cool_only, dual, fan_dry_only)
- **Dynamic Role Assignment**: Changes device roles automatically as seasons and conditions change
- **Capability Ranking**: Considers device features like temperature control and HVAC mode support

**Configuration Examples**:
```yaml
# Enable automatic device selection
auto_device_selection: true

# Disable for manual control
auto_device_selection: false
primary_climates: ["climate.living_room_ac"]
secondary_climates: ["climate.bedroom_ac"]
```

**Benefits**:
- ✅ Optimizes device usage for each season automatically
- ✅ Reduces energy consumption by using the most appropriate devices
- ✅ Improves comfort by leveraging device-specific capabilities
- ✅ Simplifies multi-device setup and management
- ✅ Adapts to changing conditions without manual intervention

### **Temperature Change Threshold Fix (v1.3.1)**
**Problem**: The `temperature_change_threshold` configuration was not being properly applied, causing frequent on/off cycles even when configured for higher thresholds.

**Solution**: Fixed the application of `temperature_change_threshold` in three critical areas:
1. **Equilibrium Detection**: Now uses configured threshold instead of hardcoded 0.5°C
2. **Change Detection**: Uses configured threshold for determining when to execute actions
3. **Override Detection**: Uses configured threshold for detecting manual temperature changes

**Impact**: 
- ✅ Prevents short cycling of AC compressors
- ✅ Respects user configuration for sensitivity
- ✅ Reduces wear on HVAC equipment
- ✅ Improves energy efficiency

**Recommended Configuration**:
```yaml
adaptive_climate:
  - entity: climate.your_ac_entity
    # ... other settings ...
    temperature_change_threshold: 1.0  # Increase from default 0.5°C
    enable_off_mode: false  # Use fan-only instead of turning off completely
    # ... other settings ...
```

**Threshold Guidelines**:
- **0.5°C**: Very sensitive (default, may cause frequent cycles)
- **1.0°C**: Balanced approach (recommended)
- **1.5°C**: Conservative (good for equipment longevity)
- **2.0°C**: Very conservative (minimal changes)

### **Enable Off Mode Feature (v1.3.2)**
**New Feature**: Added `enable_off_mode` configuration option to control whether the system can turn off HVAC equipment completely.

**Configuration Examples**:
```yaml
# Standard configuration (AC can turn off)
enable_off_mode: true

# Conservative configuration (AC stays on with fan)
enable_off_mode: false
```

**Benefits**:
- ✅ Prevents short cycling of AC compressors
- ✅ Maintains air circulation when disabled
- ✅ Protects sensitive HVAC equipment
- ✅ Improves energy efficiency when enabled

---

## 🚀 Getting Started

### **Quick Setup Guide**

1. **Install via HACS** (recommended)
2. **Choose Setup Method**:
   - **Area Setup**: Select an area and let the system discover devices automatically
   - **Bulk Setup**: Select multiple climate devices manually
   - **Single Setup**: Configure one device at a time
3. **Configure Sensors**: Select indoor and outdoor temperature sensors
4. **Customize Settings**: Adjust comfort categories and thresholds as needed
5. **Enable Automation**: Turn on auto mode to start adaptive control

### **Multi-Device Setup Tips**

- **Start with Area Setup**: Use area-based discovery for the easiest multi-device configuration
- **Share Sensors**: Multiple devices in the same area can share temperature sensors
- **Consistent Settings**: Use bulk setup for devices that should have similar behavior
- **Individual Control**: Use single setup for devices that need specific configurations

---

## 📚 Additional Resources

- **Documentation**: [GitHub Repository](https://github.com/msinhore/adaptive-climate)
- **Issues**: [GitHub Issues](https://github.com/msinhore/adaptive-climate/issues)
- **Discussions**: [GitHub Discussions](https://github.com/msinhore/adaptive-climate/discussions)
- **Examples**: [Example Configurations](https://github.com/msinhore/adaptive-climate/tree/main/examples)

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.