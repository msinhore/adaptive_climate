#!/usr/bin/env python3
"""Debug script to test options flow detection."""

import sys
import os

# Add the custom component to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components', 'adaptive_climate'))

def test_options_flow():
    """Test if options flow is properly configured."""
    try:
        from config_flow import ConfigFlow, OptionsFlowHandler
        from const import DOMAIN
        
        print(f"✅ Successfully imported ConfigFlow and OptionsFlowHandler")
        print(f"✅ Domain: {DOMAIN}")
        
        # Test if ConfigFlow has the required method
        if hasattr(ConfigFlow, 'async_get_options_flow'):
            print("✅ ConfigFlow has async_get_options_flow method")
            
            # Test if it's static
            method = getattr(ConfigFlow, 'async_get_options_flow')
            if isinstance(method, staticmethod):
                print("✅ async_get_options_flow is a static method")
            else:
                print("❌ async_get_options_flow is NOT a static method")
                
        else:
            print("❌ ConfigFlow missing async_get_options_flow method")
            
        # Test OptionsFlowHandler
        if hasattr(OptionsFlowHandler, 'async_step_init'):
            print("✅ OptionsFlowHandler has async_step_init method")
        else:
            print("❌ OptionsFlowHandler missing async_step_init method")
            
        # Test domain inheritance
        if hasattr(ConfigFlow, '__orig_bases__'):
            bases = ConfigFlow.__orig_bases__
            print(f"✅ ConfigFlow inheritance: {bases}")
        
        print("\n🔍 ConfigFlow class info:")
        print(f"   - VERSION: {getattr(ConfigFlow, 'VERSION', 'NOT_FOUND')}")
        print(f"   - MINOR_VERSION: {getattr(ConfigFlow, 'MINOR_VERSION', 'NOT_FOUND')}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Testing Adaptive Climate Options Flow Configuration")
    print("=" * 60)
    
    success = test_options_flow()
    
    if success:
        print("\n✅ All basic checks passed!")
        print("If the configuration button still doesn't appear:")
        print("1. Restart Home Assistant completely")
        print("2. Check Home Assistant logs for config_flow errors")
        print("3. Verify the integration is loaded correctly")
    else:
        print("\n❌ Configuration issues found!")
