# Example Templates for Adaptive Climate

This document provides examples of how to use Home Assistant templates to filter entities by area, which can be useful when working with the Adaptive Climate integration.

## Filtering Entities by Area

Home Assistant provides built-in template functions for filtering entities by area. Here are some examples:

### Get all entities in an area

```yaml
{{ area_entities('Living Room') }}
```

### Get climate entities in an area

```yaml
{% set climate_entities = area_entities('Living Room') | select('search', '^climate\.') | list %}
{{ climate_entities }}
```

### Get temperature sensors in an area

```yaml
{% set temp_sensors = area_entities('Living Room') | selectattr('entity_id', 'search', '^sensor\..*temp') | list %}
{{ temp_sensors }}
```

### Get occupancy sensors in an area

```yaml
{% set occupancy_sensors = area_entities('Living Room') | selectattr('entity_id', 'search', '^binary_sensor\..*occupancy|.*motion|.*presence') | list %}
{{ occupancy_sensors }}
```

## Complete Example for Adaptive Climate

This example shows how to find all climate entities and associated sensors in a specific area:

```yaml
{% set area_name = 'Living Room' %}
{% set area_entities_list = area_entities(area_name) | list %}

{% set climate_entities = area_entities_list | select('search', '^climate\.') | list %}
{% set temp_sensors = area_entities_list | selectattr('entity_id', 'search', '^sensor\..*temp') | list %}
{% set occupancy_sensors = area_entities_list | selectattr('entity_id', 'search', '^binary_sensor\..*occupancy|.*motion|.*presence') | list %}
{% set humidity_sensors = area_entities_list | selectattr('entity_id', 'search', '^sensor\..*humid') | list %}

Climate entities: {{ climate_entities }}
Temperature sensors: {{ temp_sensors }}
Occupancy sensors: {{ occupancy_sensors }}
Humidity sensors: {{ humidity_sensors }}
```

## Filtering by Entity Domain

If you need to filter by domain more explicitly, you can use:

```yaml
{% set area_name = 'Living Room' %}
{% set area_entities_list = area_entities(area_name) | list %}

{% set climate_entities = area_entities_list | select('search', '^climate\.') | list %}
{% set sensor_entities = area_entities_list | select('search', '^sensor\.') | list %}
{% set binary_sensor_entities = area_entities_list | select('search', '^binary_sensor\.') | list %}

Climate entities: {{ climate_entities }}
Sensor entities: {{ sensor_entities }}
Binary sensor entities: {{ binary_sensor_entities }}
```

## Alternative Method Using selectattr

This example uses `selectattr` with `is_state_attr` to filter entities by area and device class:

```yaml
{% set area_name = 'Living Room' %}
{% set area_entities_list = area_entities(area_name) | list %}

{# Get temperature sensors by device class #}
{% set temp_sensors = area_entities_list | selectattr('entity_id', 'search', '^sensor\.') | select('is_state_attr', 'device_class', 'temperature') | list %}

{# Get humidity sensors by device class #}
{% set humidity_sensors = area_entities_list | selectattr('entity_id', 'search', '^sensor\.') | select('is_state_attr', 'device_class', 'humidity') | list %}

{# Get occupancy sensors by device class #}
{% set occupancy_sensors = area_entities_list | selectattr('entity_id', 'search', '^binary_sensor\.') | select('is_state_attr', 'device_class', 'occupancy') | list %} 

Temperature sensors: {{ temp_sensors }}
Humidity sensors: {{ humidity_sensors }}
Occupancy sensors: {{ occupancy_sensors }}
```
