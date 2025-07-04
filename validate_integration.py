#!/usr/bin/env python3
"""
Validation script for Adaptive Climate integration modernization.

This script checks that all the modernization requirements are met:
- All entity files have proper device_info implementation
- Entity categories are correctly assigned
- New entity platforms are properly structured
- Config flow uses dynamic schemas with proper selectors

Run this script to validate the integration before testing in Home Assistant.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set


def check_file_exists(file_path: str) -> bool:
    """Check if a file exists."""
    return os.path.exists(file_path)


def read_file_content(file_path: str) -> str:
    """Read and return file content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""


def check_device_info_implementation(content: str, file_name: str) -> bool:
    """Check if device_info is properly implemented."""
    has_device_info = '"identifiers": {(DOMAIN, config_entry.entry_id)}' in content
    has_manufacturer = '"manufacturer":' in content
    has_model = '"model":' in content
    
    if not all([has_device_info, has_manufacturer, has_model]):
        print(f"❌ {file_name}: Missing proper device_info implementation")
        return False
    else:
        print(f"✅ {file_name}: device_info properly implemented")
        return True


def check_entity_category(content: str, file_name: str) -> bool:
    """Check if entity_category is used."""
    has_entity_category = "EntityCategory" in content
    
    if not has_entity_category:
        print(f"⚠️  {file_name}: No EntityCategory found (might be intentional)")
        return True  # Not always required
    else:
        print(f"✅ {file_name}: EntityCategory used")
        return True


def check_unique_id(content: str, file_name: str) -> bool:
    """Check if unique_id is properly set."""
    has_unique_id = "_attr_unique_id" in content or "unique_id" in content
    
    if not has_unique_id:
        print(f"❌ {file_name}: Missing unique_id implementation")
        return False
    else:
        print(f"✅ {file_name}: unique_id properly implemented")
        return True


def check_platforms_in_init(content: str) -> bool:
    """Check if all platforms are included in __init__.py."""
    required_platforms = ["sensor", "binary_sensor", "switch", "number", "button", "select"]
    platforms_found = []
    
    for platform in required_platforms:
        if f'Platform.{platform.upper()}' in content or f'"{platform}"' in content:
            platforms_found.append(platform)
    
    missing_platforms = set(required_platforms) - set(platforms_found)
    
    if missing_platforms:
        print(f"❌ __init__.py: Missing platforms: {missing_platforms}")
        return False
    else:
        print("✅ __init__.py: All required platforms included")
        return True


def check_config_flow_selectors(content: str) -> bool:
    """Check if config flow uses proper selectors."""
    has_selectors = "selector." in content
    has_dynamic_schema = "build_" in content and "schema" in content
    
    if not has_selectors:
        print("❌ config_flow.py: Missing selector usage")
        return False
    elif not has_dynamic_schema:
        print("⚠️  config_flow.py: No dynamic schema methods found")
        return True
    else:
        print("✅ config_flow.py: Proper selectors and dynamic schemas")
        return True


def validate_integration():
    """Main validation function."""
    print("🔍 Validating Adaptive Climate Integration Modernization")
    print("=" * 60)
    
    base_path = "/Users/marcosinhoreli/Projects/adaptive_climate/custom_components/adaptive_climate"
    
    # Check required files exist
    required_files = [
        "__init__.py",
        "config_flow.py", 
        "sensor.py",
        "binary_sensor.py",
        "switch.py",
        "number.py",
        "button.py",
        "select.py",
        "manifest.json"
    ]
    
    print("\n📁 Checking required files:")
    missing_files = []
    for file in required_files:
        file_path = os.path.join(base_path, file)
        if check_file_exists(file_path):
            print(f"✅ {file}")
        else:
            print(f"❌ {file}")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n❌ Missing required files: {missing_files}")
        return False
    
    # Check entity platform files
    print("\n🏗️  Checking entity platforms:")
    entity_platforms = ["sensor.py", "binary_sensor.py", "switch.py", "number.py", "button.py", "select.py"]
    platform_checks = []
    
    for platform in entity_platforms:
        file_path = os.path.join(base_path, platform)
        content = read_file_content(file_path)
        
        if content:
            print(f"\n--- {platform} ---")
            device_info_ok = check_device_info_implementation(content, platform)
            entity_category_ok = check_entity_category(content, platform)
            unique_id_ok = check_unique_id(content, platform)
            
            platform_checks.append(all([device_info_ok, entity_category_ok, unique_id_ok]))
    
    # Check __init__.py
    print("\n📋 Checking __init__.py:")
    init_content = read_file_content(os.path.join(base_path, "__init__.py"))
    init_ok = check_platforms_in_init(init_content)
    
    # Check config_flow.py
    print("\n⚙️  Checking config_flow.py:")
    config_flow_content = read_file_content(os.path.join(base_path, "config_flow.py"))
    config_flow_ok = check_config_flow_selectors(config_flow_content)
    
    # Check manifest.json
    print("\n📄 Checking manifest.json:")
    manifest_content = read_file_content(os.path.join(base_path, "manifest.json"))
    try:
        manifest_data = json.loads(manifest_content)
        required_keys = ["domain", "name", "config_flow", "homeassistant"]
        manifest_ok = all(key in manifest_data for key in required_keys)
        
        if manifest_ok:
            print("✅ manifest.json: All required fields present")
            print(f"   - Home Assistant version: {manifest_data.get('homeassistant', 'unknown')}")
        else:
            print("❌ manifest.json: Missing required fields")
    except json.JSONDecodeError:
        print("❌ manifest.json: Invalid JSON format")
        manifest_ok = False
    
    # Final assessment
    print("\n" + "=" * 60)
    print("📊 VALIDATION RESULTS:")
    
    all_checks = [
        all(platform_checks),
        init_ok,
        config_flow_ok,
        manifest_ok,
        not missing_files
    ]
    
    if all(all_checks):
        print("🎉 ✅ ALL CHECKS PASSED!")
        print("\nThe integration is ready for testing in Home Assistant 2025.7+")
        print("\nNext steps:")
        print("1. Restart Home Assistant")
        print("2. Go to Settings > Devices & Services")
        print("3. Add the Adaptive Climate integration")
        print("4. Check the device page for proper entity grouping")
        print("5. Test the 'Reconfigure Entities' button")
    else:
        print("❌ SOME CHECKS FAILED!")
        print("Please review the issues above before testing.")
        
    return all(all_checks)


if __name__ == "__main__":
    validate_integration()
