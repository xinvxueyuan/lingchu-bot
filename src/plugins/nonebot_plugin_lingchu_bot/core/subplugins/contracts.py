"""Stable parent services exposed to nested subplugins."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from nonebot import require

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_config_file

from ...database.toml_store import ensure_toml_dict_file_sync, load_toml_dict_sync
from ...handle.menu import LocalizedText, MenuAvailability, MenuFeature
from ...handle.qq.commands.common import selected_adapter_handle
from ...handle.qq.commands.triggers import COMMAND_TRIGGERS
from ...i18n import get_configured_locale
from ...platforms import PlatformCapability
from ...services.llm import (
    LLMError,
    LLMOptions,
    WebSearchResult,
    complete_chat,
    complete_with_web_search,
    supports_web_search,
)
from ...services.llm.runtime import LLMRuntime, get_llm_runtime
from ..config import plugin_config
from ..http_security import download_public_http_bytes

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from nonebot.adapters.onebot.v11 import MessageSegment


class SubpluginLLMError(LLMError):
    """Contracts-owned LLM error type for nested subplugins."""


def get_subplugin_llm_runtime() -> LLMRuntime:
    """Return the parent-owned managed runtime to a nested subplugin."""
    return get_llm_runtime()


async def complete_subplugin_chat(
    messages: Sequence[Mapping[str, str]],
    *,
    options: LLMOptions,
) -> str:
    """Complete one child-owned prompt through the parent LLM service."""
    try:
        return await complete_chat(messages, options=options)
    except SubpluginLLMError:
        raise
    except LLMError as exc:
        raise SubpluginLLMError(str(exc)) from exc


async def complete_subplugin_chat_default(
    messages: Sequence[Mapping[str, str]],
) -> str:
    """Complete a prompt using the parent's default LLM options."""
    try:
        result = await complete_chat(messages)
    except SubpluginLLMError:
        raise
    except LLMError as exc:
        raise SubpluginLLMError(str(exc)) from exc
    return result


def subplugin_supports_web_search(options: LLMOptions) -> bool:
    """Return whether the selected parent LLM supports native web search."""
    return supports_web_search(options)


async def complete_subplugin_web_search(
    messages: Sequence[Mapping[str, str]],
    *,
    options: LLMOptions,
) -> WebSearchResult | None:
    """Complete a child-owned native web-search prompt through the parent service."""
    return await complete_with_web_search(messages, options=options)


@dataclass(frozen=True, slots=True)
class SubpluginTrigger:
    primary: str
    aliases: frozenset[str]


def get_subplugin_trigger(command_key: str) -> SubpluginTrigger:
    """Return the primary trigger and aliases for a command key."""
    trigger = COMMAND_TRIGGERS[command_key]
    return SubpluginTrigger(primary=trigger.primary, aliases=frozenset(trigger.aliases))


def resolve_default_llm_options() -> LLMOptions:
    """Return the parent's default LLM options from runtime_config."""
    return LLMOptions(
        provider=plugin_config.ai_provider,
        model=plugin_config.ai_model,
        base_url=plugin_config.ai_base_url,
        api_key=plugin_config.ai_api_key,
        timeout=plugin_config.ai_timeout,
    )


def ensure_subplugin_config_file(
    filename: str,
    defaults: dict[str, Any],
    *,
    schema_basename: str | None = None,
) -> None:
    """Ensure a subplugin TOML config file exists in the localstore config directory."""
    ensure_toml_dict_file_sync(
        get_plugin_config_file(filename),
        defaults,
        schema_basename=schema_basename,
    )


def load_subplugin_config(filename: str) -> dict[str, Any]:
    """Load a subplugin TOML config file from the localstore config directory."""
    return load_toml_dict_sync(get_plugin_config_file(filename))


def image_message(image_bytes: bytes) -> MessageSegment:
    """Create an adapter-specific image message from raw bytes."""
    from nonebot.adapters.onebot.v11 import MessageSegment

    return MessageSegment.image(image_bytes)


def register_subplugin_handler(
    matcher: Any,
    command_key: str,
    adapter_id: str,
    *,
    bypass_gate: bool = False,
    bypass_silent: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register through the shared adapter, permission, and state gates."""
    return selected_adapter_handle(
        matcher,
        adapter_id,
        command_key,
        bypass_gate=bypass_gate,
        bypass_silent=bypass_silent,
    )


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
    "LocalizedText",
    "MenuAvailability",
    "MenuFeature",
    "PlatformCapability",
    "SubpluginLLMError",
    "SubpluginTrigger",
    "WebSearchResult",
    "collect_subplugin_menu_features",
    "complete_subplugin_chat",
    "complete_subplugin_chat_default",
    "complete_subplugin_web_search",
    "download_public_http_bytes",
    "ensure_subplugin_config_file",
    "get_configured_locale",
    "get_subplugin_llm_runtime",
    "get_subplugin_trigger",
    "image_message",
    "load_subplugin_config",
    "register_subplugin_handler",
    "register_subplugin_menu_feature",
    "reset_subplugin_menu_features",
    "resolve_default_llm_options",
    "subplugin_supports_web_search",
]
