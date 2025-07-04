# Adaptive Climate Integration Testing Guide

This guide helps you test the modernized Adaptive Climate integration in Home Assistant 2025.7+.

## 🚀 Pre-Testing Setup

1. **Backup your Home Assistant configuration** before testing
2. Ensure you're running Home Assistant 2025.6.0 or later
3. Have some climate entities and temperature sensors available for testing

## 📋 Testing Checklist

### ✅ Initial Setup
- [ ] Integration installs without errors
- [ ] Config flow completes successfully
- [ ] All linked entities are properly selected

### ✅ Device Page Layout
Navigate to **Settings > Devices & Services > Adaptive Climate > [Your Device]**

#### Controls Tab
Should contain:
- [ ] **Adaptive Climate Enabled** (switch)
- [ ] **Comfort Category** (select: I, II, III)
- [ ] **Target Temperature** (number input)
- [ ] **Temperature Tolerance** (number input)  
- [ ] **Min Comfort Temperature** (number input)
- [ ] **Max Comfort Temperature** (number input)
- [ ] **Air Velocity** (number input)
- [ ] **Setback Offset** (number input)
- [ ] **Prolonged Absence** (number input)
- [ ] **Auto Shutdown** (number input)
- [ ] **Reconfigure Entities** (button)

#### Sensors Tab  
Should contain:
- [ ] **Indoor Temperature** (sensor)
- [ ] **Outdoor Temperature** (sensor)
- [ ] **Comfort Temperature Min** (sensor)
- [ ] **Comfort Temperature Max** (sensor)
- [ ] **Status** (sensor)

#### Diagnostic Tab
Should contain:
- [ ] **ASHRAE Compliance** (binary sensor)
- [ ] **Natural Ventilation** (binary sensor)

### ✅ Functionality Tests

#### Configuration Changes
- [ ] Change **Comfort Category** → Verify sensors update
- [ ] Adjust **Target Temperature** → Verify climate entity responds
- [ ] Toggle **Adaptive Climate Enabled** → Verify behavior changes

#### Reconfiguration Test
- [ ] Click **Reconfigure Entities** button
- [ ] Confirm deletion dialog appears
- [ ] Complete reconfiguration flow
- [ ] Verify new entity selection works
- [ ] Check all entities appear correctly on device page

#### Entity Behavior
- [ ] **ASHRAE Compliance** shows correct status
- [ ] **Natural Ventilation** reflects outdoor conditions
- [ ] **Status** sensor shows meaningful states
- [ ] Temperature sensors display current values

### ✅ Advanced Testing

#### Options Flow
- [ ] Go to integration options (Configure button)
- [ ] Verify all current values show as defaults
- [ ] Change multiple settings and save
- [ ] Confirm changes take effect

#### Climate Integration
- [ ] Linked climate entity responds to comfort range changes
- [ ] Temperature setback works during absence
- [ ] Auto-shutdown activates after configured time

## 🐛 Common Issues & Solutions

### Issue: Entities not appearing in correct tabs
**Solution:** Check entity_category assignments in entity files

### Issue: Reconfigure button doesn't work
**Solution:** Verify config_entries module is properly imported

### Issue: Sensors showing "Unknown" values
**Solution:** Check if linked entities are available and returning data

### Issue: Config flow validation errors
**Solution:** Ensure all entity IDs exist and are accessible

## 📊 Expected Entity Categories

| Entity Type | Tab | Category |
|-------------|-----|----------|
| Switches (config) | Controls | CONFIG |
| Numbers (config) | Controls | CONFIG |
| Select (comfort) | Controls | CONFIG |
| Button (reconfigure) | Controls | CONFIG |
| Temperature sensors | Sensors | None |
| Status sensor | Sensors | None |
| Binary sensors | Diagnostic | DIAGNOSTIC |

## 🔧 Debugging Tips

1. **Check Home Assistant logs** for any error messages
2. **Enable debug logging** for adaptive_climate domain
3. **Use Developer Tools** to inspect entity states
4. **Verify entity registry** entries are properly created

## 📝 Reporting Issues

If you encounter problems:

1. **Gather logs** from Home Assistant
2. **Note your configuration** (entity IDs used)
3. **Describe expected vs actual behavior**
4. **Include Home Assistant version**

## ✨ New Features Summary

This modernization brings:

- **Organized device page** with proper Controls/Sensors/Diagnostic tabs
- **Dynamic reconfiguration** of linked entities without reinstalling
- **Modern UI selectors** in config and options flows  
- **Better entity categorization** for improved UX
- **Compatibility** with Home Assistant 2025.7+ standards

## 🎯 Success Criteria

The test is successful when:

1. ✅ All entities appear in the correct device page tabs
2. ✅ Configuration controls work and update the integration
3. ✅ Reconfigure Entities button works properly
4. ✅ No errors in Home Assistant logs
5. ✅ Climate control functions as expected

---

Happy testing! 🏠🌡️
