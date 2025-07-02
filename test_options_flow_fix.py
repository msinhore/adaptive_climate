#!/usr/bin/env python3
"""Test script for options flow debugging with specific fixes."""

import os
import json

def check_config_flow_fixes():
    """Check if the recent fixes are applied correctly."""
    print("🔧 Checking Options Flow Fixes...")
    
    try:
        with open("custom_components/adaptive_climate/config_flow.py", "r") as f:
            content = f.read()
        
        fixes_applied = []
        
        # Check if class name is correct
        if "class AdaptiveClimateConfigFlow(" in content:
            fixes_applied.append("✅ Config flow class name corrected")
        else:
            fixes_applied.append("❌ Config flow class name still incorrect")
        
        # Check if error handling is in place
        if "try:" in content and "except KeyError:" in content:
            fixes_applied.append("✅ Error handling for coordinator access added")
        else:
            fixes_applied.append("❌ Error handling missing")
        
        # Check if entity updates are handled
        if "async_update_entry" in content:
            fixes_applied.append("✅ Entity updates handling added")
        else:
            fixes_applied.append("❌ Entity updates handling missing")
        
        # Check if reset flags are properly filtered
        if 'k != "reset_outdoor_history"' in content:
            fixes_applied.append("✅ Reset flags filtering implemented")
        else:
            fixes_applied.append("❌ Reset flags filtering missing")
        
        for fix in fixes_applied:
            print(f"  {fix}")
        
        return all("✅" in fix for fix in fixes_applied)
        
    except Exception as e:
        print(f"❌ Error checking fixes: {e}")
        return False

def generate_test_config_entry():
    """Generate a test configuration to verify structure."""
    print("\n📋 Generating test configuration structure...")
    
    test_config = {
        "data": {
            "name": "Adaptive Climate Test",
            "climate_entity": "climate.test_hvac",
            "indoor_temp_sensor": "sensor.indoor_temperature",
            "outdoor_temp_sensor": "sensor.outdoor_temperature",
            "occupancy_sensor": "binary_sensor.motion_sensor",
            "comfort_category": "II"
        },
        "options": {
            "energy_save_mode": True,
            "natural_ventilation_enable": True,
            "adaptive_air_velocity": False,
            "humidity_comfort_enable": True,
            "comfort_precision_mode": False,
            "use_occupancy_features": True,
            "auto_shutdown_enable": False,
            "use_operative_temperature": False,
            "min_comfort_temp": 18.0,
            "max_comfort_temp": 28.0,
            "temperature_change_threshold": 0.5,
            "air_velocity": 0.1,
            "natural_ventilation_threshold": 2.0,
            "setback_temperature_offset": 2.0,
            "prolonged_absence_minutes": 60,
            "auto_shutdown_minutes": 120
        }
    }
    
    with open("test_config_entry.json", "w") as f:
        json.dump(test_config, f, indent=2)
    
    print("✅ Test configuration saved to test_config_entry.json")
    return True

def create_troubleshooting_guide():
    """Create a comprehensive troubleshooting guide."""
    print("\n📖 Creating troubleshooting guide...")
    
    guide = """
# Adaptive Climate Options Flow Troubleshooting Guide

## Common Issues and Solutions

### 1. Configuration Button Not Appearing

**Symptoms:**
- No "Configure" button visible on the device page
- Only device settings visible, no integration settings

**Solutions:**
1. **Restart Home Assistant completely** (not just reload integrations)
2. Check Home Assistant logs for config flow errors:
   ```
   Settings > System > Logs
   Search for: "adaptive_climate" or "config_flow"
   ```
3. Verify integration is properly loaded:
   ```
   Developer Tools > States
   Look for entities starting with adaptive_climate.*
   ```

### 2. Configuration Changes Not Saving

**Symptoms:**
- Configuration form submits but values don't persist
- Values reset to defaults after restart

**Solutions:**
1. Check for coordinator errors in logs
2. Verify the update listener is working
3. Try removing and re-adding the integration

### 3. Integration Not Loading

**Symptoms:**
- Integration appears in HACS but not in HA
- Import errors in logs

**Solutions:**
1. Check Home Assistant version (requires 2025.6.0+)
2. Verify all required files are present
3. Check for Python syntax errors

## Step-by-Step Debugging

### Step 1: Verify Installation
1. Go to HACS > Integrations
2. Find "Adaptive Climate" 
3. Ensure it shows "Installed"
4. Note the version number

### Step 2: Check Integration Status
1. Go to Settings > Devices & Services
2. Look for "Adaptive Climate" integration
3. Note any error states or warnings

### Step 3: Examine Logs
1. Go to Settings > System > Logs
2. Filter by "adaptive_climate"
3. Look for errors during startup or configuration

### Step 4: Test Configuration
1. Click on the integration name (not the device)
2. Look for "Configure" option
3. If missing, check logs for config flow errors

### Step 5: Restart and Retry
1. Restart Home Assistant completely
2. Wait for full startup (check logs)
3. Try accessing configuration again

## Manual Configuration Reset

If configuration is corrupted, you can manually reset:

1. Stop Home Assistant
2. Edit `.storage/core.config_entries`
3. Find the adaptive_climate entry
4. Remove or reset the options section
5. Restart Home Assistant

## Contact Support

If issues persist:
1. Enable debug logging:
   ```yaml
   logger:
     logs:
       custom_components.adaptive_climate: debug
   ```
2. Reproduce the issue
3. Collect logs and configuration
4. Report on GitHub Issues with details

## Version Compatibility

- Home Assistant: 2025.6.0 or later
- Python: 3.11 or later
- Integration Version: 0.1.4+
"""
    
    with open("OPTIONS_FLOW_TROUBLESHOOTING.md", "w") as f:
        f.write(guide)
    
    print("✅ Troubleshooting guide saved to OPTIONS_FLOW_TROUBLESHOOTING.md")
    return True

def main():
    """Main function."""
    print("🔧 Adaptive Climate Options Flow Debug & Fix")
    print("=" * 50)
    
    # Change to project directory
    os.chdir("/Users/marcosinhoreli/Projects/adaptive_climate")
    
    # Run checks
    config_ok = check_config_flow_fixes()
    test_ok = generate_test_config_entry()
    guide_ok = create_troubleshooting_guide()
    
    print("\n" + "=" * 50)
    if config_ok and test_ok and guide_ok:
        print("✅ All fixes applied and documentation created!")
        print("\n🚀 Next Steps:")
        print("1. Commit the changes")
        print("2. Restart Home Assistant")
        print("3. Test the options flow")
        print("4. Check the troubleshooting guide if issues persist")
    else:
        print("❌ Some issues detected. Please review the output above.")
    
    return 0 if (config_ok and test_ok and guide_ok) else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
"""
Test and fix script for options flow functionality.
"""
