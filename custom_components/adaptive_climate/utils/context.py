from __future__ import annotations

from typing import Any, Dict, Optional

from homeassistant.core import Context
from homeassistant.util import dt as dt_util


def create_command_context(device_name: str) -> Context:
    parent_id = f"adaptive_climate_{device_name}_{int(dt_util.utcnow().timestamp())}"
    return Context(parent_id=parent_id)


def is_system_event_context(
    last_system_command: Dict[str, Any], context: Optional[Context]
) -> bool:
    try:
        if not context or not last_system_command:
            return False
        event_ctx_id = str(context.id)
        last_ctx_id = str(last_system_command.get("context_id"))
        last_parent_id = str(last_system_command.get("parent_id"))
        return bool(event_ctx_id) and (
            event_ctx_id == last_ctx_id or event_ctx_id == last_parent_id
        )
    except Exception:
        return False


