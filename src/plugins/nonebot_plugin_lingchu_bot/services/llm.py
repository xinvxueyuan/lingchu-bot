"""Thin LLM service over LiteLLM with OpenAI SDK fallback."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from time import monotonic
from typing import TYPE_CHECKING, Any, Literal, cast

from nonebot import logger

from ..core.runtime_config import runtime_config

if TYPE_CHECKING:
    from openai.types.chat import (  # pyright: ignore[reportMissingImports]  # ty: ignore[unresolved-import]
        ChatCompletionMessageParam,
    )

ChatMessage = Mapping[str, str]


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


class LLMError(RuntimeError):
    """LLM provider call failed or returned no text."""


class MissingLLMContentError(LLMError):
    """LLM response did not contain message content."""

    def __init__(self) -> None:
        super().__init__("LLM response did not contain message content")


class EmptyLLMContentError(LLMError):
    """LLM response content was empty."""

    def __init__(self) -> None:
        super().__init__("LLM response content was empty")


class LLMProviderError(LLMError):
    """LLM provider call failed."""

    def __init__(self) -> None:
        super().__init__("LLM provider call failed")


async def _call_litellm(
    *,
    model: str,
    messages: Sequence[ChatMessage],
    api_base: str | None,
    api_key: str | None,
    request_timeout: float,
) -> Any:
    from litellm import (  # pyright: ignore[reportMissingImports]  # ty: ignore[unresolved-import]
        acompletion,
    )

    return await acompletion(
        model=model,
        messages=list(messages),
        api_base=api_base,
        api_key=api_key,
        timeout=request_timeout,
    )


def _litellm_supports_web_search(model: str) -> bool:
    from litellm import (  # pyright: ignore[reportMissingImports]  # ty: ignore[unresolved-import]
        supports_web_search as probe,
    )

    return bool(probe(model=model))


def supports_web_search(options: LLMOptions) -> bool:
    """Return whether the selected LiteLLM model supports native web search."""
    if options.provider != "litellm":
        return False
    try:
        return _litellm_supports_web_search(options.model)
    except Exception:  # noqa: BLE001 - capability probes must fail closed
        logger.warning(
            "LLM web-search capability probe failed: model={}, reason=probe_error",
            options.model,
        )
        return False


async def _call_litellm_web_search(
    *,
    model: str,
    messages: Sequence[ChatMessage],
    api_base: str | None,
    api_key: str | None,
    request_timeout: float,
) -> Any:
    from litellm import (  # pyright: ignore[reportMissingImports]  # ty: ignore[unresolved-import]
        acompletion,
    )

    return await acompletion(
        model=model,
        messages=list(messages),
        api_base=api_base,
        api_key=api_key,
        timeout=request_timeout,
        tools=[{"type": "web_search"}],
    )


def _field(value: object, name: str) -> object | None:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _extract_source_urls_unchecked(response: Any) -> tuple[str, ...]:
    try:
        message = response.choices[0].message
    except (AttributeError, IndexError, TypeError):
        return ()
    annotations = _field(message, "annotations")
    if annotations is None:
        provider_fields = _field(message, "provider_specific_fields")
        annotations = _field(provider_fields, "annotations")
    if not isinstance(annotations, Sequence) or isinstance(annotations, (str, bytes)):
        return ()

    urls: list[str] = []
    for annotation in annotations:
        citation = _field(annotation, "url_citation")
        url = _field(citation, "url") or _field(annotation, "url")
        if isinstance(url, str) and url and url not in urls:
            urls.append(url)
    return tuple(urls)


def _extract_source_urls(response: Any) -> tuple[str, ...]:
    try:
        return _extract_source_urls_unchecked(response)
    except Exception:  # noqa: BLE001 - provider annotations are untrusted
        return ()


async def complete_with_web_search(
    messages: Sequence[ChatMessage],
    *,
    options: LLMOptions | None = None,
) -> WebSearchResult | None:
    """Return a native web-search completion, or ``None`` when unavailable."""
    selected = options or LLMOptions(
        provider=runtime_config.ai_provider,
        model=runtime_config.ai_model,
        base_url=runtime_config.ai_base_url,
        api_key=runtime_config.ai_api_key,
        timeout=runtime_config.ai_timeout,
    )
    started = monotonic()
    if not supports_web_search(selected):
        logger.info(
            "LLM web search skipped: model={}, reason=unsupported, "
            "duration={:.3f}s, sources=0",
            selected.model,
            monotonic() - started,
        )
        return None
    try:
        response = await _call_litellm_web_search(
            model=selected.model,
            messages=messages,
            api_base=selected.base_url,
            api_key=selected.api_key,
            request_timeout=selected.timeout,
        )
        text = _extract_content(response)
    except Exception:  # noqa: BLE001 - provider failures are soft failures
        logger.warning(
            "LLM web search failed: model={}, reason=provider_error, "
            "duration={:.3f}s, sources=0",
            selected.model,
            monotonic() - started,
        )
        return None
    sources = _extract_source_urls(response)
    logger.info(
        "LLM web search completed: model={}, reason=success, "
        "duration={:.3f}s, sources={}",
        selected.model,
        monotonic() - started,
        len(sources),
    )
    return WebSearchResult(text=text, sources=sources)


async def _call_openai(
    *,
    model: str,
    messages: Sequence[ChatMessage],
    base_url: str | None,
    api_key: str | None,
    request_timeout: float,
) -> Any:
    from openai import (  # pyright: ignore[reportMissingImports]  # ty: ignore[unresolved-import]
        AsyncOpenAI,
    )

    client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=request_timeout)
    return await client.chat.completions.create(
        model=model,
        messages=cast("list[ChatCompletionMessageParam]", list(messages)),
    )


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
    selected = options or LLMOptions(
        provider=runtime_config.ai_provider,
        model=runtime_config.ai_model,
        base_url=runtime_config.ai_base_url,
        api_key=runtime_config.ai_api_key,
        timeout=runtime_config.ai_timeout,
    )
    selected_model = model or selected.model
    try:
        if selected.provider == "openai":
            response = await _call_openai(
                model=selected_model,
                messages=messages,
                base_url=selected.base_url,
                api_key=selected.api_key,
                request_timeout=selected.timeout,
            )
        else:
            response = await _call_litellm(
                model=selected_model,
                messages=messages,
                api_base=selected.base_url,
                api_key=selected.api_key,
                request_timeout=selected.timeout,
            )
    except LLMError:
        raise
    except Exception as exc:
        raise LLMProviderError from exc
    return _extract_content(response)
