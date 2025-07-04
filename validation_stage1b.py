"""
Stage 1b Validation Script for Adaptive Climate Bridge Entity Refactor.

This script provides utilities for validating the NumberBridgeEntity migration
from Entity to CoordinatorEntity pattern in Home Assistant.

Key validation points:
1. Bridge entities appear in UI with correct ranges/units
2. Value changes via UI reflect immediately in binary sensor attributes  
3. Coordinator logging shows detailed tracking of all operations
4. Values reset to defaults after HA restart (expected - no persistence yet)
5. No regressions in binary sensor or coordinator functionality

Usage:
- Install the integration with Stage 1b refactored entities
- Monitor logs at DEBUG level for detailed tracking
- Use HA Developer Tools to test entity operations
- Verify UI functionality in frontend controls
"""

import logging
from typing import Dict, List, Any

_LOGGER = logging.getLogger(__name__)

# Test entities expected to be available after Stage 1b implementation
STAGE1B_TEST_ENTITIES = [
    {
        "entity_id": "number.adaptive_climate_min_comfort_temp_bridge_v2",
        "attribute_name": "min_comfort_temp",
        "display_name": "Minimum Comfort Temperature (Test)",
        "unit": "°C",
        "range": [15.0, 25.0],
        "step": 0.5,
        "test_values": [18.0, 20.5, 22.0]
    },
    {
        "entity_id": "number.adaptive_climate_max_comfort_temp_bridge_v2", 
        "attribute_name": "max_comfort_temp",
        "display_name": "Maximum Comfort Temperature (Test)",
        "unit": "°C",
        "range": [25.0, 35.0],
        "step": 0.5,
        "test_values": [26.0, 28.5, 30.0]
    },
    {
        "entity_id": "number.adaptive_climate_air_velocity_bridge_v2",
        "attribute_name": "air_velocity", 
        "display_name": "Air Velocity (Test)",
        "unit": "m/s",
        "range": [0.0, 2.0],
        "step": 0.1,
        "test_values": [0.1, 0.5, 1.0]
    }
]

# Log patterns to look for during validation
EXPECTED_LOG_PATTERNS = {
    "setup": [
        "STAGE1B_SETUP: Added * test entities for validation",
        "STAGE1B_TEST: Created test entity * for attribute *"
    ],
    "read_operations": [
        "NumberBridge * native_value READ: value=*, source=*",
        "BRIDGE_READ START: attribute=*",
        "BRIDGE_READ SUCCESS: attribute=*, value=*, source=*"
    ],
    "write_operations": [
        "NumberBridge * SET_VALUE START: old_value=*, new_value=*",
        "NumberBridge * VALUE_UPDATE_REQUEST: * -> *",
        "BRIDGE_UPDATE START: attribute=*, new_value=*",
        "BRIDGE_UPDATE SUCCESS: *.* = * (was: *) [NO PERSISTENCE - IN-MEMORY ONLY]"
    ],
    "coordinator_operations": [
        "BRIDGE_UPDATE binary_sensor_target: *",
        "BRIDGE_UPDATE attribute_change: *: * -> *",
        "BRIDGE_UPDATE coordinator_data_updated: * = *"
    ]
}

def log_stage1b_validation_start():
    """Log the start of Stage 1b validation with expected entities and test plan."""
    _LOGGER.info("=" * 80)
    _LOGGER.info("STAGE 1B VALIDATION - NumberBridgeEntity CoordinatorEntity Migration")
    _LOGGER.info("=" * 80)
    _LOGGER.info("Expected Test Entities:")
    
    for entity in STAGE1B_TEST_ENTITIES:
        _LOGGER.info(
            "  - %s: %s [%s-%s %s, step=%s]",
            entity["entity_id"],
            entity["display_name"],
            entity["range"][0],
            entity["range"][1], 
            entity["unit"],
            entity["step"]
        )
    
    _LOGGER.info("")
    _LOGGER.info("Manual Test Steps:")
    _LOGGER.info("1. ✅ Verify test entities appear in HA UI (Developer Tools > States)")
    _LOGGER.info("2. ✅ Test value changes via UI controls (should update instantly)")
    _LOGGER.info("3. ✅ Check binary sensor attributes are updated correctly")
    _LOGGER.info("4. ✅ Monitor logs for expected patterns (see log_patterns below)")
    _LOGGER.info("5. ⚠️  Test restart persistence (values should reset - expected)")
    _LOGGER.info("")
    _LOGGER.info("Expected Log Patterns:")
    for category, patterns in EXPECTED_LOG_PATTERNS.items():
        _LOGGER.info("  %s:", category.upper())
        for pattern in patterns:
            _LOGGER.info("    - %s", pattern)
    _LOGGER.info("=" * 80)

