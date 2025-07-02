#!/usr/bin/env python3
"""
Simple test script for the ASHRAE calculator to validate the compliance logic.
This script tests the binary sensor logic without needing Home Assistant.
"""

import sys
import os

# Add the project root to the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Mock the Home Assistant dependencies
class MockState:
    def __init__(self, state, attributes=None):
        self.state = state
        self.attributes = attributes or {}

# Mock constants that would come from Home Assistant
STATE_ON = "on"
STATE_OFF = "off"

# Now we can import and test our calculator
from custom_components.adaptive_climate.const import (
    ASHRAE_BASE_TEMP,
    ASHRAE_TEMP_COEFFICIENT,
    MIN_OUTDOOR_TEMP,
    MAX_OUTDOOR_TEMP,
    COMFORT_CATEGORIES,
)

class MockAdaptiveComfortCalculator:
    """Mock version of the calculator for testing"""
    
    def __init__(self, config):
        self.config = config
        self._outdoor_temp = 20.0
        self._indoor_temp = 22.0
        self._indoor_humidity = 50.0
        self._outdoor_humidity = 50.0
        self._mean_radiant_temp = None
        self._occupancy_state = True
        self._air_velocity = config.get("air_velocity", 0.1)

    def update_sensors(self, outdoor_temp, indoor_temp, indoor_humidity=None, **kwargs):
        self._outdoor_temp = outdoor_temp
        self._indoor_temp = indoor_temp
        self._indoor_humidity = indoor_humidity or 50.0

    @property
    def outdoor_temp_valid(self):
        return MIN_OUTDOOR_TEMP <= self._outdoor_temp <= MAX_OUTDOOR_TEMP

    @property
    def operative_temperature(self):
        if (self.config.get("use_operative_temperature", False) 
            and self._mean_radiant_temp is not None):
            return (self._indoor_temp + self._mean_radiant_temp) / 2
        return self._indoor_temp

    @property
    def base_adaptive_comfort_temp(self):
        return ASHRAE_BASE_TEMP + ASHRAE_TEMP_COEFFICIENT * self._outdoor_temp

    @property
    def air_velocity_offset(self):
        # Air velocity cooling allows higher temperatures (negative offset)
        if self._air_velocity > 0.2 and self.operative_temperature > 25.0:
            return -1.2 * self._air_velocity  # Negative = allows higher temps
        return 0.0

    @property
    def humidity_offset(self):
        if not self.config.get("humidity_comfort_enable", True):
            return 0.0
        
        if self._indoor_humidity > 70:
            return 0.5 * ((self._indoor_humidity - 70) / 10)
        elif self._indoor_humidity < 30:
            return -0.5 * ((30 - self._indoor_humidity) / 10)
        return 0.0

    @property
    def adaptive_comfort_temp(self):
        if not self.outdoor_temp_valid:
            return 22.0
        
        base_temp = self.base_adaptive_comfort_temp
        
        if self.config.get("comfort_precision_mode", False):
            corrected_temp = base_temp + self.air_velocity_offset + self.humidity_offset
        else:
            corrected_temp = base_temp
        
        # Simple rounding for test
        return round(corrected_temp, 1)

    @property
    def comfort_tolerance(self):
        category = self.config.get("comfort_category", "II")
        return COMFORT_CATEGORIES[category]["tolerance"]

    @property
    def comfort_temp_min(self):
        min_adaptive = self.adaptive_comfort_temp - self.comfort_tolerance
        min_absolute = self.config.get("min_comfort_temp", 18.0)
        return max(min_adaptive, min_absolute)

    @property
    def comfort_temp_max(self):
        max_adaptive = self.adaptive_comfort_temp + self.comfort_tolerance
        max_absolute = self.config.get("max_comfort_temp", 28.0)
        return min(max_adaptive, max_absolute)

    @property
    def natural_ventilation_available(self):
        if not self.config.get("natural_ventilation_enable", True):
            return False
        
        threshold = self.config.get("natural_ventilation_threshold", 2.0)
        
        temp_suitable = (
            self._outdoor_temp >= (self._indoor_temp - threshold)
            and self._outdoor_temp <= (self._indoor_temp + threshold)
            and self._outdoor_temp >= self.comfort_temp_min
            and self._outdoor_temp <= self.comfort_temp_max
        )
        
        return temp_suitable

    def get_status_summary(self):
        # Calculate effective comfort range considering all offsets
        air_vel_offset = self.air_velocity_offset
        humidity_off = self.humidity_offset
        
        # Air velocity allows higher temperatures (negative offset expands upper range)
        effective_comfort_min = self.comfort_temp_min + humidity_off
        effective_comfort_max = self.comfort_temp_max - air_vel_offset + humidity_off
        
        # Determine compliance based on effective range
        is_compliant = effective_comfort_min <= self._indoor_temp <= effective_comfort_max
        
        return {
            "outdoor_temp": self._outdoor_temp,
            "indoor_temp": self._indoor_temp,
            "adaptive_comfort_temp": self.adaptive_comfort_temp,
            "comfort_temp_min": self.comfort_temp_min,
            "comfort_temp_max": self.comfort_temp_max,
            "effective_comfort_min": effective_comfort_min,
            "effective_comfort_max": effective_comfort_max,
            "air_velocity_offset": air_vel_offset,
            "humidity_offset": humidity_off,
            "ashrae_compliant": is_compliant,
            "natural_ventilation_available": self.natural_ventilation_available,
        }

