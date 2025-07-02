# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
