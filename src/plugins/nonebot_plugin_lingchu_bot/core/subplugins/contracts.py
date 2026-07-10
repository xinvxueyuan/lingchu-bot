"""Stable parent services exposed to nested subplugins."""

from collections.abc import Mapping, Sequence

from ...handle.qq.commands.common import selected_adapter_handle
from ...i18n import get_configured_locale
from ...services.llm import LLMOptions, complete_chat


async def complete_subplugin_chat(
    messages: Sequence[Mapping[str, str]],
    *,
    options: LLMOptions,
) -> str:
    """Complete one child-owned prompt through the parent LLM service."""
    return await complete_chat(messages, options=options)


__all__ = [
    "LLMOptions",
    "complete_subplugin_chat",
    "get_configured_locale",
    "selected_adapter_handle",
]
