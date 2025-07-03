# Quick Diagnostic Template for Entity Selection Issues

Copy and paste this template into Home Assistant Developer Tools → Template to check entity assignments and potential issues:

```yaml
{% set your_area = "Living Room" %}  {# Change this to your area name #}

## Area Entity Diagnostic Results

**Testing area: {{ your_area }}**

### Areas and their entities:
{% for area_id in areas() %}
  - {{ area_name(area_id) }}: {{ area_entities(area_id) | count }} entities
{% endfor %}

### Climate entities in your area:
{% set climate_entities = area_entities(area_id) | select('search', '^climate\.') | list %}
{% if climate_entities %}
  {% for entity in climate_entities %}
    - {{ entity }}
  {% endfor %}
{% else %}
  No climate entities found in this area
{% endif %}

### Temperature sensors in your area:
{% set temp_sensors = states | selectattr('attributes.device_class', 'eq', 'temperature') | 
                     selectattr('attributes.area_id', 'eq', area_id) | map(attribute='entity_id') | list %}
{% if temp_sensors %}
  {% for entity in temp_sensors %}
    - {{ entity }}
  {% endfor %}
{% else %}
  No temperature sensors with device_class 'temperature' found in this area
{% endif %}

### Temperature sensors by unit in your area:
{% set temp_by_unit = states | selectattr('attributes.unit_of_measurement', 'in', ['°C', '°F']) | 
                     selectattr('attributes.area_id', 'eq', area_id) | map(attribute='entity_id') | list %}
{% if temp_by_unit %}
  {% for entity in temp_by_unit %}
    - {{ entity }}
  {% endfor %}
{% else %}
  No sensors with temperature units found in this area
{% endif %}

### All entities in your area:
{% for entity in area_entities(area_id) %}
  - {{ entity }}
{% endfor %}
```

## If you have the Adaptive Climate template helpers loaded:

```yaml
{% set your_area = "Living Room" %}  {# Change this to your area name #}

{{ check_area_entities(your_area) }}

Climate entities: {{ area_domain_entities(your_area, 'climate') }}

Temperature sensors: {{ area_domain_entities(your_area, ['sensor']) | select('is_state_attr', 'device_class', 'temperature') | list }}
```
