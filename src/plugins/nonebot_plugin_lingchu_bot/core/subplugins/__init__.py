"""Nested subplugin discovery and parent-child contracts."""

from .contracts import (
    LLMOptions,
    collect_subplugin_menu_features,
    complete_subplugin_chat,
    register_subplugin_menu_feature,
    reset_subplugin_menu_features,
)
from .loader import discover_subplugin_dirs, load_subplugins

__all__ = [
    "LLMOptions",
    "collect_subplugin_menu_features",
    "complete_subplugin_chat",
    "discover_subplugin_dirs",
    "load_subplugins",
    "register_subplugin_menu_feature",
    "reset_subplugin_menu_features",
]
