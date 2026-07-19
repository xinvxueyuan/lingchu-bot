"""Typed runtime mutation for declared handle default values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from .runtime_config import get_handle_config_manager

MUTE_DURATION_MIN: Final = 1
MUTE_DURATION_MAX: Final = 30 * 24 * 60 * 60
RECALL_COUNT_MAX: Final = 100

if TYPE_CHECKING:
    from collections.abc import Callable


class HandleDefaultValueError(ValueError):
    """Raised when a chat value cannot safely update a handle default."""


@dataclass(frozen=True, slots=True)
class HandleDefaultDefinition:
    """One explicitly mutable handle default field."""

    command_key: str
    field: str
    parse: Callable[[str], Any]


def _parse_positive_duration(value: str) -> int:
    try:
        duration = int(value)
    except ValueError as error:
        msg = "duration must be an integer"
        raise HandleDefaultValueError(msg) from error
    if not MUTE_DURATION_MIN <= duration <= MUTE_DURATION_MAX:
        msg = f"duration must be between {MUTE_DURATION_MIN} and {MUTE_DURATION_MAX}"
        raise HandleDefaultValueError(msg)
    return duration


def _parse_optional_duration(value: str) -> int | None:
    if value.casefold() in {"permanent", "永久"}:
        return None
    return _parse_positive_duration(value)


def _parse_positive_count(value: str) -> int:
    try:
        count = int(value)
    except ValueError as error:
        msg = "count must be an integer"
        raise HandleDefaultValueError(msg) from error
    if not 1 <= count <= RECALL_COUNT_MAX:
        msg = f"count must be between 1 and {RECALL_COUNT_MAX}"
        raise HandleDefaultValueError(msg)
    return count


def _parse_scope(value: str) -> str:
    normalized = value.casefold()
    aliases = {"group": "group", "global": "global", "本群": "group", "全局": "global"}
    if normalized not in aliases:
        msg = "scope must be group or global"
        raise HandleDefaultValueError(msg)
    return aliases[normalized]


def _parse_bool(value: str) -> bool:
    normalized = value.casefold()
    aliases = {"true": True, "false": False, "是": True, "否": False}
    if normalized not in aliases:
        msg = "value must be true or false"
        raise HandleDefaultValueError(msg)
    return aliases[normalized]


def _parse_text(value: str) -> str:
    text = value.strip()
    if not text:
        msg = "text must not be empty"
        raise HandleDefaultValueError(msg)
    return text


HANDLE_DEFAULT_DEFINITIONS: Final[tuple[HandleDefaultDefinition, ...]] = (
    HandleDefaultDefinition("member_mute", "mute_duration", _parse_positive_duration),
    HandleDefaultDefinition("member_mute", "default_reason", _parse_text),
    HandleDefaultDefinition("remote_mute", "mute_duration", _parse_positive_duration),
    HandleDefaultDefinition("remote_mute", "default_reason", _parse_text),
    HandleDefaultDefinition("block_member", "block_duration", _parse_optional_duration),
    HandleDefaultDefinition("block_member", "default_reason", _parse_text),
    HandleDefaultDefinition("remote_block", "block_duration", _parse_optional_duration),
    HandleDefaultDefinition("remote_block", "default_reason", _parse_text),
    HandleDefaultDefinition("recall_message", "default_count", _parse_positive_count),
    HandleDefaultDefinition("protect_member", "whitelist_scope", _parse_scope),
    HandleDefaultDefinition("protect_member", "default_reason", _parse_text),
    HandleDefaultDefinition("kick_member", "require_reason", _parse_bool),
    HandleDefaultDefinition(
        "restart_protocol_endpoint", "default_platform", _parse_text
    ),
)

_DEFINITION_BY_KEY: Final = {
    (definition.command_key, definition.field): definition
    for definition in HANDLE_DEFAULT_DEFINITIONS
}


def supported_handle_defaults() -> tuple[HandleDefaultDefinition, ...]:
    """Return all safe runtime-mutable default fields."""
    return HANDLE_DEFAULT_DEFINITIONS


async def update_handle_default(
    command_key: str,
    field: str,
    raw_value: str,
    *,
    config_manager: Any | None = None,
) -> Any:
    """Parse, validate, persist, and return one configured default value."""
    definition = _DEFINITION_BY_KEY.get((command_key, field))
    if definition is None:
        msg = f"unsupported handle default: {command_key}.{field}"
        raise HandleDefaultValueError(msg)
    value = definition.parse(raw_value)
    manager = config_manager or get_handle_config_manager()
    await manager.update_config(command_key, {"defaults": {field: value}})
    return value
