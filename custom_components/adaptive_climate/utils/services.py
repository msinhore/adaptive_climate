from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant


def check_service_support(hass: HomeAssistant, domain: str, service: str, entity_id: str) -> bool:
    try:
        services = hass.services.services.get(domain, {})
        return service in services
    except Exception:
        return False



