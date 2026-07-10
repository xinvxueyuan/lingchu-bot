"""Nested subplugin discovery and parent-child contracts."""

from .contracts import LLMOptions, complete_subplugin_chat
from .loader import discover_subplugin_dirs, load_subplugins

__all__ = [
    "LLMOptions",
    "complete_subplugin_chat",
    "discover_subplugin_dirs",
    "load_subplugins",
]
