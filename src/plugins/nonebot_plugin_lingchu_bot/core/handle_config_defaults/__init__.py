"""Standard-library defaults for handle-level configuration."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

HandleDefaultsFactory = Callable[[], dict[str, Any]]


def _config(defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "enabled": True,
        "defaults": deepcopy(defaults or {}),
        "policies": {},
    }


HANDLE_DEFAULTS_REGISTRY: dict[str, HandleDefaultsFactory] = {
    "kick_member": lambda: _config({
        "require_reason": False,
        "default_reason": "管理员操作",
        "audit_level": "low",
    }),
    "protect_member": lambda: _config({
        "whitelist_scope": "group",
        "default_reason": "管理员操作",
    }),
    "block_member": lambda: _config({
        "block_duration": None,
        "default_reason": "违反群规",
    }),
    "member_mute": lambda: _config({
        "mute_duration": 300,
        "default_reason": "管理员操作",
    }),
    "recall_message": lambda: _config({"default_count": 10}),
    "remote_mute": lambda: _config({
        "mute_duration": 60,
        "default_reason": "管理员操作",
    }),
    "remote_kick": _config,
    "remote_block": lambda: _config({
        "block_duration": None,
        "default_reason": "违反群规",
    }),
    "remote_announcement": _config,
    "mass_announcement": _config,
    "restart_protocol_endpoint": lambda: _config({"default_platform": "当前平台"}),
    "send_announcement": _config,
    "set_member_card": _config,
    "set_member_title": _config,
    "set_member_admin": _config,
    "set_group_name": _config,
    "set_group_avatar": _config,
}


def register_handle_defaults(command_key: str, factory: HandleDefaultsFactory) -> None:
    """Register a standard-library default factory."""
    if command_key in HANDLE_DEFAULTS_REGISTRY:
        raise ValueError(f"duplicate key: {command_key}")
    HANDLE_DEFAULTS_REGISTRY[command_key] = factory


__all__ = ["HANDLE_DEFAULTS_REGISTRY", "register_handle_defaults"]
