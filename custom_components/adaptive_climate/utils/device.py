from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple, Literal


DeviceClass = Literal["heat_only", "cool_only", "dual", "fan_dry_only", "unknown"]
Season = Literal["winter", "summer", "shoulder"]
Side = Literal["heat", "cool", "fan", "dry"]


@dataclass(frozen=True)
class ClimateInfo:
    entity_id: str
    area_id: Optional[str]
    hvac_modes: List[str]
    fan_modes: List[str]
    supports_set_temperature: bool = True
    supports_set_hvac_mode: bool = True


def classify_device(hvac_modes: List[str], fan_modes: List[str]) -> DeviceClass:
    modes = set((hvac_modes or []))
    has_heat = "heat" in modes
    has_cool = "cool" in modes
    has_fan = "fan_only" in modes
    has_dry = "dry" in modes

    if has_heat and not has_cool:
        return "heat_only"
    if has_cool and not has_heat:
        return "cool_only"
    if has_heat and has_cool:
        return "dual"
    if has_fan or has_dry:
        return "fan_dry_only"
    return "unknown"


def pick_season_side(
    season: Season,
    indoor_temp: Optional[float],
    comfort_min: Optional[float],
    comfort_max: Optional[float],
) -> Side:
    if season == "winter":
        return "heat"
    if season == "summer":
        return "cool"
    if indoor_temp is None or comfort_min is None or comfort_max is None:
        return "fan"
    if indoor_temp > comfort_max:
        return "cool"
    if indoor_temp < comfort_min:
        return "heat"
    return "fan"


def _has_mode(dev: ClimateInfo, mode: str) -> bool:
    return mode in set(dev.hvac_modes or [])


def _capability_rank(dev: ClimateInfo) -> int:
    rank = 0
    if not dev.supports_set_temperature:
        rank += 1
    if not dev.supports_set_hvac_mode:
        rank += 1
    return rank


def _rank_for_side(dev: ClimateInfo, side: Side) -> Tuple[int, int]:
    cls = classify_device(dev.hvac_modes, dev.fan_modes)
    if side == "heat":
        class_key = 0 if cls == "heat_only" else (1 if cls == "dual" else 9)
    elif side == "cool":
        class_key = 0 if cls == "cool_only" else (1 if cls == "dual" else 9)
    elif side == "dry":
        class_key = 0 if _has_mode(dev, "dry") else 9
    else:
        class_key = 0 if _has_mode(dev, "fan_only") else 9
    caps_key = _capability_rank(dev)
    return (class_key, caps_key)


def choose_roles_for_area(
    devices: List[ClimateInfo],
    season: Season,
    indoor_temp: Optional[float],
    comfort_min: Optional[float],
    comfort_max: Optional[float],
    indoor_humidity: Optional[float] = None,
    humidity_high_threshold: float = 60.0,
) -> Tuple[Optional[str], Optional[str], Side]:
    if not devices:
        return None, None, "fan"

    if season == "winter":
        side: Side = "heat"
        ranked = sorted(
            ((dev, *_rank_for_side(dev, side)) for dev in devices),
            key=lambda x: (x[1], x[2], dev_key(x[0])),
        )
    elif season == "summer":
        if indoor_temp is None or comfort_min is None or comfort_max is None:
            side = "cool"
        elif indoor_temp > comfort_max:
            side = "cool"
        else:
            side = "dry" if (indoor_humidity is not None and indoor_humidity >= humidity_high_threshold) else "fan"

        ranked = sorted(
            ((dev, *_rank_for_side(dev, side)) for dev in devices),
            key=lambda x: (x[1], x[2], dev_key(x[0])),
        )
    else:
        base_side = pick_season_side(season, indoor_temp, comfort_min, comfort_max)
        if base_side == "fan" and indoor_humidity is not None and indoor_humidity >= humidity_high_threshold:
            side = "dry"
        else:
            side = base_side

        ranked = sorted(
            ((dev, *_rank_for_side(dev, side)) for dev in devices),
            key=lambda x: (x[1], x[2], dev_key(x[0])),
        )

    primary = ranked[0][0].entity_id if ranked and ranked[0][1] != 9 else None

    secondary: Optional[str] = None
    for item in ranked[1:]:
        class_key = item[1]
        if class_key != 9:
            secondary = item[0].entity_id
            break

    return primary, secondary, side


def dev_key(dev: ClimateInfo) -> str:
    return dev.entity_id


__all__ = [
    "ClimateInfo",
    "DeviceClass",
    "Season",
    "Side",
    "classify_device",
    "pick_season_side",
    "choose_roles_for_area",
]



