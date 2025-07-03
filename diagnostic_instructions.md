# Using this diagnostic tool

This diagnostic tool helps identify and fix the "No matching entities found" issue in the Adaptive Climate integration.

## Setup Instructions

1. First, add the following to your Home Assistant configuration:

   ```yaml
   # In configuration.yaml
   python_script:

   logger:
     default: info
     logs:
       custom_components.adaptive_climate: debug
   ```

2. Create a Python script in your `<config>/python_scripts` directory:

   ```python
   # In <config>/python_scripts/adaptive_climate_diagnostics.py
   helper = hass.data["custom_components.adaptive_climate"].get_area_helper(hass)
   if helper:
       diagnostics = helper.dump_entity_registry_assignments()
       
       # Log main statistics
       logger.info(f"Total entities: {diagnostics['entity_count']}")
       logger.info(f"Entities with area: {diagnostics['entities_with_area']}")
       logger.info(f"Entities without area: {diagnostics['entities_without_area']}")
       
       # Log climate entities
       for entity in diagnostics['climate_entities']:
           logger.info(f"Climate: {entity['entity_id']} - Area: {entity['area_name']}")
       
       # Log temperature sensors
       for entity in diagnostics['temperature_sensors']:
           logger.info(f"Temperature: {entity['entity_id']} - Area: {entity['area_name']}")
       
       # Create persistent notification with summary
       hass.services.call(
           "persistent_notification", 
           "create", 
           {
               "title": "Adaptive Climate Diagnostics",
               "message": f"Total entities: {diagnostics['entity_count']}\n"
                          f"Entities with area: {diagnostics['entities_with_area']}\n"
                          f"Entities without area: {diagnostics['entities_without_area']}\n\n"
                          f"Climate entities: {len(diagnostics['climate_entities'])}\n"
                          f"Temperature sensors: {len(diagnostics['temperature_sensors'])}\n"
                          f"Check Home Assistant logs for details."
           }
       )
   else:
       logger.error("Adaptive Climate helper not available")
   ```

3. Restart Home Assistant to enable Python scripting

4. Run the diagnostic by calling the script service:
   - Go to Developer Tools → Services
   - Select `python_script.adaptive_climate_diagnostics`
   - Click "Call Service"

5. Check the notification and logs for detailed information

## Alternative: Use Templates for Diagnostics

Add this card to any dashboard to get entity diagnostics:

```yaml
type: markdown
content: >
  ## Entity Diagnostic Tool

  ### All Areas
  {% for area_id in areas() %}
    **{{ area_name(area_id) }}** ({{ area_entities(area_id) | count }} entities)  
    {% set climate = area_entities(area_id) | select('search', '^climate\.') | list %}
    {% set temp = area_entities(area_id) | selectattr('attributes.unit_of_measurement', 'in', ['°C', '°F']) | map(attribute='entity_id') | list %}
    Climate: {{ climate | count }} | Temperature: {{ temp | count }}
  {% endfor %}

  ### Entities Without Area
  {% set no_area = states | rejectattr('attributes.area_id') | map(attribute='entity_id') | list %}
  {% set climate_no_area = states | selectattr('entity_id', 'search', '^climate\.') | rejectattr('attributes.area_id') | map(attribute='entity_id') | list %}
  {% set temp_no_area = states | selectattr('attributes.unit_of_measurement', 'in', ['°C', '°F']) | rejectattr('attributes.area_id') | map(attribute='entity_id') | list %}
  
  **Entities without area:** {{ no_area | count }}  
  **Climate without area:** {{ climate_no_area | count }}  
  **Temperature sensors without area:** {{ temp_no_area | count }}
```

## Common Fixes

1. **Assign areas to entities:**
   - Go to Settings → Devices & Services → Entities
   - Filter for "climate" or "temperature" 
   - Edit each relevant entity and assign it to an area

2. **Make sure device classes are correct:**
   - Temperature sensors should have device_class "temperature" or unit "°C"/"°F"
   - Climate entities should have domain "climate"

3. **Try without area filtering:**
   - If area filtering is causing problems, try setting up the integration without selecting an area