def test_scenario(name, config, outdoor_temp, indoor_temp, indoor_humidity=50.0):
    print(f"\n=== {name} ===")
    calc = MockAdaptiveComfortCalculator(config)
    calc.update_sensors(outdoor_temp, indoor_temp, indoor_humidity)
    
    status = calc.get_status_summary()
    
    print(f"Outdoor temp: {status['outdoor_temp']}°C")
    print(f"Indoor temp: {status['indoor_temp']}°C")
    print(f"Adaptive comfort temp: {status['adaptive_comfort_temp']}°C")
    print(f"Comfort range: {status['comfort_temp_min']:.1f}-{status['comfort_temp_max']:.1f}°C")
    print(f"Effective range: {status['effective_comfort_min']:.1f}-{status['effective_comfort_max']:.1f}°C")
    print(f"Air velocity offset: {status['air_velocity_offset']:.1f}°C")
    print(f"Humidity offset: {status['humidity_offset']:.1f}°C")
    print(f"ASHRAE Compliant: {status['ashrae_compliant']} ({'ON' if status['ashrae_compliant'] else 'OFF'})")
    print(f"Natural Ventilation: {status['natural_ventilation_available']} ({'ON' if status['natural_ventilation_available'] else 'OFF'})")
    
    return status

def main():
    print("Testing Adaptive Climate Binary Sensor Logic")
    print("=" * 50)
    
    # Default config
    config = {
        "comfort_category": "II",
        "air_velocity": 0.1,
        "use_operative_temperature": False,
        "comfort_precision_mode": False,
        "humidity_comfort_enable": True,
        "natural_ventilation_enable": True,
        "natural_ventilation_threshold": 2.0,
        "min_comfort_temp": 18.0,
        "max_comfort_temp": 28.0,
    }
    
    # Test cases
    print("\\nTesting normal scenarios that should show compliance...")
    
    # Test 1: Should be compliant (indoor temp within comfort range)
    test_scenario("Test 1: Normal compliant case", config, 25.0, 24.0)
    
    # Test 2: Should be compliant with natural ventilation
    test_scenario("Test 2: Natural ventilation suitable", config, 22.0, 22.5)
    
    # Test 3: Should NOT be compliant (too hot)
    test_scenario("Test 3: Too hot - non-compliant", config, 25.0, 27.5)
    
    # Test 4: Should NOT be compliant (too cold)  
    test_scenario("Test 4: Too cold - non-compliant", config, 15.0, 19.0)
    
    print("\\nTesting with air velocity offset...")
    
    # Test 5: High air velocity should expand upper comfort range
    config_with_velocity = config.copy()
    config_with_velocity["air_velocity"] = 0.5
    config_with_velocity["comfort_precision_mode"] = True
    test_scenario("Test 5: High air velocity", config_with_velocity, 25.0, 26.0)
    
    print("\\nTesting with humidity offset...")
    
    # Test 6: High humidity
    test_scenario("Test 6: High humidity", config, 25.0, 24.0, 75.0)
    
    # Test 7: Low humidity
    test_scenario("Test 7: Low humidity", config, 25.0, 24.0, 25.0)

if __name__ == "__main__":
    main()
