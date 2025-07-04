# Adaptive Climate - ASHRAE 55 Custom Component

[![GitHub Release](https://img.shields.io/github/v/release/msinhore/adaptive-climate?style=for-the-badge)](https://github.com/msinhore/adaptive-climate/releases)
[![GitHub Activity](https://img.shields.io/github/commit-activity/y/msinhore/adaptive-climate?style=for-the-badge)](https://github.com/msinhore/adaptive-climate/commits/main)
[![License](https://img.shields.io/github/license/msinhore/adaptive-climate.svg?style=for-the-badge)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![Community Forum](https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge)](https://community.home-assistant.io)

A Home Assistant custom component that acts as an intelligent controller for your existing climate entities using the ASHRAE 55 adaptive comfort model. It provides energy-saving features, natural ventilation detection, and comprehensive configuration through real entities.

**Current Version: 0.1.39 - Stage 4 (HACS Production Ready)**

> **🚀 Development Environment**: This project uses a **remote development server** (192.168.4.127 - Debian 12) for all testing and development. See [DEVELOPMENT.md](DEVELOPMENT.md) for setup instructions.

## 🆕 What's New in Stage 4 (HACS Production Ready)

This version brings full HACS production readiness with advanced UI configuration and international support:

### 🎛️ Options Flow Implementation
- **UI-based configuration** through Home Assistant's options flow
- **Real-time updates** without requiring restarts
- **Complete parameter control** for all 15 user-editable entities
- **Validation and error handling** with user-friendly messages

### 🌍 Multi-language Support
- **6 languages supported**: English, Portuguese (BR), Italian, French, Spanish, German
- **Complete translations** for all entities, descriptions, and UI elements
- **Localized entity names** and state descriptions
- **Future-ready** for additional language contributions

### 🏭 HACS Production Standards
- **integration_type**: "device" for proper device grouping
- **pythermalcomfort requirement** properly declared
- **Options flow integration** with config_flow
- **Proper entity translations** following HA i18n standards

## 🆕 What's New in Stage 3 (Real Entity Architecture)

### 🎯 Real Entity Configuration
- **Number entities** for all numeric parameters (temperatures, thresholds, timeouts)
- **Switch entities** for all boolean settings (energy save, natural ventilation)
- **Select entities** for comfort category selection
- **Sensor entities** for diagnostic information
- **Binary sensor** for compliance status and comprehensive attributes

### ⚙️ CoordinatorEntity Pattern
- **Unified data management** through AdaptiveClimateCoordinator
- **Real-time updates** across all entities
- **Consistent device_info** with stable unique_ids
- **Performance optimized** with single data source

### 📊 Essential Configuration Entities
- **Temperature Controls**: Min/Max comfort temps, change thresholds
- **Air & Ventilation**: Air velocity, natural ventilation settings
- **Energy Management**: Setback offsets, auto-shutdown timers
- **Comfort Settings**: ASHRAE category, precision modes

### 🛡️ Safety & Standards
- **18-30°C safety limits**: Prevents dangerous temperature settings
- **ASHRAE 55 compliance**: Strict adherence to comfort standards
- **User-configurable limits**: Set your own comfort boundaries within safe ranges
- **Stable unique_ids**: Based on config_entry.entry_id for persistence

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. It provides real entities for configuration and rich diagnostic sensors for monitoring and automation.

## Key Features

### ASHRAE 55 Adaptive Comfort Model
- Calculates optimal comfort temperatures using the adaptive model: `18.9 + 0.255 × Outdoor Temperature`
- Supports three comfort categories (I, II, III) with different tolerance levels
- Accounts for air velocity and humidity corrections
- Uses operative temperature when radiant temperature sensors are available

### Service-Based Configuration
- **All parameters as attributes**: View all settings in one place
- **Service management**: Use Home Assistant services to change any setting
- **No UI clutter**: Clean device page with only essential status
- **Future-proof architecture**: Follows HA 2025.7+ patterns

### Intelligent Climate Control
- Automatically controls your existing climate entities (thermostats, HVAC systems)
- Calculates optimal comfort temperatures and applies them to your hardware
- Natural ventilation detection and recommendation  
- Adaptive fan speed control based on comfort requirements
- Manual override with automatic timeout functionality
- Works as a coordinator - no new climate entity created

### Energy Efficiency
- Occupancy-based setback with configurable temperature offsets
- Automatic system shutdown during extended absence periods
- Dynamic comfort zones that adapt to seasonal changes
- Natural ventilation prioritization when conditions are suitable

### Rich Diagnostic Sensors
- Real-time ASHRAE 55 compliance monitoring
- Comfort temperature, range, and outdoor running mean sensors
- Binary sensors for natural ventilation and compliance status
- Comprehensive attributes for Home Assistant automations
- All sensors are automatically created for monitoring and dashboards
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

### Initial Setup

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

#### Required Sensors:
- **Climate Entity**: Your existing thermostat/HVAC system
- **Indoor Temperature Sensor**: Current indoor temperature
- **Outdoor Temperature Sensor**: Current outdoor temperature
- **Comfort Category**: ASHRAE 55 category (I/II/III)

#### Optional Sensors:
- **Indoor/Outdoor Humidity Sensors**: For enhanced comfort calculations
- **Mean Radiant Temperature Sensor**: For operative temperature calculations
- **Occupancy Sensor**: For energy-saving modes

### Advanced Configuration (Options Flow)

After initial setup, access advanced settings through **Settings** → **Devices & Services** → **Adaptive Climate** → **Configure**.

#### 🎛️ Available Options:

**🌡️ Temperature Settings:**
- Minimum/Maximum Comfort Temperature (10-35°C)
- Comfort Range Offsets (±10°C)
- Temperature Change Threshold (0.1-5.0°C)
- Setback Temperature Offset (0.5-10.0°C)

**💨 Air & Ventilation:**
- Air Velocity (0.0-2.0 m/s)
- Natural Ventilation Threshold (0.5-10.0°C)
- Adaptive Air Velocity Control

**⚙️ Advanced Features:**
- Comfort Precision Mode
- Humidity Comfort Adjustments
- Operative Temperature Calculations
- Energy Saving Mode

#### 🌍 Multi-Language Support
The integration supports 6 languages with complete translations:
- **English** (en)
- **Portuguese Brazil** (pt-BR)
- **Italian** (it)
- **French** (fr)
- **Spanish** (es)
- **German** (de)

### Real-Time Entity Configuration

All settings are also available as **15 user-editable entities** that can be controlled via:

- **UI**: Direct editing in the device page
- **Automations**: Using `number.set_value`, `switch.turn_on/off`, `select.select_option`
- **Services**: REST API calls or service calls
- **Dashboards**: Include controls in your Lovelace dashboards

### 📋 Service-Based Configuration

All configuration is now managed through Home Assistant services for a clean, modern experience. See the [Service Configuration Guide](SERVICE_CONFIGURATION.md) for complete details.

#### Quick Examples:
```yaml
# Change minimum comfort temperature
service: adaptive_climate.set_parameter
data:
  entity_id: binary_sensor.adaptive_climate_living_room_ashrae_compliance
  parameter: min_comfort_temp
  value: 19.0

# Set manual override for 2 hours
service: adaptive_climate.set_manual_override
data:
  entity_id: binary_sensor.adaptive_climate_living_room_ashrae_compliance
  temperature: 22.5
  duration_hours: 2
```

### 🎯 Clean Device Page

Your device page shows only essential entities:
- **ASHRAE Compliance**: Main status with all config as attributes
- **Natural Ventilation**: Ventilation opportunity detection  
- **Comfort Temperature**: Real-time adaptive comfort calculation
- **Running Mean**: 7-day outdoor temperature average

### ⚙️ Service-Driven Configuration
- **`adaptive_climate.set_parameter`**: Change any configuration value
- **`adaptive_climate.reset_parameter`**: Reset to defaults
- **`adaptive_climate.set_manual_override`**: Temporary manual control
- **`adaptive_climate.clear_manual_override`**: Return to adaptive mode

### 📊 Essential Entities Only
- **ASHRAE Compliance Binary Sensor**: Main status + all config attributes
- **Natural Ventilation Sensor**: Ventilation opportunity detection
- **Adaptive Comfort Temperature**: Real-time comfort calculations
- **Outdoor Running Mean**: 7-day temperature average

### 🛡️ Safety & Standards
- **18-30°C safety limits**: Prevents dangerous temperature settings
- **ASHRAE 55 compliance**: Strict adherence to comfort standards
- **User-configurable limits**: Set your own comfort boundaries within safe ranges

## Development & Testing

### Local Test Environment with HACS

This project includes a complete Docker-based test environment that automatically installs HACS for easy integration testing:

```bash
# Start local test environment with HACS
./start_test_environment.sh
```

This script will:
- 🐳 Set up Home Assistant, InfluxDB, and Mosquitto in Docker containers
- 🛍️ Automatically install HACS (Home Assistant Community Store)
- 📦 Copy the Adaptive Climate integration to the test environment
- ⚙️ Configure all necessary services and dependencies

After running, you can:
1. Access Home Assistant at http://localhost:8123
2. Configure HACS in Settings > Devices & Services
3. Install and test the Adaptive Climate integration via HACS
4. Use the built-in test scripts for validation

### HACS Installation Scripts

For manual HACS installation:

```bash
# Install HACS locally
./install_hacs_local.sh

# Install HACS on remote host (for remote testing)
docker/install_hacs.sh
```

### Test Environment Features

- **Automatic HACS setup**: No manual download required
- **Full Home Assistant stack**: Complete testing environment
- **Data persistence**: InfluxDB for historical data
- **MQTT support**: Mosquitto for IoT device simulation
- **Hot reload**: Changes reflect immediately
- **Diagnostic tools**: Built-in test scripts and validators

See [docker/README.md](docker/README.md) for detailed setup instructions and [QUICKSTART.md](QUICKSTART.md) for a complete development guide.

## 🚀 Development Environment

This project uses a **remote development server** for all development and testing:

- **Server**: 192.168.4.127 (Debian 12)
- **Environment**: Docker-based with HACS pre-installed
- **Access**: SSH without password required

### Quick Start for Developers

```bash
# 1. Configure remote server (one time)
./docker/setup.sh

# 2. Deploy to remote server
./docker/deploy.sh

# 3. Start complete environment with HACS
./start_test_environment.sh

# 4. Access Home Assistant
# http://192.168.4.127:8123
```

📖 **Complete development guide**: [DEVELOPMENT.md](DEVELOPMENT.md)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.