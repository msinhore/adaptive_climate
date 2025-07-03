"""Command-line diagnostic tool for Adaptive Climate area-entity assignments."""
import sys
import json
import logging
from pathlib import Path

# Add custom_components directory to path so we can import our component
sys.path.append(str(Path(__file__).parent))

from custom_components.adaptive_climate.area_helper import AreaBasedConfigHelper

# Configure logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

def dump_diagnostics(hass):
    """Dump diagnostics for entity-area assignments."""
    _LOGGER.info("Running Adaptive Climate entity-area diagnostics")
    
    helper = AreaBasedConfigHelper(hass)
    
    # Get detailed entity registry info
    registry_info = helper.dump_entity_registry_assignments()
    
    _LOGGER.info("Entity Registry Summary:")
    _LOGGER.info(f"Total entities: {registry_info['entity_count']}")
    _LOGGER.info(f"Entities with area: {registry_info['entities_with_area']}")
    _LOGGER.info(f"Entities without area: {registry_info['entities_without_area']}")
    
    _LOGGER.info("Domain Statistics:")
    for domain, count in registry_info['domain_stats'].items():
        _LOGGER.info(f"  {domain}: {count} entities")
    
    _LOGGER.info("Areas without entities:")
    for area in registry_info['areas_without_entities']:
        _LOGGER.info(f"  {area}")
    
    _LOGGER.info("Domains without areas:")
    for domain, count in registry_info['domains_without_areas'].items():
        _LOGGER.info(f"  {domain}: {count} entities")
    
    _LOGGER.info("Climate entities:")
    for entity in registry_info['climate_entities']:
        _LOGGER.info(f"  {entity['entity_id']} - Area: {entity['area_name']}")
    
    _LOGGER.info("Temperature sensors:")
    for entity in registry_info['temperature_sensors']:
        _LOGGER.info(f"  {entity['entity_id']} - Area: {entity['area_name']} - Unit: {entity['unit']} - Device class: {entity['device_class']}")
    
    # Test area-based filtering for each area
    _LOGGER.info("Testing area-based entity filtering:")
    for area_id in helper._area_registry.areas:
        area = helper._area_registry.async_get_area(area_id)
        _LOGGER.info(f"Area: {area.name} (ID: {area_id})")
        
        entities_by_type = helper.get_entities_by_type_in_area(area_id)
        _LOGGER.info(f"  Climate entities: {entities_by_type['climate']}")
        _LOGGER.info(f"  Temperature sensors: {entities_by_type['temperature_sensors']}")
        _LOGGER.info(f"  Humidity sensors: {entities_by_type['humidity_sensors']}")
    
    # Output detailed diagnostics to file
    with open("adaptive_climate_diagnostics.json", "w") as f:
        json.dump(registry_info, f, indent=2)
    
    _LOGGER.info("Detailed diagnostics written to adaptive_climate_diagnostics.json")

# Note: This script should be run from within Home Assistant using the Python scripting integration
# If you are using this standalone, you need to provide a valid Home Assistant instance
if __name__ == "__main__":
    _LOGGER.info("This script should be run from within Home Assistant using the Python scripting integration")
    _LOGGER.info("If you're seeing this message, please add this script to your Home Assistant scripts")
