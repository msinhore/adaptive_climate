# Adaptive Climate - ASHRAE 55 Custom Component

[![GitHub Release](https://img.shields.io/github/v/release/msinhore/adaptive-climate?style=for-the-badge)](https://github.com/msinhore/adaptive-climate/releases)
[![GitHub Activity](https://img.shields.io/github/commit-activity/y/msinhore/adaptive-climate?style=for-the-badge)](https://github.com/msinhore/adaptive-climate/commits/main)
[![License](https://img.shields.io/github/license/msinhore/adaptive-climate.svg?style=for-the-badge)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![Community Forum](https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge)](https://community.home-assistant.io)

A Home Assistant custom component that acts as an intelligent controller for your existing climate entities using the ASHRAE 55 adaptive comfort model. It provides energy-saving features, natural ventilation detection, and comprehensive diagnostic sensors.

**Development Version: 0.1.37**

## 🆕 What's New in 2025.7+ (Service-Based Configuration)

This version brings a completely modernized experience compatible with Home Assistant 2025.7+ best practices:

### 🎯 Clean Device Page
- **Only 4 essential entities** visible on device page
- **All configuration as attributes** on the main binary sensor
- **Service-based management** for all parameter changes
- **No entity clutter** - follows modern HA patterns

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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

The component uses a modern UI-based configuration flow accessible through **Settings** → **Devices & Services** → **Add Integration** → **Adaptive Climate**.

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

## Overview

This component acts as a smart controller/coordinator that enhances your existing climate entities (thermostats, HVAC systems) with ASHRAE 55 adaptive comfort intelligence. Instead of creating a new climate entity, it works behind the scenes to automatically adjust your existing climate systems based on adaptive comfort principles while providing rich diagnostic sensors for monitoring and automation.

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
3. Add