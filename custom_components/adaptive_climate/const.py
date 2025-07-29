"""Constants for the Adaptive Climate integration."""
import json
import os

DOMAIN = "adaptive_climate"

# Load version from manifest.json
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "manifest.json")
try:
    with open(MANIFEST_PATH, "r") as manifest_file:
        _MANIFEST = json.load(manifest_file)
        VERSION = _MANIFEST.get("version", "1.3.0")
except (FileNotFoundError, json.JSONDecodeError):
    VERSION = "1.3.0"

# Default configurable parameters (stored in config_entry.options)
DEFAULT_COMFORT_CATEGORY = "I"
DEFAULT_MIN_COMFORT_TEMP = 18.0
DEFAULT_MAX_COMFORT_TEMP = 28.0
DEFAULT_TEMPERATURE_CHANGE_THRESHOLD = 0.5
DEFAULT_OVERRIDE_TEMPERATURE = 0
DEFAULT_AGGRESSIVE_COOLING_THRESHOLD = 2.0
DEFAULT_AGGRESSIVE_HEATING_THRESHOLD = 2.0

# HVAC and Fan Control Options
DEFAULT_ENABLE_FAN_MODE = True
DEFAULT_ENABLE_COOL_MODE = True
DEFAULT_ENABLE_HEAT_MODE = True
DEFAULT_ENABLE_DRY_MODE = True
DEFAULT_MAX_FAN_SPEED = "high"  # Options: low, mid, high, highest
DEFAULT_MIN_FAN_SPEED = "low"

# Available HVAC modes for selection
HVAC_MODE_OPTIONS = {
    "cool": "Cooling",
    "heat": "Heating",
    "fan_only": "Fan Only",
    "dry": "Dry/Dehumidify",
    "off": "Off"
}

# Available fan speed options
FAN_SPEED_OPTIONS = {
    "low": "Low",
    "mid": "Medium",
    "high": "High",
    "highest": "Highest"
}

# Comfort categories (ASHRAE 55)
COMFORT_CATEGORIES = {
    "I": {"tolerance": 2.0, "description": "±2.5°C (90% satisfaction)"},
    "II": {"tolerance": 3.0, "description": "±3.5°C (80% satisfaction)"},
}

# ASHRAE 55 model limits
ASHRAE_BASE_TEMP = 18.9
ASHRAE_TEMP_COEFFICIENT = 0.255
MIN_OUTDOOR_TEMP = 10.0
MAX_OUTDOOR_TEMP = 40.0
MAX_STANDARD_OUTDOOR_TEMP = 33.5

# Logbook events
EVENT_ADAPTIVE_CLIMATE_MODE_CHANGE = f"{DOMAIN}_mode_change"
EVENT_ADAPTIVE_CLIMATE_TARGET_TEMP = f"{DOMAIN}_target_temp"

# Update intervals (minutes)
UPDATE_INTERVAL_SHORT = 0.5  # 30 seconds
UPDATE_INTERVAL_MEDIUM = 1   # 1 minute
UPDATE_INTERVAL_LONG = 5     # 5 minutes