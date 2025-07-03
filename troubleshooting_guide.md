# Comprehensive Troubleshooting Guide for "No matching entities found" Issue

This guide provides step-by-step solutions to resolve the "No matching entities found" issue when configuring the Adaptive Climate integration.

## Root Causes

This issue typically occurred for one of the following reasons:

1. **Area Filtering**: Area-based entity filtering was causing selectors to show "No matching entities found"
2. **Entity Registry**: Issues with entity registration or area ID mapping
3. **Selector Configuration**: Problems with how entity selectors were configured
4. **Browser Cache**: Stale data in your browser cache
5. **Permissions**: The user doesn't have proper permissions to access entities

**UPDATE:** We've removed area-based entity filtering from the config flow to fix this issue. Now all selectors will show all relevant entities regardless of area selection. The area is still stored and used for organizational purposes, but it no longer affects which entities are shown in the dropdown selectors.

## Diagnostic Steps

### 1. Check Area Assignments

First, verify that your entities are correctly assigned to areas:

1. Go to **Settings → Devices & Services → Entities**
2. Filter for entities you want to use (e.g., search for "climate" or "temperature")
3. Check if each entity has an area assigned
4. If not, click the entity, then click the gear icon to edit, and assign an area

### 2. Use the Diagnostic Template

Use our diagnostic template to verify entity-area assignments:

1. Copy the template from [diagnostic_template.md](diagnostic_template.md)
2. Go to **Developer Tools → Template**
3. Paste the template, modify the area name, and check the results
4. Verify that your climate and temperature entities appear under the correct area

### 3. Check Entity Types and Attributes

For temperature sensors to be recognized properly:

1. They must either:
   - Have a `device_class` of "temperature"
   - Have a `unit_of_measurement` of "°C" or "°F"
2. For climate entities, they must have domain "climate"

### 4. Debug Home Assistant Logs

Enable debug logging:

1. Add to your `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.adaptive_climate: debug
   ```
2. Restart Home Assistant
3. Try setting up the integration again
4. Check the logs for error messages or debugging information

## Solutions

### Solution 1: Fix Area Assignments

1. Go to **Settings → Areas & Zones**
2. Ensure all your areas are correctly set up
3. Go to **Settings → Devices & Services → Entities**
4. Assign each climate entity and temperature sensor to the correct area
5. Restart Home Assistant

### Solution 2: Area Selection

Area-based entity filtering has been removed from the config flow. Now:

1. **Area Is Optional**: The area field is still available but only for organizational purposes
2. **All Entities Are Shown**: All relevant entities are shown in selectors regardless of area selection
3. **Use Device Class**: Entities are filtered by device class and domain, not by area

### Solution 3: Update Browser and Clear Cache

1. Clear your browser cache
2. Try a different browser
3. Use an incognito/private window

### Solution 4: Advanced Troubleshooting

If none of the above solutions work:

1. **Check entity registry integrity**:
   - Look at `.storage/core.entity_registry` file
   - Verify area_id assignments are correct

2. **Run our diagnostic script**:
   - Set up Python scripting in Home Assistant
   - Use the script in [diagnostic_tool.py](diagnostic_tool.py)
   - Check the detailed output

3. **Try with device_class filtering**:
   The updated code now uses device_class filtering in addition to include_entities, which should help catch temperature sensors even if area filtering isn't working correctly.

## Last Resort Solutions

### Solution A: Database Fix

If entity-area assignments seem correct but still don't work:

1. Stop Home Assistant
2. Make a backup of `.storage/core.entity_registry`
3. Edit the file to manually fix area_id assignments
4. Restart Home Assistant

### Solution B: Reinstall Integration

1. Remove the Adaptive Climate integration
2. Restart Home Assistant
3. Install the integration again

### Solution C: Directly Edit Config Entry

For advanced users:

1. Stop Home Assistant
2. Edit `.storage/core.config_entries`
3. Find the entry for Adaptive Climate
4. Manually edit the configuration to include your entity IDs
5. Restart Home Assistant

## Need More Help?

If you're still experiencing issues:

1. Submit a GitHub issue with:
   - Home Assistant version
   - Integration version
   - Output from diagnostic templates
   - Log files
   - Screenshots of the problem

2. Join our community support channels for assistance
