"""Thin LLM service over LiteLLM with OpenAI SDK fallback."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, cast

from ..core.runtime_config import runtime_config

if TYPE_CHECKING:
    from openai.types.chat import (
        ChatCompletionMessageParam,  # pyright: ignore[reportMissingImports]
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
    from litellm import acompletion  # pyright: ignore[reportAttributeAccessIssue]

    return await acompletion(
        model=model,
        messages=list(messages),
        api_base=api_base,
        api_key=api_key,
        timeout=request_timeout,
    )


async def _call_openai(
    *,
    model: str,
    messages: Sequence[ChatMessage],
    base_url: str | None,
    api_key: str | None,
    request_timeout: float,
) -> Any:
    from openai import AsyncOpenAI  # pyright: ignore[reportMissingImports]

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
