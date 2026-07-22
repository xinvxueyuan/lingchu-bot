"""Stable parent services exposed to nested subplugins."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import re
from time import monotonic
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import parse_qsl, unquote, urlsplit

from nonebot import logger, require

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_config_file

from ...database.toml_store import ensure_toml_dict_file_sync, load_toml_dict_sync
from ...handle.menu import LocalizedText, MenuAvailability, MenuFeature
from ...handle.qq.commands.common import selected_adapter_handle
from ...handle.qq.commands.triggers import COMMAND_TRIGGERS
from ...i18n import get_configured_locale
from ...platforms import PlatformCapability
from ...services.llm import (
    EmptyLLMContentError,
    LLMError,
    MissingLLMContentError,
)
from ...services.llm.capabilities import probe_capability
from ...services.llm.runtime import LLMRuntime, get_llm_runtime
from ..http_security import download_public_http_bytes

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from nonebot.adapters.onebot.v11 import MessageSegment

MAX_WEB_SEARCH_ANNOTATIONS = 100
MAX_WEB_SEARCH_SOURCES = 64
MAX_SOURCE_URL_LENGTH = 2048
CONTROL_CHARACTER_LIMIT = 32
DELETE_CHARACTER = 127
MAX_SOURCE_QUERY_FIELDS = 64
_SENSITIVE_QUERY_MARKERS = (
    "apikey",
    "auth",
    "authorization",
    "credential",
    "secret",
    "signature",
    "token",
)
_SENSITIVE_QUERY_VALUE = re.compile(
    "".join((
        r"(?i)(?:bearer\s+|sk-[a-z0-9]|api[_-]?key|access[_-]?token|",
        r"authorization|credential|secret|signature|",
        r"x-amz-(?:credential|signature))",
    ))
)


class SubpluginLLMError(LLMError):
    """Contracts-owned LLM error type for nested subplugins."""


@dataclass(frozen=True, slots=True)
class WebSearchResult:
    """Text and ordered, de-duplicated source URLs from a web search."""

    text: str
    sources: tuple[str, ...]


def get_subplugin_llm_runtime() -> LLMRuntime:
    """Return the parent-owned managed runtime to a nested subplugin."""
    return get_llm_runtime()


def _response_text(response_text: str | None) -> str:
    if response_text is None:
        raise MissingLLMContentError
    if not response_text:
        raise EmptyLLMContentError
    return response_text


async def complete_subplugin_chat(
    messages: Sequence[Mapping[str, str]],
    *,
    profile: str | None = None,
) -> str:
    """Complete one child-owned prompt through the parent LLM service."""
    try:
        response = await get_subplugin_llm_runtime().respond(
            list(messages), profile=profile
        )
        return _response_text(response.text)
    except SubpluginLLMError:
        raise
    except LLMError as exc:
        raise SubpluginLLMError(str(exc)) from exc


async def complete_subplugin_chat_default(
    messages: Sequence[Mapping[str, str]],
) -> str:
    """Complete a prompt using the parent's default LLM profile."""
    return await complete_subplugin_chat(messages)


def _field(value: object, name: str) -> object | None:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _is_public_source_host(host: str) -> bool:
    normalized_host = host.casefold()
    try:
        address = ipaddress.ip_address(normalized_host)
    except ValueError:
        return normalized_host not in {
            "localhost",
            "metadata.google.internal",
            "metadata.google.internal.",
        } and not normalized_host.endswith(".localhost")
    return not (address.is_private or address.is_loopback or address.is_link_local)


def _source_query_is_safe(query: str) -> bool:
    try:
        query_fields = parse_qsl(
            query,
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=MAX_SOURCE_QUERY_FIELDS,
        )
    except ValueError:
        return False
    for key, query_value in query_fields:
        normalized_key = "".join(char for char in key.casefold() if char.isalnum())
        if any(marker in normalized_key for marker in _SENSITIVE_QUERY_MARKERS):
            return False
        if _SENSITIVE_QUERY_VALUE.search(unquote(query_value)):
            return False
    return True


def _safe_source_url(value: object) -> str | None:
    if type(value) is not str or not value or len(value) > MAX_SOURCE_URL_LENGTH:
        return None
    if any(
        ord(char) < CONTROL_CHARACTER_LIMIT or ord(char) == DELETE_CHARACTER
        for char in value
    ):
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        return None
    if not _is_public_source_host(parsed.hostname) or not _source_query_is_safe(
        parsed.query
    ):
        return None
    return value


def _extract_source_urls_unchecked(response: object) -> tuple[str, ...]:
    try:
        message = cast("Any", response).choices[0].message
    except (AttributeError, IndexError, TypeError):
        return ()
    annotations = _field(message, "annotations")
    if annotations is None:
        provider_fields = _field(message, "provider_specific_fields")
        annotations = _field(provider_fields, "annotations")
    if type(annotations) not in {list, tuple}:
        return ()
    bounded_annotations = cast("list[object] | tuple[object, ...]", annotations)

    urls: list[str] = []
    seen: set[str] = set()
    for annotation in bounded_annotations[:MAX_WEB_SEARCH_ANNOTATIONS]:
        citation = _field(annotation, "url_citation")
        url = _safe_source_url(_field(citation, "url") or _field(annotation, "url"))
        if url is not None and url not in seen:
            seen.add(url)
            urls.append(url)
            if len(urls) >= MAX_WEB_SEARCH_SOURCES:
                break
    return tuple(urls)


def _extract_source_urls(response: object) -> tuple[str, ...]:
    try:
        return _extract_source_urls_unchecked(response)
    except Exception:  # provider annotations are untrusted
        return ()


async def complete_subplugin_web_search(
    messages: Sequence[Mapping[str, str]],
    *,
    profile: str | None = None,
) -> WebSearchResult | None:
    """Complete a child-owned native web-search prompt through the parent service."""
    started = monotonic()
    runtime = get_subplugin_llm_runtime()
    try:
        selected = runtime.profile(profile)
        if selected.backend != "litellm":
            logger.info(
                "Subplugin LLM web search skipped: reason=unsupported, "
                "duration={:.3f}s, sources=0",
                monotonic() - started,
            )
            return None
        backend = runtime.litellm(selected.name)
        result = probe_capability(selected, "web_search", backend=backend)
        if result.support != "supported":
            logger.info(
                "Subplugin LLM web search skipped: reason=unsupported, "
                "duration={:.3f}s, sources=0",
                monotonic() - started,
            )
            return None
        response = await runtime.respond(
            list(messages), profile=selected.name, tools=[{"type": "web_search"}]
        )
        text = _response_text(response.text)
    except Exception:  # provider failures are soft failures for visual research
        logger.warning(
            "Subplugin LLM web search failed: reason=provider_error, "
            "duration={:.3f}s, sources=0",
            monotonic() - started,
        )
        return None
    sources = _extract_source_urls(response.raw)
    logger.info(
        "Subplugin LLM web search completed: reason=success, duration={:.3f}s, "
        "sources={}",
        monotonic() - started,
        len(sources),
    )
    return WebSearchResult(text=text, sources=sources)


@dataclass(frozen=True, slots=True)
class SubpluginTrigger:
    primary: str
    aliases: frozenset[str]


def get_subplugin_trigger(command_key: str) -> SubpluginTrigger:
    """Return the primary trigger and aliases for a command key."""
    trigger = COMMAND_TRIGGERS[command_key]
    return SubpluginTrigger(primary=trigger.primary, aliases=frozenset(trigger.aliases))


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
]