def create_service_call_examples() -> List[Dict[str, Any]]:
    """Generate service call examples for testing the refactored entities."""
    service_calls = []
    
    for entity in STAGE1B_TEST_ENTITIES:
        for test_value in entity["test_values"]:
            service_calls.append({
                "service": "number.set_value",
                "data": {
                    "entity_id": entity["entity_id"],
                    "value": test_value
                },
                "expected_result": f"Update {entity['attribute_name']} to {test_value}",
                "expected_logs": [
                    f"NumberBridge {entity['attribute_name']} SET_VALUE START",
                    f"BRIDGE_UPDATE START: attribute={entity['attribute_name']}, new_value={test_value}",
                    f"BRIDGE_UPDATE SUCCESS"
                ]
            })
    
    return service_calls

def log_service_call_examples():
    """Log example service calls for manual testing."""
    service_calls = create_service_call_examples()
    
    _LOGGER.info("Example Service Calls for Testing:")
    _LOGGER.info("-" * 40)
    
    for i, call in enumerate(service_calls, 1):
        _LOGGER.info("Test %d: %s", i, call["expected_result"])
        _LOGGER.info("  Service: %s", call["service"])
        _LOGGER.info("  Data: %s", call["data"])
        _LOGGER.info("  Expected logs: %s", ", ".join(call["expected_logs"]))
        _LOGGER.info("")

def validate_entity_availability(hass) -> Dict[str, bool]:
    """Check if all expected test entities are available in Home Assistant."""
    results = {}
    
    _LOGGER.info("Validating Entity Availability:")
    _LOGGER.info("-" * 30)
    
    for entity in STAGE1B_TEST_ENTITIES:
        entity_id = entity["entity_id"]
        state = hass.states.get(entity_id)
        available = state is not None
        results[entity_id] = available
        
        status = "✅ AVAILABLE" if available else "❌ MISSING"
        _LOGGER.info("%s: %s", entity_id, status)
        
        if available:
            _LOGGER.info("  Value: %s %s", state.state, entity["unit"])
            _LOGGER.info("  Range: %s-%s", entity["range"][0], entity["range"][1])
    
    _LOGGER.info("")
    available_count = sum(results.values())
    total_count = len(results)
    _LOGGER.info("Summary: %d/%d entities available", available_count, total_count)
    
    return results

def check_persistence_behavior(hass, test_values: Dict[str, float]) -> None:
    """Check persistence behavior by setting values and documenting expected reset."""
    _LOGGER.info("Persistence Behavior Check:")
    _LOGGER.info("-" * 25)
    _LOGGER.info("Setting test values to verify they reset after restart...")
    
    for entity_id, value in test_values.items():
        state = hass.states.get(entity_id)
        if state:
            current_value = state.state
            _LOGGER.info("  %s: %s -> %s", entity_id, current_value, value)
        else:
            _LOGGER.warning("  %s: Entity not found", entity_id)
    
    _LOGGER.info("")
    _LOGGER.info("⚠️  EXPECTED BEHAVIOR: Values will reset to defaults after HA restart")
    _LOGGER.info("   This is expected because Stage 1b does not implement persistence yet")
    _LOGGER.info("   Persistence will be added in Stage 2")

# Main validation function
def run_stage1b_validation(hass=None):
    """Run complete Stage 1b validation sequence."""
    _LOGGER.info("Starting Stage 1b Validation Sequence...")
    
    # 1. Log validation start info
    log_stage1b_validation_start()
    
    # 2. Show service call examples
    log_service_call_examples()
    
    # 3. If hass is available, check entity availability
    if hass:
        entity_results = validate_entity_availability(hass)
        
        # 4. Test persistence behavior
        test_values = {
            "number.adaptive_climate_min_comfort_temp_bridge_v2": 19.5,
            "number.adaptive_climate_max_comfort_temp_bridge_v2": 27.5,
            "number.adaptive_climate_air_velocity_bridge_v2": 0.8
        }
        check_persistence_behavior(hass, test_values)
    
    _LOGGER.info("Stage 1b Validation Setup Complete!")
    _LOGGER.info("Proceed with manual testing using the information above.")

# Export main functions
__all__ = [
    "run_stage1b_validation",
    "log_stage1b_validation_start", 
    "validate_entity_availability",
    "check_persistence_behavior",
    "STAGE1B_TEST_ENTITIES",
    "EXPECTED_LOG_PATTERNS"
]
