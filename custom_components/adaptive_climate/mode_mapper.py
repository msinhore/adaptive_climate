FAN_MODE_EQUIVALENTS = {
    "off": ["off"],
    "auto": ["auto", "Auto"],
    "quiet": ["quiet", "Quiet", "silent", "Silence", "night"],
    "lowest": ["lowest", "min", "minimum", "level1", "ultralow"],
    "low": ["low", "Low", "level1", "1"],
    "mediumlow": ["mediumlow", "medium low", "level2", "2"],
    "mid": ["mid", "Mid", "medium", "Medium", "med", "middle", "level3", "3"],
    "mediumhigh": ["mediumhigh", "medium high", "level4", "4"],
    "high": ["high", "High", "level5", "5"],
    "highest": ["highest", "max", "maximum", "top", "superhigh", "powerful", "turbo", "Turbo", "strong", "Strong"],
}

HVAC_MODE_EQUIVALENTS = {
    "auto": ["auto", "heat_cool", "Heat/Cool", "heatcool"],
    "cool": ["cool", "Cool"],
    "heat": ["heat", "Heat"],
    "dry": ["dry", "Dry", "dehumidify"],
    "humidify": ["humidify", "Humidify", "humidification"], 
    "fan_only": ["fan_only", "fan", "Fan only", "Fan", "fanonly"],
    "off": ["off", "Off"],
}

def map_mode(calculated, supported, equivalents):
    calculated = calculated.lower()
    supported_lower = [m.lower() for m in supported]
    # 1. Direct match
    if calculated in supported_lower:
        return supported[supported_lower.index(calculated)]
    # 2. Equivalent match
    for key, aliases in equivalents.items():
        if calculated == key or calculated in aliases:
            for alias in aliases:
                if alias.lower() in supported_lower:
                    return supported[supported_lower.index(alias.lower())]
    # 3. Partial match
    for mode in supported:
        if calculated in mode.lower() or mode.lower() in calculated:
            return mode
    # 4. Fallback
    return supported[0] if supported else calculated

def map_fan_mode(calculated_fan, supported_fan_modes):
    return map_mode(calculated_fan, supported_fan_modes, FAN_MODE_EQUIVALENTS)

def map_hvac_mode(calculated_hvac, supported_hvac_modes):
    return map_mode(calculated_hvac, supported_hvac_modes, HVAC_MODE_EQUIVALENTS)