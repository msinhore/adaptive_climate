"""Constants for the Adaptive Climate integration."""
import json
import os
from pathlib import Path

DOMAIN = "adaptive_climate"

# Carregar versão do manifest.json
MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "manifest.json")
try:
    with open(MANIFEST_PATH, "r") as manifest_file:
        _MANIFEST = json.load(manifest_file)
        VERSION = _MANIFEST.get("version", "1.1.0")
except (FileNotFoundError, json.JSONDecodeError):
    VERSION = "1.1.0"

# Default values
DEFAULT_COMFORT_CATEGORY = "II"
DEFAULT_MIN_COMFORT_TEMP = 18.0
DEFAULT_MAX_COMFORT_TEMP = 28.0
DEFAULT_TEMPERATURE_CHANGE_THRESHOLD = 0.5
DEFAULT_AIR_VELOCITY = 0.1
DEFAULT_NATURAL_VENTILATION_THRESHOLD = 2.0
DEFAULT_SETBACK_TEMPERATURE_OFFSET = 2.0
DEFAULT_PROLONGED_ABSENCE_MINUTES = 15
DEFAULT_AUTO_SHUTDOWN_MINUTES = 60
DEFAULT_AUTO_START_MINUTES = 5
DEFAULT_USER_OVERRIDE_MINUTES = 30

# Default comfort range offsets (configurable via number helpers)
DEFAULT_COMFORT_TEMP_MIN_OFFSET = -2.0  # Negative offset from adaptive comfort temp
DEFAULT_COMFORT_TEMP_MAX_OFFSET = 2.0   # Positive offset from adaptive comfort temp

# Comfort categories based on ASHRAE 55
COMFORT_CATEGORIES = {
    "I": {"tolerance": 2.0, "description": "±2°C (90% satisfaction)"},
    "II": {"tolerance": 3.0, "description": "±3°C (80% satisfaction)"},
    "III": {"tolerance": 4.0, "description": "±4°C (65% satisfaction)"},
}

# ASHRAE 55 model parameters
ASHRAE_BASE_TEMP = 18.9
ASHRAE_TEMP_COEFFICIENT = 0.255
MIN_OUTDOOR_TEMP = 10.0
MAX_OUTDOOR_TEMP = 40.0
MAX_STANDARD_OUTDOOR_TEMP = 33.5

# Events for logbook
EVENT_ADAPTIVE_CLIMATE_MODE_CHANGE = f"{DOMAIN}_mode_change"
EVENT_ADAPTIVE_CLIMATE_TARGET_TEMP = f"{DOMAIN}_target_temp"

# Air velocity cooling thresholds
AIR_VELOCITY_COOLING_TEMP = 25.0
AIR_VELOCITY_HIGH_THRESHOLD = 1.2
AIR_VELOCITY_MEDIUM_THRESHOLD = 0.9
AIR_VELOCITY_LOW_THRESHOLD = 0.6
AIR_VELOCITY_MIN_THRESHOLD = 0.3

# Humidity comfort parameters
HUMIDITY_HIGH_THRESHOLD = 60
HUMIDITY_LOW_THRESHOLD = 30
HUMIDITY_CORRECTION_FACTOR_HIGH = 0.3
HUMIDITY_CORRECTION_FACTOR_LOW = 0.2

# Update intervals (minutes)
UPDATE_INTERVAL_SHORT = 0.5  # 30 seconds
UPDATE_INTERVAL_MEDIUM = 1   # 1 minute (was 5)
UPDATE_INTERVAL_LONG = 5     # 5 minutes (was 10)
