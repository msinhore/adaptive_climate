"""Tests for ASHRAE calculator with pythermalcomfort integration."""
import pytest
from unittest.mock import Mock, patch

from custom_components.adaptive_climate.ashrae_calculator import (
    calculate_adaptive_ashrae,
    PYTHERMALCOMFORT_AVAILABLE
)


class TestAdaptiveASHRAE:
    """Test the calculate_adaptive_ashrae wrapper function."""

    def test_calculate_adaptive_ashrae_with_pythermalcomfort(self):
        """Test calculate_adaptive_ashrae with sample inputs when pythermalcomfort is available."""
        if not PYTHERMALCOMFORT_AVAILABLE:
            pytest.skip("pythermalcomfort library not available")
        
        # Test inputs as specified in prompt
        result = calculate_adaptive_ashrae(
            tdb=25.0,
            tr=25.0,
            t_running_mean=20.0,
            v=0.1,
            standard="ashrae"
        )
        
        # Assert output keys exist as specified
        assert "adaptive_comfort_temp" in result
        assert "ashrae_compliant" in result
        
        # Verify types
        assert isinstance(result["adaptive_comfort_temp"], (int, float))
        assert isinstance(result["ashrae_compliant"], bool)
        
        # Sanity check values
        assert 15.0 <= result["adaptive_comfort_temp"] <= 35.0  # Reasonable temperature range
        
    def test_calculate_adaptive_ashrae_without_pythermalcomfort(self):
        """Test calculate_adaptive_ashrae when pythermalcomfort is not available."""
        with patch('custom_components.adaptive_climate.ashrae_calculator.PYTHERMALCOMFORT_AVAILABLE', False):
            with pytest.raises(ImportError, match="pythermalcomfort library is not available"):
                calculate_adaptive_ashrae(
                    tdb=25.0,
                    tr=25.0,
                    t_running_mean=20.0,
                    v=0.1
                )
    
    def test_calculate_adaptive_ashrae_invalid_inputs(self):
        """Test calculate_adaptive_ashrae with invalid inputs."""
        if not PYTHERMALCOMFORT_AVAILABLE:
            pytest.skip("pythermalcomfort library not available")
        
        # Test with extreme values that should cause errors
        with pytest.raises(ValueError):
            calculate_adaptive_ashrae(
                tdb=100.0,  # Unrealistic indoor temperature
                tr=25.0,
                t_running_mean=20.0,
                v=0.1
            )
    
    def test_calculate_adaptive_ashrae_different_standards(self):
        """Test calculate_adaptive_ashrae with different standards."""
        if not PYTHERMALCOMFORT_AVAILABLE:
            pytest.skip("pythermalcomfort library not available")
        
        # Test with EN standard
        result_en = calculate_adaptive_ashrae(
            tdb=25.0,
            tr=25.0,
            t_running_mean=20.0,
            v=0.1,
            standard="en"
        )
        
        # Should have same keys
        assert "adaptive_comfort_temp" in result_en
        assert "ashrae_compliant" in result_en
        
        # Test with ASHRAE standard (default)
        result_ashrae = calculate_adaptive_ashrae(
            tdb=25.0,
            tr=25.0,
            t_running_mean=20.0,
            v=0.1,
            standard="ashrae"
        )
        
        # Results might differ between standards
        assert "adaptive_comfort_temp" in result_ashrae
        assert "ashrae_compliant" in result_ashrae
    
    def test_calculate_adaptive_ashrae_edge_cases(self):
        """Test calculate_adaptive_ashrae with edge case inputs."""
        if not PYTHERMALCOMFORT_AVAILABLE:
            pytest.skip("pythermalcomfort library not available")
        
        # Test with minimum air velocity
        result_min_v = calculate_adaptive_ashrae(
            tdb=22.0,
            tr=22.0,
            t_running_mean=15.0,
            v=0.0  # Minimum air velocity
        )
        
        assert "adaptive_comfort_temp" in result_min_v
        assert "ashrae_compliant" in result_min_v
        
        # Test with higher air velocity
        result_high_v = calculate_adaptive_ashrae(
            tdb=22.0,
            tr=22.0,
            t_running_mean=15.0,
            v=1.5  # Higher air velocity
        )
        
        assert "adaptive_comfort_temp" in result_high_v
        assert "ashrae_compliant" in result_high_v
