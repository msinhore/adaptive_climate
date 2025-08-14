from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import logging

from homeassistant.core import HomeAssistant

from custom_components.adaptive_climate.const import DOMAIN

_LOGGER = logging.getLogger(__name__)
from custom_components.adaptive_climate.utils.device import ClimateInfo, choose_roles_for_area
from custom_components.adaptive_climate.utils.services import check_service_support


def get_area_id(hass: HomeAssistant, climate_entity_id: str) -> Optional[str]:
    try:
        ent_reg = hass.helpers.entity_registry.async_get(hass)
    except Exception:
        from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

        ent_reg = async_get_entity_registry(hass)
    entry = ent_reg.async_get(climate_entity_id) if ent_reg else None
    return entry.area_id if entry else None


def collect_area_devices(hass: HomeAssistant, climate_entity_id: str) -> List[ClimateInfo]:
    area_id = get_area_id(hass, climate_entity_id)
    if not area_id:
        return []

    devices: List[ClimateInfo] = []
    coordinators = hass.data.get(DOMAIN, {}).get("coordinators", {})
    for _key, other in coordinators.items():
        try:
            other_climate_entity_id = getattr(other, "climate_entity_id", None)
            if not other_climate_entity_id or other_climate_entity_id == climate_entity_id:
                continue
            other_area = get_area_id(hass, other_climate_entity_id)
            if other_area != area_id:
                continue
            state = hass.states.get(other_climate_entity_id)
            if not state:
                continue
            hvac_modes = list(state.attributes.get("hvac_modes", []))
            fan_modes = list(state.attributes.get("fan_modes", []))
            info = ClimateInfo(
                entity_id=other_climate_entity_id,
                area_id=other_area,
                hvac_modes=hvac_modes,
                fan_modes=fan_modes,
                supports_set_temperature=check_service_support(hass, "climate", "set_temperature", other_climate_entity_id),
                supports_set_hvac_mode=check_service_support(hass, "climate", "set_hvac_mode", other_climate_entity_id),
            )
            devices.append(info)
        except Exception:
            continue

    # Include self device as candidate too
    own_state = hass.states.get(climate_entity_id)
    if own_state:
        devices.append(
            ClimateInfo(
                entity_id=climate_entity_id,
                area_id=area_id,
                hvac_modes=list(own_state.attributes.get("hvac_modes", [])),
                fan_modes=list(own_state.attributes.get("fan_modes", [])),
                supports_set_temperature=check_service_support(hass, "climate", "set_temperature", climate_entity_id),
                supports_set_hvac_mode=check_service_support(hass, "climate", "set_hvac_mode", climate_entity_id),
            )
        )
    return devices


def collect_area_fans(hass: HomeAssistant, climate_entity_id: str) -> List[str]:
    area_id = get_area_id(hass, climate_entity_id)
    if not area_id:
        return []
    try:
        ent_reg = hass.helpers.entity_registry.async_get(hass)
    except Exception:
        from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

        ent_reg = async_get_entity_registry(hass)

    fan_entities: List[str] = []
    if not ent_reg:
        return fan_entities
    for entity in list(ent_reg.entities.values()):
        if entity.domain != "fan":
            continue
        if entity.area_id == area_id:
            fan_entities.append(entity.entity_id)
            continue
        if entity.device_id:
            try:
                dev_reg = hass.helpers.device_registry.async_get(hass)
            except Exception:
                from homeassistant.helpers.device_registry import async_get as async_get_device_registry

                dev_reg = async_get_device_registry(hass)
            device = dev_reg.async_get(entity.device_id) if dev_reg else None
            if device and device.area_id == area_id:
                fan_entities.append(entity.entity_id)
    return fan_entities


def area_orchestration_gate(
    hass: HomeAssistant, climate_entity_id: str, comfort_params: Dict[str, Any]
) -> Tuple[bool, Optional[str], Optional[str], str]:
    devices = collect_area_devices(hass, climate_entity_id)
    if not devices:
        # No peers found in area; act as primary by default
        return True, climate_entity_id, None, "solo"

    season_str: str = comfort_params.get("season") or "summer"
    if season_str in ("spring", "autumn"):
        season: str = "shoulder"
    elif season_str == "winter":
        season = "winter"
    else:
        season = "summer"

    indoor_temp = comfort_params.get("indoor_temperature")
    comfort_min = comfort_params.get("comfort_min_ashrae")
    comfort_max = comfort_params.get("comfort_max_ashrae")
    indoor_humidity = comfort_params.get("indoor_humidity")

    primary_id, secondary_id, side = choose_roles_for_area(
        devices,
        season=season,  # type: ignore[arg-type]
        indoor_temp=indoor_temp,
        comfort_min=comfort_min,
        comfort_max=comfort_max,
        indoor_humidity=indoor_humidity,
    )

    # Log the roles chosen for visibility
    try:
        _LOGGER.debug(
            "[Area Orchestration] Devices=%s | primary=%s | secondary=%s | side=%s",
            [d.entity_id for d in devices],
            primary_id,
            secondary_id,
            side,
        )
    except Exception:
        pass

    if not primary_id:
        # No clear primary; allow everyone to act conservatively
        return True, None, None, side

    # Act only if we are primary
    return (primary_id == climate_entity_id), primary_id, secondary_id, side


