#!/usr/bin/env python3
"""Test script to verify options flow registration."""

import sys
import importlib.util

# Load the config_flow module
spec = importlib.util.spec_from_file_location(
    "config_flow", 
    "custom_components/adaptive_climate/config_flow.py"
)
config_flow = importlib.util.module_from_spec(spec)

def test_options_flow():
    """Test if options flow is properly defined."""
    
    # Check if ConfigFlow class exists
    if not hasattr(config_flow, 'ConfigFlow'):
        print("❌ ConfigFlow class not found")
        return False
    
    config_flow_class = config_flow.ConfigFlow
    
    # Check if async_get_options_flow method exists
    if not hasattr(config_flow_class, 'async_get_options_flow'):
        print("❌ async_get_options_flow method not found")
        return False
    
    print("✅ ConfigFlow class found")
    print("✅ async_get_options_flow method found")
    
    # Check if OptionsFlowHandler class exists
    if not hasattr(config_flow, 'OptionsFlowHandler'):
        print("❌ OptionsFlowHandler class not found")
        return False
    
    options_flow_class = config_flow.OptionsFlowHandler
    
    # Check if async_step_init method exists
    if not hasattr(options_flow_class, 'async_step_init'):
        print("❌ async_step_init method not found in OptionsFlowHandler")
        return False
    
    print("✅ OptionsFlowHandler class found")
    print("✅ async_step_init method found")
    
    print("\n🎯 Options flow appears to be properly configured!")
    print("\nIf the configuration button is not showing:")
    print("1. Restart Home Assistant completely")
    print("2. Remove and re-add the integration")
    print("3. Check Home Assistant logs for any errors")
    
    return True

if __name__ == "__main__":
    try:
        # Try to load the module
        spec.loader.exec_module(config_flow)
        test_options_flow()
    except Exception as e:
        print(f"❌ Error loading config_flow module: {e}")
        sys.exit(1)
