# Using Templates with Area Filtering in Adaptive Climate

This guide explains how to use Home Assistant templates for filtering entities by area when working with the Adaptive Climate integration.

## Built-in Home Assistant Methods

Home Assistant provides built-in template functions for working with areas:

### `area_entities(area_name_or_id)`

Returns all entities in the specified area. You can use either the area name or ID:

```yaml
{{ area_entities('Living Room') }}
```

To filter these entities by domain, you can use Jinja's filtering capabilities:

```yaml
{# Get all climate entities in the Living Room #}
{{ area_entities('Living Room') | select('search', '^climate\.') | list }}
```

### Filtering by Domain and Device Class

For more advanced filtering, you can combine multiple filters:

```yaml
{# Get temperature sensors in an area #}
{% set area_entities_list = area_entities('Living Room') | list %}
{% set temp_sensors = area_entities_list | selectattr('entity_id', 'search', '^sensor\.') | select('is_state_attr', 'device_class', 'temperature') | list %}
```

## Adaptive Climate Custom Template Function

The Adaptive Climate integration provides a custom template function for easier filtering:

### `area_domain_entities(area_name_or_id, domains)`

This function directly filters entities by both area and domain in one step:

```yaml
{# Get climate entities in the Living Room #}
{{ area_domain_entities('Living Room', 'climate') }}

{# Get both sensors and binary sensors in the Kitchen #}
{{ area_domain_entities('Kitchen', ['sensor', 'binary_sensor']) }}
```

This makes templates much cleaner and more readable compared to nested filters.

## Examples for Common Use Cases

### Finding Climate Entities in an Area

```yaml
{{ area_domain_entities('Living Room', 'climate') }}
```

### Finding Temperature Sensors in an Area

With the custom function:
```yaml
{{ area_domain_entities('Living Room', 'sensor') | select('is_state_attr', 'device_class', 'temperature') | list }}
```

With built-in functions:
```yaml
{{ area_entities('Living Room') | selectattr('entity_id', 'search', '^sensor\.') | select('is_state_attr', 'device_class', 'temperature') | list }}
```

### Creating an Adaptive Climate Dashboard

```yaml
{% set living_room_climate = area_domain_entities('Living Room', 'climate')[0] %}
{% set living_room_temp = area_domain_entities('Living Room', 'sensor') | select('is_state_attr', 'device_class', 'temperature') | list | first %}

Living Room Climate: {{ living_room_climate }}
Current Temperature: {{ states(living_room_temp) }} °C
```

## Troubleshooting

If your templates are not working as expected:

1. Verify that entities are assigned to the correct area in Home Assistant
2. Check the actual area name (exact spelling matters)
3. Try using the area ID instead of the name
4. Use the Developer Tools > Template editor to test your templates
5. Check Home Assistant logs for any template errors

## Getting Entity Area Information

To find out which area an entity belongs to:

```yaml
{{ state_attr('climate.living_room', 'area_id') }}
{{ area_name(state_attr('climate.living_room', 'area_id')) }}
```
