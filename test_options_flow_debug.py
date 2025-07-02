#!/usr/bin/env python3
"""Test script to verify options flow configuration."""

import os
import sys
import json

def check_config_flow_structure():
    """Check if config flow structure is correct."""
    print("🔍 Checking config flow structure...")
    
    try:
        with open("custom_components/adaptive_climate/config_flow.py", "r") as f:
            content = f.read()
        
        # Check for required components
        required_components = [
            "class AdaptiveClimateConfigFlow",
            "async_get_options_flow",
            "class OptionsFlowHandler",
            "async_step_init",
            "config_entries.OptionsFlow"
        ]
        
        missing = []
        for component in required_components:
            if component not in content:
                missing.append(component)
        
        if not missing:
            print("✅ All required config flow components found")
        else:
            print(f"❌ Missing components: {missing}")
            return False
        
        # Check if OptionsFlowHandler extends OptionsFlow correctly
        if "class OptionsFlowHandler(config_entries.OptionsFlow):" in content:
            print("✅ OptionsFlowHandler correctly extends config_entries.OptionsFlow")
        else:
            print("❌ OptionsFlowHandler inheritance issue")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking config flow: {e}")
        return False

def check_manifest_config():
    """Check manifest configuration."""
    print("\n📋 Checking manifest.json...")
    
    try:
        with open("custom_components/adaptive_climate/manifest.json", "r") as f:
            manifest = json.load(f)
        
        # Check required fields for config flow
        if manifest.get("config_flow") is True:
            print("✅ config_flow is enabled in manifest")
        else:
            print("❌ config_flow is not enabled in manifest")
            return False
        
        # Check integration type
        integration_type = manifest.get("integration_type")
        if integration_type:
            print(f"ℹ️  Integration type: {integration_type}")
        
        # Check HA version requirement
        ha_version = manifest.get("homeassistant")
        if ha_version:
            print(f"ℹ️  Required HA version: {ha_version}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking manifest: {e}")
        return False

def check_options_flow_implementation():
    """Check specific options flow implementation details."""
    print("\n🔧 Checking options flow implementation...")
    
    try:
        with open("custom_components/adaptive_climate/config_flow.py", "r") as f:
            content = f.read()
        
        # Look for async_step_init method
        if "async def async_step_init(self, user_input=None):" in content:
            print("✅ async_step_init method found")
        else:
            print("❌ async_step_init method missing")
            return False
        
        # Check for async_create_entry calls
        if "async_create_entry" in content:
            print("✅ async_create_entry calls found")
        else:
            print("❌ async_create_entry calls missing")
            return False
        
        # Check for form display
        if "async_show_form" in content:
            print("✅ async_show_form calls found")
        else:
            print("❌ async_show_form calls missing")
            return False
        
        # Check for proper schema
        if "vol.Schema" in content:
            print("✅ Voluptuous schema found")
        else:
            print("❌ Voluptuous schema missing")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking options flow: {e}")
        return False

def check_coordinator_update_method():
    """Check if coordinator has proper update_config method."""
    print("\n🔄 Checking coordinator update method...")
    
    try:
        with open("custom_components/adaptive_climate/coordinator.py", "r") as f:
            content = f.read()
        
        if "async def update_config(self, config_updates: dict[str, Any]) -> None:" in content:
            print("✅ Coordinator update_config method found")
        else:
            print("❌ Coordinator update_config method missing")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking coordinator: {e}")
        return False

def check_init_update_listener():
    """Check if __init__.py has update listener setup."""
    print("\n👂 Checking update listener setup...")
    
    try:
        with open("custom_components/adaptive_climate/__init__.py", "r") as f:
            content = f.read()
        
        if "add_update_listener" in content:
            print("✅ Update listener setup found")
        else:
            print("❌ Update listener setup missing")
            return False
            
        if "_async_update_listener" in content:
            print("✅ Update listener function found")
        else:
            print("❌ Update listener function missing")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking __init__.py: {e}")
        return False

def generate_debug_info():
    """Generate debug information for troubleshooting."""
    print("\n🐛 Generating debug information...")
    
    debug_info = {
        "files_checked": [
            "custom_components/adaptive_climate/config_flow.py",
            "custom_components/adaptive_climate/manifest.json",
            "custom_components/adaptive_climate/coordinator.py",
            "custom_components/adaptive_climate/__init__.py"
        ],
        "common_issues": [
            "1. Check if Home Assistant has been restarted after installing the integration",
            "2. Verify that the integration is properly loaded in HA logs",
            "3. Check if there are any import errors in the logs",
            "4. Ensure the config entry is not in a 'disabled' state",
            "5. Try removing and re-adding the integration",
            "6. Check Developer Tools > States for any error states"
        ],
        "troubleshooting_steps": [
            "1. Go to Settings > Devices & Services",
            "2. Find 'Adaptive Climate' integration",
            "3. Click on the integration name (not the device)",
            "4. Look for 'Configure' button or three-dot menu",
            "5. If not visible, check HA logs for config flow errors"
        ]
    }
    
    with open("options_flow_debug_info.json", "w") as f:
        json.dump(debug_info, f, indent=2)
    
    print("📝 Debug info saved to options_flow_debug_info.json")

def main():
    """Main function."""
    print("🔍 Adaptive Climate Options Flow Diagnostic")
    print("=" * 50)
    
    # Change to project directory
    os.chdir("/Users/marcosinhoreli/Projects/adaptive_climate")
    
    all_checks = [
        check_config_flow_structure(),
        check_manifest_config(),
        check_options_flow_implementation(),
        check_coordinator_update_method(),
        check_init_update_listener()
    ]
    
    if all(all_checks):
        print("\n✅ All checks passed!")
        print("\n💡 If the options flow still doesn't work:")
        print("1. Restart Home Assistant completely")
        print("2. Check Home Assistant logs for any errors")
        print("3. Try removing and re-adding the integration")
        print("4. Ensure you're using Home Assistant 2025.6.0 or later")
    else:
        print("\n❌ Some checks failed.")
        print("Please review the issues above.")
    
    generate_debug_info()
    
    return 0 if all(all_checks) else 1

if __name__ == "__main__":
    sys.exit(main())
