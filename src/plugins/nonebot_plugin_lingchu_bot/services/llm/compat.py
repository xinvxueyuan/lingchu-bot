"""Thin LLM service over LiteLLM with OpenAI SDK fallback."""

# pyright: reportMissingImports=false
# openai and litellm are optional extras ([project.optional-dependencies] ai)

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import ipaddress
import re
from time import monotonic
from typing import TYPE_CHECKING, Any, Literal, cast
from urllib.parse import parse_qsl, unquote, urlsplit

from nonebot import logger

from .backends import LiteLLMBackend, OpenAIBackend
from .capabilities import probe_capability
from .errors import (
    EmptyLLMContentError,
    LLMError,
    LLMProviderError,
    MissingLLMContentError,
)
from .types import LLMProfile

if TYPE_CHECKING:
    from openai.types.chat import (
        ChatCompletionMessageParam,
    )

    from ...core.runtime_config import RuntimeConfig

runtime_config: RuntimeConfig | None = None

ChatMessage = Mapping[str, str]
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


@dataclass(frozen=True, slots=True)
class LLMOptions:
    """Explicit provider settings for one completion call."""

    provider: Literal["litellm", "openai"]
    model: str
    base_url: str | None
    api_key: str | None
    timeout: float


@dataclass(frozen=True, slots=True)
class WebSearchResult:
    """Text and ordered, de-duplicated source URLs from a web search."""

    text: str
    sources: tuple[str, ...]


def _ephemeral_profile(options: LLMOptions, *, model: str | None = None) -> LLMProfile:
    return LLMProfile(
        name="__compat__",
        backend=options.provider,
        model=model or options.model,
        base_url=options.base_url,
        api_key=options.api_key,
        timeout=options.timeout,
    )


def _default_options() -> LLMOptions:
    config = runtime_config
    if config is None:
        from ...core.runtime_config import runtime_config as config

    return LLMOptions(
        provider=config.ai_provider,
        model=config.ai_model,
        base_url=config.ai_base_url,
        api_key=config.ai_api_key,
        timeout=config.ai_timeout,
    )


def supports_web_search(options: LLMOptions) -> bool:
    """Project tri-state web-search support to the legacy boolean contract."""
    if options.provider != "litellm":
        return False
    backend: LiteLLMBackend | None = None
    try:
        profile = _ephemeral_profile(options)
        backend = LiteLLMBackend(profile, _forward_max_retries=False)
        result = probe_capability(
            profile,
            "web_search",
            backend=backend,
        )
    except Exception:  # capability probes must fail closed for compatibility
        logger.warning("LLM web-search capability probe failed: reason=probe_error")
        return False
    finally:
        if backend is not None:
            backend.release()
    return result.support == "supported"


async def _close_backend_cancellation_safe(backend: LiteLLMBackend) -> None:
    """Finish backend cleanup before propagating cancellation."""
    close_task = asyncio.create_task(backend.close())
    cancellation: asyncio.CancelledError | None = None
    while not close_task.done():
        try:
            await asyncio.shield(close_task)
        except asyncio.CancelledError as exc:
            cancellation = exc
    close_task.result()
    if cancellation is not None:
        raise cancellation


def _field(value: object, name: str) -> object | None:
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        return mapping.get(name)
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


def _extract_source_urls_unchecked(response: Any) -> tuple[str, ...]:
    try:
        message = response.choices[0].message
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


def _extract_source_urls(response: Any) -> tuple[str, ...]:
    try:
        return _extract_source_urls_unchecked(response)
    except Exception:  # provider annotations are untrusted
        return ()


async def complete_with_web_search(
    messages: Sequence[ChatMessage],
    *,
    options: LLMOptions | None = None,
) -> WebSearchResult | None:
    """Return a native web-search completion, or ``None`` when unavailable."""
    selected = options or _default_options()
    started = monotonic()
    if not supports_web_search(selected):
        logger.info(
            "LLM web search skipped: reason=unsupported, duration={:.3f}s, sources=0",
            monotonic() - started,
        )
        return None
    backend: LiteLLMBackend | None = None
    try:
        profile = _ephemeral_profile(selected)
        backend = LiteLLMBackend(profile, _forward_max_retries=False)
        response = await backend.call(
            "acompletion",
            messages=list(messages),
            tools=[{"type": "web_search"}],
        )
        text = _extract_content(response)
    except Exception:  # provider failures are soft failures
        logger.warning(
            "LLM web search failed: reason=provider_error, duration={:.3f}s, sources=0",
            monotonic() - started,
        )
        return None
    finally:
        if backend is not None:
            await _close_backend_cancellation_safe(backend)
    sources = _extract_source_urls(response)
    logger.info(
        "LLM web search completed: reason=success, duration={:.3f}s, sources={}",
        monotonic() - started,
        len(sources),
    )
    return WebSearchResult(text=text, sources=sources)


def _extract_content(response: Any) -> str:
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise MissingLLMContentError from exc
    if not content:
        raise EmptyLLMContentError
    return str(content)


async def complete_chat(
    messages: Sequence[ChatMessage],
    *,
    model: str | None = None,
    options: LLMOptions | None = None,
) -> str:
    """Return text from the configured LLM chat provider."""
    selected = options or _default_options()
    selected_model = model or selected.model
    backend: OpenAIBackend | LiteLLMBackend | None = None
    try:
        if selected.provider == "openai":
            backend = OpenAIBackend(_ephemeral_profile(selected, model=selected_model))
            response = await backend.client.chat.completions.create(
                model=selected_model,
                messages=cast("list[ChatCompletionMessageParam]", list(messages)),
            )
        else:
            backend = LiteLLMBackend(
                _ephemeral_profile(selected, model=selected_model),
                _forward_max_retries=False,
            )
            response = await backend.call(
                "acompletion",
                messages=list(messages),
            )
    except LLMError:
        raise
    except Exception as exc:
        raise LLMProviderError from exc
    finally:
        if backend is not None:
            await backend.close()
    return _extract_content(response)
