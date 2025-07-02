"""Test configuration for Adaptive Climate."""
import pytest
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.setup import async_setup_component

from custom_components.adaptive_climate.const import DOMAIN
from custom_components.adaptive_climate.ashrae_calculator import AdaptiveComfortCalculator


@pytest.fixture
def hass():
    """Home Assistant test instance."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {}
    hass.states = Mock()
    hass.states.async_entity_ids = Mock(return_value=[])
    hass.config_entries = Mock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.services = Mock()
    hass.services.async_register = Mock()
    return hass


@pytest.fixture 
def mock_config_entry():
    """Mock config entry."""
    return {
        "name": "Test Adaptive Climate",
        "climate_entity": "climate.test_ac",
        "indoor_temp_sensor": "sensor.indoor_temp",
        "outdoor_temp_sensor": "sensor.outdoor_temp",
        "comfort_category": "II",
        "energy_save_mode": True,
        "natural_ventilation_enable": True,
        "adaptive_air_velocity": True,
        "min_comfort_temp": 18.0,
        "max_comfort_temp": 28.0,
        "temperature_change_threshold": 1.0,
        "air_velocity": 0.1,
    }


class TestAdaptiveClimate:
    """Test Adaptive Climate component."""
    
    async def test_setup(self, hass, mock_config_entry):
        """Test component setup."""
        with patch("custom_components.adaptive_climate.async_setup_entry"):
            assert await async_setup_component(hass, DOMAIN, {})


class TestAdaptiveComfortCalculator:
    """Test ASHRAE 55 calculations."""
    
    def test_base_adaptive_comfort_temp(self):
        """Test base adaptive comfort temperature calculation."""
        from custom_components.adaptive_climate.ashrae_calculator import AdaptiveComfortCalculator
        
        config = {"comfort_category": "II"}
        calc = AdaptiveComfortCalculator(config)
        calc.update_sensors(outdoor_temp=20.0, indoor_temp=22.0)
        
        # 18.9 + 0.255 * 20 = 24.0
        assert calc.base_adaptive_comfort_temp == 24.0
    
    def test_comfort_tolerance(self):
        """Test comfort tolerance for different categories."""
        from custom_components.adaptive_climate.ashrae_calculator import AdaptiveComfortCalculator
        
        # Category I: ±2°C
        calc_i = AdaptiveComfortCalculator({"comfort_category": "I"})
        assert calc_i.comfort_tolerance == 2.0
        
        # Category II: ±3°C  
        calc_ii = AdaptiveComfortCalculator({"comfort_category": "II"})
        assert calc_ii.comfort_tolerance == 3.0
        
        # Category III: ±4°C
        calc_iii = AdaptiveComfortCalculator({"comfort_category": "III"})
        assert calc_iii.comfort_tolerance == 4.0
    
    def test_outdoor_temp_valid_range(self):
        """Test outdoor temperature validation."""
        from custom_components.adaptive_climate.ashrae_calculator import AdaptiveComfortCalculator
        
        calc = AdaptiveComfortCalculator({"comfort_category": "II"})
        
        # Valid range: 10-40°C
        calc.update_sensors(outdoor_temp=25.0, indoor_temp=22.0)
        assert calc.outdoor_temp_valid
        
        # Below valid range
        calc.update_sensors(outdoor_temp=5.0, indoor_temp=22.0)
        assert not calc.outdoor_temp_valid
        
        # Above valid range
        calc.update_sensors(outdoor_temp=45.0, indoor_temp=22.0)
        assert not calc.outdoor_temp_valid
    
    def test_natural_ventilation_detection(self):
        """Test natural ventilation suitability."""
        from custom_components.adaptive_climate.ashrae_calculator import AdaptiveComfortCalculator
        
        config = {
            "comfort_category": "II",
            "natural_ventilation_enable": True,
            "natural_ventilation_threshold": 2.0,
        }
        calc = AdaptiveComfortCalculator(config)
        
        # Indoor: 22°C, threshold: ±2°C, so outdoor 20-24°C should be suitable
        calc.update_sensors(outdoor_temp=21.0, indoor_temp=22.0)
        
        # Assuming comfort zone includes 21°C
        calc.update_sensors(outdoor_temp=21.0, indoor_temp=22.0)
        # This would need more complex setup to test properly
    
    def test_air_velocity_offset(self):
        """Test air velocity cooling offset."""
        from custom_components.adaptive_climate.ashrae_calculator import AdaptiveComfortCalculator
        
        config = {"comfort_category": "II", "air_velocity": 0.5}
        calc = AdaptiveComfortCalculator(config)
        
        # Below 25°C operative temp - no cooling benefit
        calc.update_sensors(outdoor_temp=20.0, indoor_temp=20.0)
        assert calc.air_velocity_offset == 0.0
        
        # Above 25°C with air velocity > 0.3 m/s
        calc.update_sensors(outdoor_temp=30.0, indoor_temp=26.0)
        assert calc.air_velocity_offset < 0.0  # Should provide cooling


if __name__ == "__main__":
    pytest.main([__file__])
