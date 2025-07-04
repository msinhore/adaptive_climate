"""Test the bridge entity functionality."""
import pytest
from unittest.mock import Mock, AsyncMock
from custom_components.adaptive_climate.bridge_entity import (
    NumberBridgeEntity,
    SwitchBridgeEntity,
    SelectBridgeEntity,
    SensorBridgeEntity,
    create_bridge_entities,
    BRIDGE_ENTITY_CONFIG,
)


def test_bridge_entity_config():
    """Test that bridge entity config is properly structured."""
    assert "number" in BRIDGE_ENTITY_CONFIG
    assert "switch" in BRIDGE_ENTITY_CONFIG
    assert "select" in BRIDGE_ENTITY_CONFIG
    assert "sensor" in BRIDGE_ENTITY_CONFIG
    
    # Check number entities
    number_config = BRIDGE_ENTITY_CONFIG["number"]
    assert "outdoor_temp" in number_config
    assert "indoor_temp" in number_config
    assert "air_velocity" in number_config
    assert "metabolic_rate" in number_config
    assert "clothing_insulation" in number_config
    
    # Check switch entities
    switch_config = BRIDGE_ENTITY_CONFIG["switch"]
    assert "auto_update" in switch_config
    assert "use_feels_like" in switch_config
    
    # Check select entities
    select_config = BRIDGE_ENTITY_CONFIG["select"]
    assert "comfort_class" in select_config
    assert select_config["comfort_class"]["options"] == ["class_1", "class_2", "class_3"]
    
    # Check sensor entities
    sensor_config = BRIDGE_ENTITY_CONFIG["sensor"]
    assert "comfort_temperature" in sensor_config
    assert "comfort_range_min" in sensor_config
    assert "comfort_range_max" in sensor_config


def test_create_bridge_entities():
    """Test bridge entity creation."""
    hass = Mock()
    config_entry = Mock()
    config_entry.entry_id = "test_entry"
    config_entry.data = {"name": "Test Climate"}
    
    # Test number entities
    number_entities = create_bridge_entities(hass, config_entry, "number")
    assert len(number_entities) == 5  # outdoor_temp, indoor_temp, air_velocity, metabolic_rate, clothing_insulation
    assert all(isinstance(entity, NumberBridgeEntity) for entity in number_entities)
    
    # Test switch entities
    switch_entities = create_bridge_entities(hass, config_entry, "switch")
    assert len(switch_entities) == 2  # auto_update, use_feels_like
    assert all(isinstance(entity, SwitchBridgeEntity) for entity in switch_entities)
    
    # Test select entities
    select_entities = create_bridge_entities(hass, config_entry, "select")
    assert len(select_entities) == 1  # comfort_class
    assert all(isinstance(entity, SelectBridgeEntity) for entity in select_entities)
    
    # Test sensor entities
    sensor_entities = create_bridge_entities(hass, config_entry, "sensor")
    assert len(sensor_entities) == 3  # comfort_temperature, comfort_range_min, comfort_range_max
    assert all(isinstance(entity, SensorBridgeEntity) for entity in sensor_entities)
    
    # Test invalid platform
    invalid_entities = create_bridge_entities(hass, config_entry, "invalid")
    assert len(invalid_entities) == 0


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.states = Mock()
    hass.bus = Mock()
    hass.bus.async_listen = Mock()
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    config_entry = Mock()
    config_entry.entry_id = "test_entry"
    config_entry.data = {"name": "Test Climate"}
    return config_entry


@pytest.fixture
def mock_binary_sensor_state():
    """Create a mock binary sensor state."""
    state = Mock()
    state.state = "on"
    state.attributes = {
        "outdoor_temp": 25.0,
        "indoor_temp": 22.0,
        "air_velocity": 0.1,
        "metabolic_rate": 1.2,
        "clothing_insulation": 0.5,
        "auto_update": True,
        "use_feels_like": False,
        "comfort_class": "class_1",
        "comfort_temperature": 24.0,
        "comfort_range_min": 20.0,
        "comfort_range_max": 28.0,
    }
    return state


def test_number_bridge_entity(mock_hass, mock_config_entry, mock_binary_sensor_state):
    """Test NumberBridgeEntity functionality."""
    mock_hass.states.get.return_value = mock_binary_sensor_state
    
    entity_config = BRIDGE_ENTITY_CONFIG["number"]["outdoor_temp"]
    entity = NumberBridgeEntity(mock_hass, mock_config_entry, "outdoor_temp", entity_config)
    
    # Test properties
    assert entity.unique_id == "test_entry_outdoor_temp_bridge"
    assert entity.name == "Outdoor Temperature"
    assert entity.native_min_value == -30.0
    assert entity.native_max_value == 50.0
    assert entity.native_step == 0.1
    assert entity.native_unit_of_measurement == "°C"
    assert entity.icon == "mdi:thermometer"
    
    # Test value retrieval
    assert entity.native_value == 25.0


def test_switch_bridge_entity(mock_hass, mock_config_entry, mock_binary_sensor_state):
    """Test SwitchBridgeEntity functionality."""
    mock_hass.states.get.return_value = mock_binary_sensor_state
    
    entity_config = BRIDGE_ENTITY_CONFIG["switch"]["auto_update"]
    entity = SwitchBridgeEntity(mock_hass, mock_config_entry, "auto_update", entity_config)
    
    # Test properties
    assert entity.unique_id == "test_entry_auto_update_bridge"
    assert entity.name == "Auto Update"
    assert entity.icon == "mdi:update"
    
    # Test value retrieval
    assert entity.is_on is True


def test_select_bridge_entity(mock_hass, mock_config_entry, mock_binary_sensor_state):
    """Test SelectBridgeEntity functionality."""
    mock_hass.states.get.return_value = mock_binary_sensor_state
    
    entity_config = BRIDGE_ENTITY_CONFIG["select"]["comfort_class"]
    entity = SelectBridgeEntity(mock_hass, mock_config_entry, "comfort_class", entity_config)
    
    # Test properties
    assert entity.unique_id == "test_entry_comfort_class_bridge"
    assert entity.name == "Comfort Class"
    assert entity.options == ["class_1", "class_2", "class_3"]
    assert entity.icon == "mdi:comfort"
    
    # Test value retrieval
    assert entity.current_option == "class_1"


def test_sensor_bridge_entity(mock_hass, mock_config_entry, mock_binary_sensor_state):
    """Test SensorBridgeEntity functionality."""
    mock_hass.states.get.return_value = mock_binary_sensor_state
    
    entity_config = BRIDGE_ENTITY_CONFIG["sensor"]["comfort_temperature"]
    entity = SensorBridgeEntity(mock_hass, mock_config_entry, "comfort_temperature", entity_config)
    
    # Test properties
    assert entity.unique_id == "test_entry_comfort_temperature_bridge"
    assert entity.name == "Comfort Temperature"
    assert entity.native_unit_of_measurement == "°C"
    assert entity.device_class == "temperature"
    assert entity.icon == "mdi:thermometer-check"
    
    # Test value retrieval
    assert entity.native_value == 24.0


if __name__ == "__main__":
    pytest.main([__file__])
