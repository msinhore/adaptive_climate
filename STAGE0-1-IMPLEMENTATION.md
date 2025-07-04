# Stage 0-1: pythermalcomfort Integration

## Implementation Summary

This stage integrates the `pythermalcomfort` library into the Adaptive Climate project as a dependency and creates a wrapper function for ASHRAE 55 adaptive comfort calculations.

### Changes Made

#### 1. Updated Dependencies (manifest.json)
- Added `pythermalcomfort==2.8.0` to requirements
- Ensures scientific accuracy for thermal comfort calculations

#### 2. Created Wrapper Function (ashrae_calculator.py)
- Added `calculate_adaptive_ashrae()` function
- Uses `pythermalcomfort.models.adaptive_ashrae` internally
- Provides standardized output format:
  ```python
  {
    "adaptive_comfort_temp": result["tmp_cmf"],
    "ashrae_compliant": result["acceptability"]
  }
  ```

#### 3. Fallback Handling
- Graceful handling when pythermalcomfort is not available
- Clear error messages and logging
- Maintains compatibility with existing code

#### 4. Unit Tests (tests/test_ashrae_calculator.py)
- Tests core functionality with sample inputs (tdb=25.0, tr=25.0, t_running_mean=20.0, v=0.1)
- Tests fallback behavior when library is unavailable
- Tests edge cases and different standards (ASHRAE vs EN)
- Validates output structure and types

### Function Signature

```python
def calculate_adaptive_ashrae(
    tdb: float,          # Indoor dry bulb temperature (°C)
    tr: float,           # Mean radiant temperature (°C) 
    t_running_mean: float, # 7-day outdoor running mean temperature (°C)
    v: float,            # Air velocity (m/s)
    standard: str = "ashrae"  # Standard to use ("ashrae" or "en")
) -> Dict[str, Any]:
```

### Output Format

```python
{
    "adaptive_comfort_temp": float,  # Adaptive comfort temperature (°C)
    "ashrae_compliant": bool         # True if conditions are acceptable
}
```

### Testing

The implementation includes comprehensive tests:
- ✅ Basic functionality with specified sample inputs
- ✅ Error handling when library unavailable
- ✅ Edge cases (min/max air velocity)
- ✅ Different standards (ASHRAE vs EN)
- ✅ Input validation

### Next Steps (Stage 2)

In the next stage, we will:
1. Replace existing internal calculator logic in coordinator.py
2. Integrate the new wrapper function into the main calculation flow
3. Leverage additional pythermalcomfort features (PMV/PPD, cooling effects)
4. Expand bridge entities with new parameters

### Compatibility

- ✅ Maintains backward compatibility with existing ashrae_calculator.py class structure
- ✅ Does not modify coordinator.py (as requested)
- ✅ Graceful fallback when pythermalcomfort unavailable
- ✅ Clear error messages and logging

### Dependencies

- `pythermalcomfort==2.8.0` - Scientific thermal comfort calculations
- Existing Home Assistant core dependencies unchanged
