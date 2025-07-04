# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.39] - 2025-07-05

### 🚀 Stage 4: HACS Production Ready - Options Flow & Multi-Language Support

#### ✨ Added
- **Options Flow Implementation**: Complete UI-based configuration through Home Assistant's options flow
  - Real-time parameter updates without HA restart
  - Validation and error handling for all inputs
  - User-friendly forms with proper field descriptions
- **Multi-Language Support**: Complete translations for 6 languages
  - English (en) - Primary language
  - Portuguese Brazil (pt-BR) - Complete translation
  - Italian (it) - Full localization
  - French (fr) - Complete French translation
  - Spanish (es) - Full Spanish support
  - German (de) - Complete German translation
- **Enhanced Configuration Management**: 
  - `async_update_options()` method in coordinator
  - Real-time config updates through options flow
  - Validation schemas for all configuration parameters
- **HACS Production Standards**:
  - `integration_type`: "device" for proper device grouping
  - `pythermalcomfort>=2.7.4` requirement properly declared
  - Options flow integrated with config_flow
  - Complete translation coverage for all entities

#### 🔧 Changed
- **Manifest Updates**: 
  - Version bumped to 0.1.39
  - Added `pythermalcomfort>=2.7.4` to requirements
  - Changed `integration_type` from "service" to "device"
- **Config Flow Enhancement**:
  - Added options flow support with `async_get_options_flow()`
  - Updated import structure for options flow integration
- **Coordinator Enhancements**:
  - Added `async_update_options()` for real-time option updates
  - Enhanced error handling and logging
  - Options listener registration in __init__.py

#### 📁 File Structure
```
translations/
├── en.json      # English (primary)
├── pt-BR.json   # Portuguese Brazil
├── it.json      # Italian
├── fr.json      # French
├── es.json      # Spanish
└── de.json      # German
```

#### 🌍 Translation Coverage
- **Config Flow**: All setup steps and field descriptions
- **Options Flow**: Complete UI labels and help text
- **Entity Names**: All 21 entities fully translated
- **Error Messages**: User-friendly error descriptions
- **State Values**: ASHRAE comfort category translations

#### 📋 Options Flow Parameters
- **Temperature Settings**: Min/max comfort temps, ranges, thresholds
- **Air & Ventilation**: Air velocity, natural ventilation settings
- **Advanced Features**: Precision mode, humidity adjustments, operative temperature
- **Energy Management**: Setback offsets, energy saving modes

#### 🎯 HACS Submission Ready
- ✅ Options flow implementation complete
- ✅ Multi-language support (6 languages)
- ✅ Production-grade manifest.json
- ✅ Complete translation coverage
- ✅ Real-time configuration updates
- ✅ Proper validation and error handling

## [0.1.38] - 2025-07-05

### 🚀 Stage 3: Real Entity Architecture - HACS-Ready Implementation

#### 🔥 BREAKING CHANGES
- **Removed Bridge Entity Architecture**: Complete migration from bridge entities to real Home Assistant entities
- **Entity ID Changes**: All entities now have new unique IDs based on `config_entry.entry_id`
- **Device Integration**: All entities now appear under a single "Adaptive Climate" device
- **Configuration Method**: Real entities replace service-based configuration for better HA integration

#### ✨ Added
- **Real NumberEntity Implementation**: 8 number entities for temperature controls, thresholds, and offsets
- **Real SwitchEntity Implementation**: 6 switch entities for energy save, natural ventilation, and adaptive features  
- **Real SelectEntity Implementation**: 1 select entity for ASHRAE comfort category (I, II, III)
- **Real SensorEntity Implementation**: 5 sensor entities for diagnostic and calculated values
- **CoordinatorEntity Pattern**: All entities use proper CoordinatorEntity inheritance
- **Stable Unique IDs**: Entity persistence guaranteed with `{config_entry.entry_id}_{entity_key}` pattern
- **Consistent Device Info**: Single device grouping with proper manufacturer, model, and version info
- **Enhanced Coordinator Methods**: Added `async_update_config_value()` and `get_config_value()` methods

#### 🔧 Changed
- **Entity Architecture**: Migrated from bridge entities to real Home Assistant entities
- **Device Info**: Standardized across all entities with consistent identifiers
- **Configuration Updates**: Real-time entity updates through coordinator notifications
- **Platform Registration**: Updated __init__.py to register all platforms properly

#### 🗑️ Removed
- **bridge_entity.py**: Removed bridge entity architecture completely
- **bridge_entity_refactored.py**: Removed refactored bridge implementations
- **Temporary Files**: Cleaned up all *_new.py development files

#### 📊 Entity Summary
- **Number Entities**: 8 (min/max comfort temp, air velocity, thresholds, offsets)
- **Switch Entities**: 6 (energy save, natural ventilation, precision modes)
- **Select Entities**: 1 (comfort category)
- **Sensor Entities**: 5 (diagnostic and calculated values)
- **Binary Sensor**: 1 (ASHRAE compliance with comprehensive attributes)

