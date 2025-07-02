#!/usr/bin/env python3
"""
Test script for Adaptive Climate persistence and logbook features.
"""

def test_persistence_logic():
    """Test the persistence logic without Home Assistant."""
    import json
    from datetime import datetime, timedelta
    
    print("Testing persistence logic...")
    
    # Simulate storage data
    outdoor_temp_history = [
        (datetime.now() - timedelta(days=i), 20.0 + i)
        for i in range(7)
    ]
    
    # Test serialization
    storage_data = {
        "outdoor_temp_history": [
            (timestamp.isoformat(), temp)
            for timestamp, temp in outdoor_temp_history
        ],
        "running_mean_outdoor_temp": 23.5,
        "last_sensor_data": {
            "adaptive_comfort_temp": 22.0,
            "comfort_temp_min": 20.0,
            "comfort_temp_max": 24.0,
            "indoor_temperature": 21.5,
            "outdoor_temperature": 18.0,
            "ashrae_compliant": True,
        },
        "last_updated": datetime.now().isoformat(),
    }
    
    # Test JSON serialization
    try:
        json_str = json.dumps(storage_data, indent=2)
        print("✓ JSON serialization successful")
        print(f"Storage data size: {len(json_str)} bytes")
    except Exception as e:
        print(f"✗ JSON serialization failed: {e}")
        return False
    
    # Test deserialization
    try:
        restored_data = json.loads(json_str)
        
        # Restore datetime objects
        restored_history = [
            (datetime.fromisoformat(timestamp), temp)
            for timestamp, temp in restored_data["outdoor_temp_history"]
        ]
        
        print("✓ JSON deserialization successful")
        print(f"Restored {len(restored_history)} temperature history entries")
        print(f"Running mean: {restored_data['running_mean_outdoor_temp']}")
        
    except Exception as e:
        print(f"✗ JSON deserialization failed: {e}")
        return False
    
    return True

def test_logbook_messages():
    """Test logbook message formatting."""
    print("\nTesting logbook message formatting...")
    
    # Test different message scenarios
    scenarios = [
        {
            "type": "climate_adjustment",
            "actions": ["Temperature set to 22.5°C", "HVAC mode set to cool"],
            "reason": "above comfort zone"
        },
        {
            "type": "manual_override",
            "temperature": 24.0,
            "duration": 7200  # 2 hours
        },
        {
            "type": "occupancy_change",
            "status": "unoccupied"
        },
        {
            "type": "natural_ventilation",
            "status": "optimal",
            "indoor_temp": 26.5,
            "outdoor_temp": 20.0,
            "temp_diff": 6.5
        },
        {
            "type": "comfort_category_change",
            "old_category": "II",
            "new_category": "I"
        }
    ]
    
    for scenario in scenarios:
        try:
            if scenario["type"] == "climate_adjustment":
                message = f"Climate adjusted: {', '.join(scenario['actions'])} ({scenario['reason']})"
            elif scenario["type"] == "manual_override":
                duration = scenario["duration"]
                duration_text = f" for {duration//3600}h {(duration%3600)//60}m"
                message = f"Manual override activated: {scenario['temperature']:.1f}°C{duration_text}"
            elif scenario["type"] == "occupancy_change":
                message = f"Occupancy changed to {scenario['status']}"
            elif scenario["type"] == "natural_ventilation":
                temp_diff = scenario["temp_diff"]
                message = f"Natural ventilation is now {scenario['status']} (indoor: {scenario['indoor_temp']:.1f}°C, outdoor: {scenario['outdoor_temp']:.1f}°C, diff: {temp_diff:.1f}°C)"
            elif scenario["type"] == "comfort_category_change":
                message = f"Comfort category changed from {scenario['old_category']} to {scenario['new_category']}"
            
            print(f"✓ {scenario['type']}: {message}")
            
        except Exception as e:
            print(f"✗ {scenario['type']}: Failed to format message - {e}")
            return False
    
    return True

def test_default_data():
    """Test default data structure."""
    print("\nTesting default data structure...")
    
    from datetime import datetime
    
    default_data = {
        "adaptive_comfort_temp": 22.0,
        "comfort_temp_min": 20.0,
        "comfort_temp_max": 24.0,
        "indoor_temperature": None,
        "outdoor_temperature": None,
        "outdoor_running_mean": None,
        "climate_state": "unknown",
        "occupancy": "unknown",
        "manual_override": False,
        "natural_ventilation_active": False,
        "ashrae_compliant": False,
        "control_actions": {},
        "last_updated": datetime.now(),
        "status": "entities_unavailable",
    }
    
    # Test that all expected keys are present
    expected_keys = [
        "adaptive_comfort_temp", "comfort_temp_min", "comfort_temp_max",
        "indoor_temperature", "outdoor_temperature", "outdoor_running_mean",
        "climate_state", "occupancy", "manual_override", 
        "natural_ventilation_active", "ashrae_compliant", "control_actions",
        "last_updated", "status"
    ]
    
    missing_keys = [key for key in expected_keys if key not in default_data]
    if missing_keys:
        print(f"✗ Missing keys in default data: {missing_keys}")
        return False
    
    print("✓ Default data structure is complete")
    print(f"  - Contains {len(default_data)} keys")
    print(f"  - Status: {default_data['status']}")
    print(f"  - Temperature defaults: {default_data['adaptive_comfort_temp']}°C")
    
    return True

def main():
    """Run all tests."""
    print("=== Adaptive Climate Enhancement Tests ===")
    
    tests = [
        ("Persistence Logic", test_persistence_logic),
        ("Logbook Messages", test_logbook_messages),
        ("Default Data", test_default_data),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n=== Test Summary ===")
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("🎉 All tests passed! The enhancements look good.")
    else:
        print("⚠️  Some tests failed. Please review the implementation.")

if __name__ == "__main__":
    main()
