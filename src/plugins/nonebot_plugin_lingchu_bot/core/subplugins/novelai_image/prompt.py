"""Convert user language into a NovelAI prompt."""

# ruff: noqa: TRY003

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..contracts import complete_subplugin_chat
from .config import NovelAIConfig, resolve_prompt_llm_options

SYSTEM_PROMPT = """Convert the user's image request to NovelAI input.
Return only JSON with: description (an English scene description), tags (an
array of English NovelAI tags), and negative_tags (an array of English tags).
Do not add markdown or commentary."""


class PromptConversionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ConvertedPrompt:
    description: str
    tags: tuple[str, ...]
    negative_tags: tuple[str, ...]


def _unique_strings(
    value: object,
    *,
    required: bool = True,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise PromptConversionError("Prompt tags must be string arrays")
    seen: set[str] = set()
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise PromptConversionError("Prompt tags must be string arrays")
        normalized = item.strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    if required and not result:
        raise PromptConversionError("Prompt tags cannot be empty")
    return tuple(result)


def _required_text(value: object) -> str:
    if not isinstance(value, str) or not (text := value.strip()):
        raise PromptConversionError("Prompt description cannot be empty")
    return text


def parse_converted_prompt(text: str) -> ConvertedPrompt:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise PromptConversionError("Prompt conversion returned no JSON object")
    try:
        value: Any = json.loads(text[start : end + 1])
        description = _required_text(value["description"])
        tags = _unique_strings(value["tags"])
        negative_tags = _unique_strings(value["negative_tags"], required=False)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise PromptConversionError("Prompt conversion returned invalid JSON") from exc
    return ConvertedPrompt(description, tags, negative_tags)


async def convert_prompt(
    user_text: str,
    *,
    config: NovelAIConfig,
) -> ConvertedPrompt:
    try:
        response = await complete_subplugin_chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            options=resolve_prompt_llm_options(config),
        )
    except Exception as exc:
        raise PromptConversionError("Prompt conversion provider failed") from exc
    return parse_converted_prompt(response)


def compose_prompts(
    converted: ConvertedPrompt,
    *,
    default_negative: str,
) -> tuple[str, str]:
    positive = ", ".join((converted.description, *converted.tags))
    defaults = [item.strip() for item in default_negative.split(",") if item.strip()]
    negative = _unique_strings([*defaults, *converted.negative_tags])
    return positive, ", ".join(negative)
