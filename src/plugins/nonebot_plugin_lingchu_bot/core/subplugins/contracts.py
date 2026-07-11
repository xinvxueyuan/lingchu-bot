"""Stable parent services exposed to nested subplugins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ...handle.qq.commands.common import selected_adapter_handle
from ...i18n import get_configured_locale
from ...services.llm import LLMOptions, complete_chat

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from ...handle.menu import MenuFeature


async def complete_subplugin_chat(
    messages: Sequence[Mapping[str, str]],
    *,
    options: LLMOptions,
) -> str:
    """Complete one child-owned prompt through the parent LLM service."""
    return await complete_chat(messages, options=options)


_subplugin_menu_features: list[Any] = []


def register_subplugin_menu_feature(feature: MenuFeature) -> None:
    """Register a MenuFeature exposed by a nested subplugin."""
    _subplugin_menu_features.append(feature)


def collect_subplugin_menu_features() -> tuple[Any, ...]:
    """Return all subplugin-registered MenuFeature entries as a tuple."""
    return tuple(_subplugin_menu_features)


def reset_subplugin_menu_features() -> None:
    """Clear the subplugin menu feature registry (for test isolation)."""
    _subplugin_menu_features.clear()


__all__ = [
    "LLMOptions",
    "collect_subplugin_menu_features",
    "complete_subplugin_chat",
    "get_configured_locale",
    "register_subplugin_menu_feature",
    "reset_subplugin_menu_features",
    "selected_adapter_handle",
]
