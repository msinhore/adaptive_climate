
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
