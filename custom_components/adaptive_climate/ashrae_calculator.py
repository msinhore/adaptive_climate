"""ASHRAE 55 adaptive comfort calculations."""
from __future__ import annotations

import logging
import math
from typing import Any, Dict

_LOGGER = logging.getLogger(__name__)

try:
    from pythermalcomfort.models import adaptive_ashrae
    import pythermalcomfort
    PYTHERMALCOMFORT_AVAILABLE = True
    _LOGGER.info("pythermalcomfort library loaded successfully (version: %s)", 
                 getattr(pythermalcomfort, '__version__', 'unknown'))
except ImportError:
    PYTHERMALCOMFORT_AVAILABLE = False
    _LOGGER.warning("pythermalcomfort library not available. Using fallback calculations.")

from .const import (
    ASHRAE_BASE_TEMP,
    ASHRAE_TEMP_COEFFICIENT,
    MIN_OUTDOOR_TEMP,
    MAX_OUTDOOR_TEMP,
    MAX_STANDARD_OUTDOOR_TEMP,
    AIR_VELOCITY_COOLING_TEMP,
    AIR_VELOCITY_HIGH_THRESHOLD,
    AIR_VELOCITY_MEDIUM_THRESHOLD,
    AIR_VELOCITY_LOW_THRESHOLD,
    AIR_VELOCITY_MIN_THRESHOLD,
    HUMIDITY_HIGH_THRESHOLD,
    HUMIDITY_LOW_THRESHOLD,
    HUMIDITY_CORRECTION_FACTOR_HIGH,
    HUMIDITY_CORRECTION_FACTOR_LOW,
    COMFORT_CATEGORIES,
)


