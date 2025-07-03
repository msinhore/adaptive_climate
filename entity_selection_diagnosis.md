# Entity Selection Diagnosis

This file contains a template to help diagnose why entities aren't appearing in the selectors.

## Template to Test Area Entity Assignment

Copy this template to a Markdown card in your Home Assistant dashboard:

```yaml
type: markdown
content: >
  ## Area Entity Diagnostic Tool

  {% set all_areas = areas() %}

  ### All Areas with Entity Counts
  
  {% for area_id in all_areas %}
    - **{{ area_name(area_id) }}**: {{ area_entities(area_id) | count }} entities
  {% endfor %}


  ### Entities Without Area Assignment

  {% set entities_without_area = states | selectattr('entity_id', 'search', '^(climate|sensor|binary_sensor)\.') | rejectattr('attributes.area_id') | map(attribute='entity_id') | list %}

  {% if entities_without_area | count > 0 %}
    **The following entities have no area assigned:**
    
    {% for entity_id in entities_without_area %}
      - {{ entity_id }}
    {% endfor %}
  {% else %}
    All relevant entities have areas assigned!
  {% endif %}


  ### Specific Area Entity Check
  
  {% set area_to_check = 'Living Room' %}  <!-- Change to the area you're trying to use -->
  
  **Checking area: {{ area_to_check }}**
  
  {% set area_diagnostic = check_area_entities(area_to_check) %}
  
  {{ area_diagnostic }}


  ### Domain Entity Check
  
  {% set area_to_check = 'Living Room' %}  <!-- Change to the area you're trying to use -->
  
  **Climate entities in {{ area_to_check }}:**
  
  {% set climate_entities = area_domain_entities(area_to_check, 'climate') %}
  {% if climate_entities | count > 0 %}
    {% for entity_id in climate_entities %}
      - {{ entity_id }}
    {% endfor %}
  {% else %}
    No climate entities found in this area!
  {% endif %}

  **Temperature sensor entities in {{ area_to_check }}:**
  
  {% set sensor_entities = area_domain_entities(area_to_check, 'sensor') | select('is_state_attr', 'device_class', 'temperature') | list %}
  {% if sensor_entities | count > 0 %}
    {% for entity_id in sensor_entities %}
      - {{ entity_id }}
    {% endfor %}
  {% else %}
    No temperature sensor entities found in this area!
  {% endif %}
```

## Debugging Steps

1. Make sure all your entities are assigned to areas. You can do this in the Home Assistant UI:
   - Go to Settings → Devices & Services → Entities
   - For each entity you want to use, click Edit and assign it to an area

2. Check if Home Assistant recognizes your area assignments:
   - Use the template above to see what entities are assigned to which areas
   - Verify that climate entities, temperature sensors, etc. appear in the expected areas

3. If entities are properly assigned but still not showing up in selectors:
   - Try clearing your browser cache
   - Restart Home Assistant
   - Check the Home Assistant logs for any errors

4. Test the area helper directly:
   - You can add the following debug code to your `config_flow.py` in the `async_step_user` method:
   ```python
   area_helper = AreaBasedConfigHelper(self.hass)
   for area_id in self.hass.helpers.area_registry.async_get(self.hass).areas:
       entities = area_helper.get_entities_by_type_in_area(area_id)
       _LOGGER.warning("Area %s contains: %s", 
                     self.hass.helpers.area_registry.async_get(self.hass).async_get_area(area_id).name, 
                     entities)
   ```

5. If all else fails, try this workaround:
   - In `config_flow.py`, modify the selectors to use include_entities with an empty list but add device_class filters
   - Example:
   ```python
   vol.Required("indoor_temp_sensor"): selector.EntitySelector(
       selector.EntitySelectorConfig(
           domain=["sensor", "input_number", "weather"],
           device_class=["temperature"],
           include_entities=[]
       )
   ),
   ```
