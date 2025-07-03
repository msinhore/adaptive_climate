# Template Helpers and Logbook Integration

## Template Helpers

The Adaptive Climate integration provides several template helpers to make it easier to work with data:

### Safe State Helpers

These helpers handle situations where entities might not exist or be unavailable:

```yaml
# Example: Getting state safely from an entity that might not exist
{% set light_state = safe_state(states.light.nonexistent_light) %}

# Example: Filtering a list of entities that might contain None values
{% set valid_lights = safe_states([ 
    states.light.light1, 
    states.light.nonexistent, 
    states.light.light2 
]) %}
```

### Safe Name Helper

This helper safely gets the name of an entity or dictionary, handling ReadOnlyDict objects:

```yaml
{{ safe_name(this) }}
```

This is especially useful when working with the `this` variable in template sensors.

### Area Domain Helpers

These helpers allow you to get entities by area and domain:

```yaml
# Get all climate entities in the Living Room
{{ area_domain_entities('Living Room', 'climate') }}

# Get all sensors and binary sensors in the Kitchen
{{ area_domain_entities('Kitchen', ['sensor', 'binary_sensor']) }}
```

## Logbook Integration

The Adaptive Climate component now properly integrates with the Home Assistant logbook. The following events are logged:

1. HVAC Mode Changes: When the component changes the HVAC mode of a climate entity.
2. Temperature Changes: When the component changes the target temperature of a climate entity.

These events will appear in the Home Assistant logbook with proper descriptions.

## Troubleshooting Templates

If you see template warnings related to missing entities, try replacing direct state access with the safe helpers:

**Instead of this:**
```yaml
{% set lights = [states.light.living_room, states.light.kitchen] %}
{% set lights_on = lights | selectattr('state', 'eq', 'on') | list %}
```

**Use this:**
```yaml
{% set lights = safe_states([states.light.living_room, states.light.kitchen]) %}
{% set lights_on = lights | selectattr('state', 'eq', 'on') | list %}
```

## Troubleshooting Logbook Events

If logbook events are not showing up:

1. Make sure the `logbook` integration is enabled in your Home Assistant configuration
2. Check that the component is properly firing events when changes occur
3. Verify that your climate entity is properly configured in the integration
