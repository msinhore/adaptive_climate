#!/usr/bin/env python3
"""
Test script to verify coordinator behavior on restart.
This simulates the condition where entities are not immediately available after HA restart.
"""

import asyncio
import logging
from unittest.mock import Mock, patch
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Mock Home Assistant components
def create_mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.data = {}
    hass.states = Mock()
    hass.services = Mock()
    hass.async_create_task = lambda coro: asyncio.create_task(coro)
    return hass

def create_mock_state(entity_id, state_value, attributes=None):
    """Create a mock state object."""
    state = Mock()
    state.entity_id = entity_id
    state.state = state_value
    state.attributes = attributes or {}
    return state

async def test_coordinator_with_unavailable_entities():
    """Test coordinator behavior when entities are unavailable."""
    print("\n=== Testing Coordinator with Unavailable Entities ===")
    
    # Import our coordinator
    from custom_components.adaptive_climate.coordinator import AdaptiveClimateCoordinator
    
    # Create mock hass
    hass = create_mock_hass()
    
    # Configuration
    config = {
        "name": "Test Adaptive Climate",
        "climate_entity": "climate.test_hvac",
        "indoor_temp_sensor": "sensor.indoor_temperature",
        "outdoor_temp_sensor": "sensor.outdoor_temperature",
        "comfort_category": "II",
    }
    
    # Create coordinator
    coordinator = AdaptiveClimateCoordinator(hass, config)
    
    # Test 1: All entities unavailable
    print("\n--- Test 1: All entities unavailable ---")
    hass.states.get.return_value = None  # No entities found
    
    try:
        data = await coordinator._async_update_data()
        print(f"✓ Coordinator returned data when entities unavailable: {list(data.keys())}")
        print(f"  - Status: {data.get('status')}")
        print(f"  - Comfort temp: {data.get('adaptive_comfort_temp')}")
        print(f"  - ASHRAE compliant: {data.get('ashrae_compliant')}")
    except Exception as e:
        print(f"✗ Error when entities unavailable: {e}")
    
    # Test 2: Entities with unknown state
    print("\n--- Test 2: Entities with unknown state ---")
    hass.states.get.side_effect = lambda entity_id: {
        "climate.test_hvac": create_mock_state("climate.test_hvac", "unknown"),
        "sensor.indoor_temperature": create_mock_state("sensor.indoor_temperature", "unknown"),
        "sensor.outdoor_temperature": create_mock_state("sensor.outdoor_temperature", "unknown"),
    }.get(entity_id)
    
    try:
        data = await coordinator._async_update_data()
        print(f"✓ Coordinator returned data when entities unknown: {list(data.keys())}")
        print(f"  - Status: {data.get('status')}")
        print(f"  - Comfort temp: {data.get('adaptive_comfort_temp')}")
    except Exception as e:
        print(f"✗ Error when entities unknown: {e}")
    
    # Test 3: Valid entities
    print("\n--- Test 3: Valid entities available ---")
    hass.states.get.side_effect = lambda entity_id: {
        "climate.test_hvac": create_mock_state("climate.test_hvac", "heat", {"temperature": 22.0}),
        "sensor.indoor_temperature": create_mock_state("sensor.indoor_temperature", "21.5"),
        "sensor.outdoor_temperature": create_mock_state("sensor.outdoor_temperature", "15.0"),
    }.get(entity_id)
    
    try:
        data = await coordinator._async_update_data()
        print(f"✓ Coordinator returned data when entities valid: {list(data.keys())}")
        print(f"  - Status: {data.get('status', 'normal')}")
        print(f"  - Indoor temp: {data.get('indoor_temperature')}")
        print(f"  - Outdoor temp: {data.get('outdoor_temperature')}")
        print(f"  - Comfort temp: {data.get('adaptive_comfort_temp')}")
        print(f"  - ASHRAE compliant: {data.get('ashrae_compliant')}")
    except Exception as e:
        print(f"✗ Error when entities valid: {e}")

async def test_sensor_availability():
    """Test sensor availability logic."""
    print("\n=== Testing Sensor Availability ===")
    
    from custom_components.adaptive_climate.sensor import AdaptiveComfortTemperatureSensor
    from custom_components.adaptive_climate.coordinator import AdaptiveClimateCoordinator
    
    # Create mock objects
    hass = create_mock_hass()
    config = {"name": "Test", "climate_entity": "climate.test", "indoor_temp_sensor": "sensor.indoor", "outdoor_temp_sensor": "sensor.outdoor"}
    coordinator = AdaptiveClimateCoordinator(hass, config)
    
    # Mock config entry
    config_entry = Mock()
    config_entry.entry_id = "test_entry"
    config_entry.data = config
    
    # Create sensor
    sensor = AdaptiveComfortTemperatureSensor(coordinator, config_entry)
    
    # Test 1: No data
    print("\n--- Test 1: No coordinator data ---")
    coordinator.data = None
    coordinator.last_update_success = False
    print(f"Sensor value: {sensor.native_value}")
    print(f"Sensor available: {sensor.available}")
    
    # Test 2: Entities unavailable
    print("\n--- Test 2: Entities unavailable status ---")
    coordinator.data = {"status": "entities_unavailable", "adaptive_comfort_temp": 22.0}
    coordinator.last_update_success = True
    print(f"Sensor value: {sensor.native_value}")
    print(f"Sensor available: {sensor.available}")
    
    # Test 3: Normal operation
    print("\n--- Test 3: Normal operation ---")
    coordinator.data = {"adaptive_comfort_temp": 23.5, "indoor_temperature": 22.0}
    coordinator.last_update_success = True
    print(f"Sensor value: {sensor.native_value}")
    print(f"Sensor available: {sensor.available}")

async def main():
    """Run all tests."""
    print("🧪 Testing Adaptive Climate Coordinator Restart Behavior")
    print("=" * 60)
    
    await test_coordinator_with_unavailable_entities()
    await test_sensor_availability()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