#### 🎯 HACS Compliance
- ✅ Real entities (no bridge architecture)
- ✅ CoordinatorEntity pattern throughout
- ✅ Consistent device_info implementation
- ✅ Stable unique_ids for entity persistence
- ✅ Proper entity categorization and device classes
- ✅ Updated documentation and manifest

## [Unreleased]

### 🚀 Initial Release: ASHRAE 55 Adaptive Climate Component

#### Added
- **ASHRAE 55 Adaptive Comfort Model**: Complete implementation of adaptive thermal comfort calculations
- **Smart Climate Control**: Automatic temperature adjustment based on outdoor conditions
- **Energy Efficiency**: Natural ventilation suggestions and setback temperature support
- **Occupancy Awareness**: Integration with occupancy sensors for energy saving
- **Home Assistant 2025.6.0+ Support**: Full compatibility with latest HA versions
- **Modern Configuration UI**: 3-step configuration flow with area filtering and entity suggestions
- **Device Registry Integration**: Proper device info for better HA integration
- **Entity Categories**: Support for entity categorization in HA UI
- **Multi-language Support**: Initial support for Portuguese and English
- **Comprehensive Documentation**: Full setup guides and examples
- **Development Tools**: Complete testing suite and CI/CD pipeline

#### Core Features
- **Adaptive Comfort Categories**: Support for ASHRAE 55 Categories I, II, and III
- **Natural Ventilation Control**: Intelligent window/fan control suggestions
- **Manual Override**: Temporary manual control with automatic return
- **Energy Saving Modes**: Setback temperatures and auto-shutdown for unoccupied spaces
- **Real-time Calculations**: Live comfort zone updates based on outdoor temperature
- **Area-based Configuration**: Smart entity filtering by Home Assistant areas
- **Multilingual Support**: Enhanced translations for better UX
- **HACS Compatibility**: Updated for HACS 2.0.0+ standards

### 🔧 Technical Improvements
- **Type Safety**: Enhanced type hints for better IDE support
- **Testing**: Comprehensive test suite for HA 2025.6.0+
- **Documentation**: Complete compatibility documentation
- **Migration**: Seamless upgrade path from v1.x

## [0.1.1] - 2025-01-27

### 🔧 Architecture Refactor: Controller Pattern

#### Changed
- **BREAKING**: Refactored from climate entity to controller/coordinator pattern
- Component now acts as an intelligent controller that manages existing climate entities
- No longer creates a new climate entity, works with your existing thermostats/HVAC systems
- Updated integration type to "service" in manifest.json
- Removed climate.py file and related climate entity code

#### Added
- **AdaptiveClimateCoordinator**: New coordinator class that manages control logic
- **Diagnostic Sensors**: Rich sensor platform with comfort temperature, ranges, and compliance
- **Binary Sensors**: ASHRAE compliance and natural ventilation recommendation sensors
- **Enhanced Monitoring**: All ASHRAE calculations now exposed as separate sensors
- **Better Integration**: Works seamlessly with any existing Home Assistant climate entity

#### Improved
- **Service Architecture**: More robust service-based approach for better integration
- **Entity Management**: Cleaner entity lifecycle management
- **Performance**: Reduced overhead by not creating unnecessary climate entities
- **Compatibility**: Better compatibility with existing climate setups

#### Developer Notes
- Updated README.md to reflect new architecture
- All diagnostic data now available through dedicated sensor entities
- Services now operate on config entry level rather than entity level

## [1.0.0] - 2025-01-02

### Added
- Initial release of Adaptive Climate custom component
- ASHRAE 55 adaptive comfort model implementation
- Support for ASHRAE 55 comfort categories I, II, and III
- Energy optimization with 15-30% potential savings
- Occupancy-aware control with automatic setback
- Natural ventilation detection and HVAC auto-shutdown
- Adaptive air velocity control for enhanced comfort
- Humidity-based comfort corrections
- Operative temperature calculation support
- Manual override with automatic timeout
- Comprehensive configuration through Home Assistant UI
- SmartIR and generic thermostat compatibility
- Detailed logging and compliance reporting
- Auto shutdown on prolonged absence
- Precision mode for high-accuracy calculations

### Features
- **Climate Control**: Intelligent HVAC mode switching (heat/cool/auto/fan_only/off)
- **Temperature Management**: Dynamic setpoint adjustment based on outdoor conditions
- **Energy Savings**: Multiple energy-saving strategies including occupancy setback
- **Natural Ventilation**: Automatic detection when outdoor conditions are suitable
- **Fan Control**: Adaptive fan speed based on temperature deviation
- **Humidity Compensation**: Comfort adjustments for high/low humidity conditions
- **Occupancy Integration**: Presence-based control with configurable absence timers
- **Manual Override**: Temporary manual control with automatic resume
- **Rich Attributes**: Comprehensive status reporting and diagnostics
- **HACS Compatible**: Easy installation through Home Assistant Community Store

[2.0.0]: https://github.com/msinhore/adaptive-climate/releases/tag/v2.0.0
[1.0.0]: https://github.com/msinhore/adaptive-climate/releases/tag/v1.0.0