class AdaptiveComfortCalculator:
    """ASHRAE 55 adaptive comfort model calculator."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the calculator with configuration."""
        self.config = config
        self._outdoor_temp = 20.0
        self._indoor_temp = 22.0
        self._indoor_humidity = 50.0
        self._outdoor_humidity = 50.0
        self._mean_radiant_temp = None
        self._occupancy_state = True
        
        from .const import DEFAULT_AIR_VELOCITY
        self._air_velocity = config.get("air_velocity", DEFAULT_AIR_VELOCITY)

    def update_sensors(
        self,
        outdoor_temp: float,
        indoor_temp: float,
        indoor_humidity: float | None = None,
        outdoor_humidity: float | None = None,
        mean_radiant_temp: float | None = None,
        occupancy_state: bool = True,
    ) -> None:
        """Update sensor readings."""
        self._outdoor_temp = outdoor_temp
        self._indoor_temp = indoor_temp
        self._indoor_humidity = indoor_humidity or 50.0
        self._outdoor_humidity = outdoor_humidity or 50.0
        self._mean_radiant_temp = mean_radiant_temp
        self._occupancy_state = occupancy_state

    @property
    def outdoor_temp_valid(self) -> bool:
        """Check if outdoor temperature is within valid range."""
        return MIN_OUTDOOR_TEMP <= self._outdoor_temp <= MAX_OUTDOOR_TEMP

    @property
    def operative_temperature(self) -> float:
        """Calculate operative temperature."""
        if (
            self.config.get("use_operative_temperature", False)
            and self._mean_radiant_temp is not None
        ):
            return (self._indoor_temp + self._mean_radiant_temp) / 2
        return self._indoor_temp

    @property
    def base_adaptive_comfort_temp(self) -> float:
        """Calculate base adaptive comfort temperature using ASHRAE 55 model."""
        if PYTHERMALCOMFORT_AVAILABLE:
            try:
                # Use pythermalcomfort for more accurate calculations
                result = self._calculate_pythermalcomfort_adaptive()
                if result and "adaptive_comfort_temp" in result:
                    return result["adaptive_comfort_temp"]
            except Exception as e:
                _LOGGER.warning("pythermalcomfort calculation failed, using fallback: %s", e)
        
        # Fallback to manual calculation
        return ASHRAE_BASE_TEMP + ASHRAE_TEMP_COEFFICIENT * self._outdoor_temp

    @property
    def air_velocity_offset(self) -> float:
        """Calculate air velocity cooling offset."""
        if self.operative_temperature <= AIR_VELOCITY_COOLING_TEMP:
            return 0.0
        
        if self._air_velocity <= AIR_VELOCITY_MIN_THRESHOLD:
            return 0.0
        
        if self._air_velocity >= AIR_VELOCITY_HIGH_THRESHOLD:
            return -2.2
        elif self._air_velocity >= AIR_VELOCITY_MEDIUM_THRESHOLD:
            return -1.8
        elif self._air_velocity >= AIR_VELOCITY_LOW_THRESHOLD:
            return -1.2
        else:
            # Linear interpolation between 0.3 and 0.6 m/s
            return -1.2 * ((self._air_velocity - AIR_VELOCITY_MIN_THRESHOLD) / (AIR_VELOCITY_LOW_THRESHOLD - AIR_VELOCITY_MIN_THRESHOLD))

    @property
    def humidity_offset(self) -> float:
        """Calculate humidity comfort correction."""
        if not self.config.get("humidity_comfort_enable", True):
            return 0.0
        
        if self._indoor_humidity > HUMIDITY_HIGH_THRESHOLD:
            return HUMIDITY_CORRECTION_FACTOR_HIGH * ((self._indoor_humidity - HUMIDITY_HIGH_THRESHOLD) / 10)
        elif self._indoor_humidity < HUMIDITY_LOW_THRESHOLD:
            return -HUMIDITY_CORRECTION_FACTOR_LOW * ((HUMIDITY_LOW_THRESHOLD - self._indoor_humidity) / 10)
        
        return 0.0

    @property
    def adaptive_comfort_temp(self) -> float:
        """Calculate adaptive comfort temperature with all corrections."""
        if not self.outdoor_temp_valid:
            return 22.0  # Fallback temperature
        
        base_temp = self.base_adaptive_comfort_temp
        
        if self.config.get("comfort_precision_mode", False):
            # Apply all corrections in precision mode
            corrected_temp = base_temp + self.air_velocity_offset + self.humidity_offset
        else:
            # Use base temperature only
            corrected_temp = base_temp
        
        # Apply directional rounding based on outdoor vs indoor temperature
        if self._outdoor_temp > self._indoor_temp:
            return math.floor(corrected_temp)
        elif self._outdoor_temp < self._indoor_temp:
            return math.ceil(corrected_temp)
        else:
            return round(corrected_temp)

    @property
    def comfort_tolerance(self) -> float:
        """Get comfort tolerance based on category."""
        from .const import DEFAULT_COMFORT_CATEGORY
        
        category = self.config.get("comfort_category", DEFAULT_COMFORT_CATEGORY)
        return COMFORT_CATEGORIES[category]["tolerance"]

    @property
    def comfort_temp_min(self) -> float:
        """Calculate minimum comfort temperature."""
        # Try to use pythermalcomfort first
        if PYTHERMALCOMFORT_AVAILABLE:
            try:
                result = self._calculate_pythermalcomfort_adaptive()
                if result and "comfort_temp_min" in result:
                    # Use 80% acceptability range from pythermalcomfort
                    return result["comfort_temp_min"]
            except Exception as e:
                _LOGGER.warning("pythermalcomfort min temp calculation failed, using fallback: %s", e)
        
        # Fallback to manual calculation
        from .const import DEFAULT_COMFORT_TEMP_MIN_OFFSET, DEFAULT_MIN_COMFORT_TEMP
        
        min_offset = self.config.get("comfort_range_min_offset", DEFAULT_COMFORT_TEMP_MIN_OFFSET)
        min_adaptive = self.adaptive_comfort_temp + min_offset  # offset is negative
        min_absolute = self.config.get("min_comfort_temp", DEFAULT_MIN_COMFORT_TEMP)
        return max(min_adaptive, min_absolute)

    @property
    def comfort_temp_max(self) -> float:
        """Calculate maximum comfort temperature."""
        # Try to use pythermalcomfort first
        if PYTHERMALCOMFORT_AVAILABLE:
            try:
                result = self._calculate_pythermalcomfort_adaptive()
                if result and "comfort_temp_max" in result:
                    # Use 80% acceptability range from pythermalcomfort
                    return result["comfort_temp_max"]
            except Exception as e:
                _LOGGER.warning("pythermalcomfort max temp calculation failed, using fallback: %s", e)
        
        # Fallback to manual calculation
        from .const import DEFAULT_COMFORT_TEMP_MAX_OFFSET, DEFAULT_MAX_COMFORT_TEMP
        
        max_offset = self.config.get("comfort_range_max_offset", DEFAULT_COMFORT_TEMP_MAX_OFFSET)
        max_adaptive = self.adaptive_comfort_temp + max_offset  # offset is positive
        max_absolute = self.config.get("max_comfort_temp", DEFAULT_MAX_COMFORT_TEMP)
        return min(max_adaptive, max_absolute)

    @property
    def target_temperature(self) -> float:
        """Calculate target temperature based on current conditions."""
        if not self._occupancy_state and self.config.get("energy_save_mode", True):
            # Unoccupied energy saving mode
            from .const import DEFAULT_SETBACK_TEMPERATURE_OFFSET, DEFAULT_MIN_COMFORT_TEMP
            
            setback_offset = self.config.get("setback_temperature_offset", DEFAULT_SETBACK_TEMPERATURE_OFFSET)
            min_comfort = self.config.get("min_comfort_temp", DEFAULT_MIN_COMFORT_TEMP)
            
            if self._indoor_temp > self.comfort_temp_max:
                return self.comfort_temp_max
            elif self._indoor_temp < self.comfort_temp_min:
                return max(self.comfort_temp_min - setback_offset, min_comfort)
            else:
                return self.adaptive_comfort_temp
        else:
            # Occupied mode
            if self._indoor_temp < self.comfort_temp_min:
                return self.comfort_temp_min
            elif self._indoor_temp > self.comfort_temp_max:
                return self.comfort_temp_max
            else:
                return self.adaptive_comfort_temp

    @property
    def natural_ventilation_available(self) -> bool:
        """Check if natural ventilation is suitable."""
        if not self.config.get("natural_ventilation_enable", True):
            return False
        
        threshold = self.config.get("natural_ventilation_threshold", 2.0)
        
        # Temperature suitability
        temp_suitable = (
            self._outdoor_temp >= (self._indoor_temp - threshold)
            and self._outdoor_temp <= (self._indoor_temp + threshold)
            and self._outdoor_temp >= self.comfort_temp_min
            and self._outdoor_temp <= self.comfort_temp_max
        )
        
        # Humidity suitability (if outdoor humidity sensor available)
        humidity_suitable = True
        if self._outdoor_humidity is not None:
            humidity_suitable = self._outdoor_humidity <= (self._indoor_humidity + 10)
        
        return temp_suitable and humidity_suitable

    @property
    def optimal_fan_speed(self) -> str:
        """Calculate optimal fan speed based on temperature deviation."""
        if not self.config.get("adaptive_air_velocity", True):
            return "auto"
        
        if self._indoor_temp <= self.comfort_temp_max:
            return "auto"
        
        temp_deviation = self._indoor_temp - self.comfort_temp_max
        
        if temp_deviation > 3:
            return "high"
        elif temp_deviation > 1.5:
            return "medium"
        elif temp_deviation > 0.5:
            return "low"
        else:
            return "auto"

    @property
    def hvac_mode_recommendation(self) -> str:
        """Recommend HVAC mode based on current conditions."""
        if self.natural_ventilation_available:
            return "off"
        
        if self._indoor_temp < self.comfort_temp_min:
            return "heat"
        elif self._indoor_temp > self.comfort_temp_max:
            return "cool"
        elif self.comfort_temp_min <= self._indoor_temp <= self.comfort_temp_max:
            # Within comfort zone - check outdoor conditions for optimization
            outdoor_indoor_diff = abs(self._outdoor_temp - self._indoor_temp)
            
            if outdoor_indoor_diff > 3:
                if self._outdoor_temp > self._indoor_temp:
                    return "cool"
                else:
                    return "heat"
            else:
                return "fan_only"  # Use fan only for minor adjustments
        
        return "auto"

    @property
    def compliance_notes(self) -> str:
        """Generate compliance notes for current conditions."""
        notes = []
        
        if self._outdoor_temp < MIN_OUTDOOR_TEMP or self._outdoor_temp > MAX_OUTDOOR_TEMP:
            notes.append(f"Outdoor temp outside valid range ({MIN_OUTDOOR_TEMP}-{MAX_OUTDOOR_TEMP}°C): {self._outdoor_temp}°C")
        elif self._outdoor_temp > MAX_STANDARD_OUTDOOR_TEMP:
            notes.append(f"Outdoor temp above ASHRAE 55 standard range ({MIN_OUTDOOR_TEMP}-{MAX_STANDARD_OUTDOOR_TEMP}°C): {self._outdoor_temp}°C - using extrapolation")
        
        if self.operative_temperature <= AIR_VELOCITY_COOLING_TEMP and self._air_velocity > AIR_VELOCITY_MIN_THRESHOLD:
            notes.append("Air velocity cooling only applies above 25°C operative temp")
        
        return "; ".join(notes) if notes else "Compliant"

    def get_status_summary(self) -> dict[str, Any]:
        """Get comprehensive status summary."""
        # Get pythermalcomfort results if available
        pythermal_result = None
        if PYTHERMALCOMFORT_AVAILABLE:
            pythermal_result = self._calculate_pythermalcomfort_adaptive()
        
        # Calculate effective comfort range considering all offsets
        # Air velocity offset is negative (expands upper range)
        # Humidity offset adjusts the range based on humidity levels
        air_vel_offset = self.air_velocity_offset
        humidity_off = self.humidity_offset
        
        # Air velocity allows higher temperatures (negative offset expands upper range)
        effective_comfort_min = self.comfort_temp_min + humidity_off
        effective_comfort_max = self.comfort_temp_max - air_vel_offset + humidity_off
        
        # Determine compliance based on effective range
        is_compliant = effective_comfort_min <= self._indoor_temp <= effective_comfort_max
        
        # Enhanced compliance using pythermalcomfort if available
        pythermal_compliant_80 = None
        pythermal_compliant_90 = None
        if pythermal_result:
            pythermal_compliant_80 = pythermal_result.get("ashrae_compliant_80")
            pythermal_compliant_90 = pythermal_result.get("ashrae_compliant_90")
        
        status = {
            "outdoor_temp": self._outdoor_temp,
            "indoor_temp": self._indoor_temp,
            "operative_temp": self.operative_temperature,
            "adaptive_comfort_temp": self.adaptive_comfort_temp,
            "comfort_temp_min": self.comfort_temp_min,
            "comfort_temp_max": self.comfort_temp_max,
            "effective_comfort_min": effective_comfort_min,
            "effective_comfort_max": effective_comfort_max,
            "target_temp": self.target_temperature,
            "comfort_tolerance": self.comfort_tolerance,
            "comfort_category": self.config.get("comfort_category", "II"),
            "hvac_mode_recommendation": self.hvac_mode_recommendation,
            "optimal_fan_speed": self.optimal_fan_speed,
            "natural_ventilation_available": self.natural_ventilation_available,
            "occupancy_state": self._occupancy_state,
            "air_velocity_offset": self.air_velocity_offset,
            "humidity_offset": self.humidity_offset,
            "compliance_notes": self.compliance_notes,
            "outdoor_temp_valid": self.outdoor_temp_valid,
            "ashrae_compliant": is_compliant,
            "pythermalcomfort_available": PYTHERMALCOMFORT_AVAILABLE,
        }
        
        # Add pythermalcomfort-specific results if available
        if pythermal_result:
            status.update({
                "pythermalcomfort_compliant_80": pythermal_compliant_80,
                "pythermalcomfort_compliant_90": pythermal_compliant_90,
                "pythermalcomfort_comfort_min_90": pythermal_result.get("comfort_temp_min_90"),
                "pythermalcomfort_comfort_max_90": pythermal_result.get("comfort_temp_max_90"),
            })
        
        return status

    def _calculate_pythermalcomfort_adaptive(self) -> dict[str, Any] | None:
        """Calculate adaptive comfort using pythermalcomfort library.
        
        Returns:
            Dictionary with adaptive comfort calculations or None if error.
        """
        if not PYTHERMALCOMFORT_AVAILABLE:
            return None
            
        try:
            # Use operative temperature (considers radiant temperature)
            tdb = self.operative_temperature
            tr = self._mean_radiant_temp if self._mean_radiant_temp is not None else tdb
            t_running_mean = self._outdoor_temp  # Using current outdoor temp as proxy for running mean
            v = self._air_velocity
            
            _LOGGER.debug(
                "pythermalcomfort inputs: tdb=%.1f, tr=%.1f, t_running_mean=%.1f, v=%.3f",
                tdb, tr, t_running_mean, v
            )
            
            # Call pythermalcomfort adaptive_ashrae
            result = adaptive_ashrae(
                tdb=tdb,
                tr=tr,
                t_running_mean=t_running_mean,
                v=v
            )
            
            # Extract values from result object
            output = {
                "adaptive_comfort_temp": result.tmp_cmf,
                "comfort_temp_min": result.tmp_cmf_80_low,
                "comfort_temp_max": result.tmp_cmf_80_up,
                "comfort_temp_min_90": result.tmp_cmf_90_low,
                "comfort_temp_max_90": result.tmp_cmf_90_up,
                "ashrae_compliant_80": result.acceptability_80,
                "ashrae_compliant_90": result.acceptability_90,
            }
            
            _LOGGER.debug(
                "pythermalcomfort result: tmp_cmf=%.1f, compliant_80=%s, compliant_90=%s",
                output["adaptive_comfort_temp"], 
                output["ashrae_compliant_80"],
                output["ashrae_compliant_90"]
            )
            
            return output
            
        except Exception as e:
            _LOGGER.error("Error in pythermalcomfort calculation: %s", e)
            return None

    def calculate_comfort_parameters(
        self,
        outdoor_temp: float,
        indoor_temp: float,
        indoor_humidity: float | None = None,
        air_velocity: float | None = None,
        mean_radiant_temp: float | None = None,
    ) -> dict[str, Any]:
        """Calculate adaptive comfort parameters based on current conditions."""
        # Update sensor values
        self.update_sensors(
            outdoor_temp=outdoor_temp,
            indoor_temp=indoor_temp,
            indoor_humidity=indoor_humidity,
            mean_radiant_temp=mean_radiant_temp,
        )
        
        # Update air velocity if provided
        if air_velocity is not None:
            self._air_velocity = air_velocity
        
        # Return comprehensive status
        return self.get_status_summary()

    def get_comfort_tolerance(self) -> float:
        """Get comfort tolerance value."""
        return self.comfort_tolerance
    
    def update_config(self, config: dict[str, Any]) -> None:
        """Update configuration."""
        self.config = config
        # Update air velocity if specified in config
        if "air_velocity" in config:
            self._air_velocity = config["air_velocity"]

    def calculate_adaptive_ashrae(
        self,
        tdb: float,
        tr: float,
        t_running_mean: float,
        v: float,
    ) -> Dict[str, Any]:
        """Calculate adaptive comfort temperature using pythermalcomfort library.
        
        This is a wrapper function for pythermalcomfort.models.adaptive_ashrae
        that provides standardized output format for the Adaptive Climate integration.
        
        Args:
            tdb: Indoor dry bulb temperature (°C)
            tr: Mean radiant temperature (°C) 
            t_running_mean: 7-day outdoor running mean temperature (°C)
            v: Air velocity (m/s)
            
        Returns:
            Dictionary with:
            - adaptive_comfort_temp: Adaptive comfort temperature (°C)
            - comfort_temp_min: Lower acceptable temperature for 80% satisfaction (°C)
            - comfort_temp_max: Upper acceptable temperature for 80% satisfaction (°C)
            - comfort_temp_min_90: Lower acceptable temperature for 90% satisfaction (°C)
            - comfort_temp_max_90: Upper acceptable temperature for 90% satisfaction (°C)
            - ashrae_compliant_80: True if conditions are within 80% acceptable range
            - ashrae_compliant_90: True if conditions are within 90% acceptable range
            
        Raises:
            ImportError: If pythermalcomfort library is not available
            ValueError: If input parameters are invalid
        """
        if not PYTHERMALCOMFORT_AVAILABLE:
            raise ImportError(
                "pythermalcomfort library is not available. "
                "Install with: pip install pythermalcomfort>=3.0.0"
            )
        
        _LOGGER.debug(
            "calculate_adaptive_ashrae: tdb=%s, tr=%s, t_running_mean=%s, v=%s",
            tdb, tr, t_running_mean, v
        )
        
        try:
            # Call pythermalcomfort adaptive_ashrae function - API 3.0+
            result = adaptive_ashrae(
                tdb=tdb,
                tr=tr,
                t_running_mean=t_running_mean,
                v=v
            )
            
            # Extract key values from result object
            output = {
                "adaptive_comfort_temp": result.tmp_cmf,
                "comfort_temp_min": result.tmp_cmf_80_low,
                "comfort_temp_max": result.tmp_cmf_80_up,
                "comfort_temp_min_90": result.tmp_cmf_90_low,
                "comfort_temp_max_90": result.tmp_cmf_90_up,
                "ashrae_compliant_80": result.acceptability_80,
                "ashrae_compliant_90": result.acceptability_90,
            }
            
            _LOGGER.debug(
                "calculate_adaptive_ashrae result: adaptive_comfort_temp=%s, compliant_80=%s, compliant_90=%s",
                output["adaptive_comfort_temp"], 
                output["ashrae_compliant_80"], 
                output["ashrae_compliant_90"]
            )
            
            return output
            
        except Exception as err:
            _LOGGER.error(
                "Error in calculate_adaptive_ashrae: tdb=%s, tr=%s, t_running_mean=%s, v=%s, error=%s",
                tdb, tr, t_running_mean, v, err
            )
            raise ValueError(f"Failed to calculate adaptive comfort: {err}") from err
