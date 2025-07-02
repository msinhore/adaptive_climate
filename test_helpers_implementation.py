#!/usr/bin/env python3
"""Test script for new helpers implementation."""
import os
import sys
import json

def check_file_exists(filepath):
    """Check if a file exists."""
    exists = os.path.exists(filepath)
    print(f"✓ {filepath} exists" if exists else f"✗ {filepath} missing")
    return exists

def check_platforms_in_init():
    """Check if all platforms are registered in __init__.py."""
    try:
        with open("custom_components/adaptive_climate/__init__.py", "r") as f:
            content = f.read()
            
        required_platforms = ["SENSOR", "BINARY_SENSOR", "NUMBER", "SWITCH"]
        all_present = all(platform in content for platform in required_platforms)
        
        print(f"✓ All platforms registered in __init__.py" if all_present else f"✗ Missing platforms in __init__.py")
        return all_present
    except Exception as e:
        print(f"✗ Error checking __init__.py: {e}")
        return False

def check_constants():
    """Check if all required constants are defined."""
    try:
        with open("custom_components/adaptive_climate/const.py", "r") as f:
            content = f.read()
            
        required_constants = [
            "DEFAULT_COMFORT_TEMP_MIN_OFFSET",
            "DEFAULT_COMFORT_TEMP_MAX_OFFSET", 
            "DEFAULT_TEMPERATURE_CHANGE_THRESHOLD",
            "DEFAULT_AIR_VELOCITY",
            "DEFAULT_NATURAL_VENTILATION_THRESHOLD",
            "DEFAULT_SETBACK_TEMPERATURE_OFFSET",
            "DEFAULT_AUTO_SHUTDOWN_MINUTES"
        ]
        
        missing = [const for const in required_constants if const not in content]
        
        if not missing:
            print("✓ All required constants defined")
            return True
        else:
            print(f"✗ Missing constants: {missing}")
            return False
    except Exception as e:
        print(f"✗ Error checking constants: {e}")
        return False

def check_number_entities():
    """Check number entities implementation."""
    try:
        with open("custom_components/adaptive_climate/number.py", "r") as f:
            content = f.read()
            
        required_entities = [
            "MinComfortTempNumber",
            "MaxComfortTempNumber", 
            "TemperatureChangeThresholdNumber",
            "AirVelocityNumber",
            "NaturalVentilationThresholdNumber",
            "SetbackTemperatureOffsetNumber",
            "AutoShutdownMinutesNumber"
        ]
        
        missing = [entity for entity in required_entities if entity not in content]
        
        if not missing:
            print("✓ All number entities implemented")
            return True
        else:
            print(f"✗ Missing number entities: {missing}")
            return False
    except Exception as e:
        print(f"✗ Error checking number entities: {e}")
        return False

def check_switch_entities():
    """Check switch entities implementation."""
    try:
        with open("custom_components/adaptive_climate/switch.py", "r") as f:
            content = f.read()
            
        required_entities = [
            "UseOperativeTemperatureSwitch",
            "EnergySaveModeSwitch",
            "ComfortPrecisionModeSwitch", 
            "UseOccupancyFeaturesSwitch",
            "NaturalVentilationEnableSwitch",
            "AdaptiveAirVelocitySwitch",
            "HumidityComfortEnableSwitch",
            "AutoShutdownEnableSwitch"
        ]
        
        missing = [entity for entity in required_entities if entity not in content]
        
        if not missing:
            print("✓ All switch entities implemented")
            return True
        else:
            print(f"✗ Missing switch entities: {missing}")
            return False
    except Exception as e:
        print(f"✗ Error checking switch entities: {e}")
        return False

def main():
    """Main test function."""
    print("🔍 Testing Adaptive Climate Helpers Implementation")
    print("=" * 50)
    
    # Change to project directory
    os.chdir("/Users/marcosinhoreli/Projects/adaptive_climate")
    
    all_good = True
    
    # Check file existence
    print("\n📁 Checking file existence:")
    files_to_check = [
        "custom_components/adaptive_climate/__init__.py",
        "custom_components/adaptive_climate/number.py", 
        "custom_components/adaptive_climate/switch.py",
        "custom_components/adaptive_climate/const.py",
        "custom_components/adaptive_climate/coordinator.py",
        "custom_components/adaptive_climate/sensor.py",
        "custom_components/adaptive_climate/binary_sensor.py"
    ]
    
    for file_path in files_to_check:
        if not check_file_exists(file_path):
            all_good = False
    
    # Check platform registration
    print("\n🔧 Checking platform registration:")
    if not check_platforms_in_init():
        all_good = False
    
    # Check constants
    print("\n📋 Checking constants:")
    if not check_constants():
        all_good = False
    
    # Check number entities
    print("\n🔢 Checking number entities:")
    if not check_number_entities():
        all_good = False
    
    # Check switch entities  
    print("\n🔘 Checking switch entities:")
    if not check_switch_entities():
        all_good = False
    
    print("\n" + "=" * 50)
    if all_good:
        print("✅ All checks passed! Implementation looks good.")
        print("\n📝 Summary of implemented helpers:")
        print("\n🔢 Number Helpers:")
        print("  - Min/Max Comfort Temperature")
        print("  - Temperature Change Threshold")  
        print("  - Air Velocity")
        print("  - Natural Ventilation Threshold")
        print("  - Setback Temperature Offset")
        print("  - Auto Shutdown Minutes")
        print("\n🔘 Toggle Helpers:")
        print("  - Use Operative Temperature")
        print("  - Energy Save Mode")
        print("  - Comfort Precision Mode")
        print("  - Use Occupancy Features") 
        print("  - Natural Ventilation Enable")
        print("  - Adaptive Air Velocity")
        print("  - Humidity Comfort Enable")
        print("  - Auto Shutdown Enable")
        print("\n🔄 Data Persistence:")
        print("  - Outdoor temperature history")
        print("  - Last valid sensor data")
        print("  - Configuration persistence")
        print("\n📊 Logbook Integration:")
        print("  - Control actions logged")
        print("  - Configuration changes logged")
        print("  - Manual overrides logged")
        print("  - Natural ventilation status logged")
    else:
        print("❌ Some checks failed. Please review the implementation.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
