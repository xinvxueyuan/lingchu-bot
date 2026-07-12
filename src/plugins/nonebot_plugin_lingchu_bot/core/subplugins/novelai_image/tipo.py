"""llama.cpp completion boundary for TIPO prompt expansion."""

# ruff: noqa: TRY003

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from nonebot import get_driver
from nonebot.drivers import Request

from .models import TipoPrompt

if TYPE_CHECKING:
    from .config import NovelAIConfig
    from .models import TipoRequest

HTTP_BAD_REQUEST = 400
_FIELD = re.compile(r"(?:^|\n)([^:\n]+):(.*(?:\n(?![^:\n]+:).*)*)")
_MAX_VISUAL_FACTS = 8
_MAX_VISUAL_FACT_LENGTH = 200


class TipoError(RuntimeError):
    pass


class TipoTransportError(TipoError):
    pass


class TipoProviderError(TipoError):
    pass


class TipoResponseError(TipoError):
    pass


def _split_tags(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in re.split(r"[,\n]", value) if part.strip())


def parse_tipo_prompt(text: str) -> TipoPrompt:
    """Parse TIPO's native colon-delimited completion fields."""
    content = text.strip().removeprefix("<s>").removesuffix("</s>").strip()
    fields: dict[str, str] = {}
    for name, value in _FIELD.findall(content):
        fields.setdefault(name.strip().casefold(), value.strip())

    natural_language = fields.get("long") or fields.get("short") or ""
    tags: list[str] = []
    seen: set[str] = set()
    for tag in _split_tags(fields.get("tag", "")):
        key = tag.casefold()
        if key not in seen:
            seen.add(key)
            tags.append(tag)
    if not natural_language or not tags:
        raise TipoResponseError("TIPO completion must contain generated text and tags")
    return TipoPrompt(natural_language=natural_language, tags=tuple(tags))


def _completion_prompt(request: TipoRequest) -> str:
    description = _single_line(request.description)
    tags = tuple(_single_line(tag) for tag in request.tags if _single_line(tag))
    facts = tuple(
        _single_line(fact)[:_MAX_VISUAL_FACT_LENGTH]
        for fact in request.visual_facts[:_MAX_VISUAL_FACTS]
        if _single_line(fact)
    )
    short = "; ".join(
        part for part in (description, ", ".join(tags), ", ".join(facts)) if part
    )
    return f"target: <|long|> <|short_to_tag_to_long|>\nshort: {short}\ntag:"


def _single_line(value: str) -> str:
    return " ".join(value.split())


def _response_payload(content: Any) -> Any:
    if isinstance(content, bytes):
        try:
            return json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TipoResponseError("TIPO response is not valid JSON") from exc
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise TipoResponseError("TIPO response is not valid JSON") from exc
    return content


async def expand_with_tipo(
    request: TipoRequest,
    *,
    config: NovelAIConfig,
) -> TipoPrompt:
    """Expand a request through llama.cpp's OpenAI-compatible completion API."""
    if not config.tipo_enabled:
        raise TipoError("TIPO is disabled")
    headers = {"Content-Type": "application/json"}
    if config.tipo_api_key:
        headers["Authorization"] = f"Bearer {config.tipo_api_key}"
    http_request = Request(
        "POST",
        f"{config.tipo_base_url.rstrip('/')}/completions",
        headers=headers,
        json={
            "model": config.tipo_model,
            "prompt": _completion_prompt(request),
            "max_tokens": config.tipo_max_tokens,
            "temperature": config.tipo_temperature,
            "top_p": config.tipo_top_p,
            "top_k": config.tipo_top_k,
            "seed": request.seed,
        },
        timeout=config.tipo_timeout,
    )
    get_session = getattr(get_driver(), "get_session", None)
    if get_session is None:
        raise TipoError("NoneBot HTTP client is unavailable")
    try:
        async with get_session() as session:
            response = await session.request(http_request)
    except Exception as exc:
        raise TipoTransportError("TIPO request transport failed") from exc
    if response.status_code >= HTTP_BAD_REQUEST:
        raise TipoProviderError(f"TIPO returned HTTP {response.status_code}")
    payload = _response_payload(response.content)
    try:
        completion = payload["choices"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise TipoResponseError("TIPO response has no completion text") from exc
    if not isinstance(completion, str) or not completion.strip():
        raise TipoResponseError("TIPO completion text is empty")
    completion = completion.strip().removeprefix("<s>").lstrip()
    if not completion.startswith("tag:"):
        completion = f"tag:{completion}"
    return parse_tipo_prompt(completion)
