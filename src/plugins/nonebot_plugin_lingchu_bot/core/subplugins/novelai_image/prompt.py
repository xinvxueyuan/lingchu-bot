"""Convert user language into a NovelAI prompt with NL + tag dual constraints."""

# ruff: noqa: TRY003

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..contracts import complete_subplugin_chat
from .config import NovelAIConfig, resolve_prompt_llm_options

SYSTEM_PROMPT = """\
You are a NovelAI prompt expert. Convert the user's image request into \
structured JSON.

STEP 1 - Assess complexity:
  simple: single character, straightforward pose, simple background
  complex: multiple characters, character interactions, intricate spatial \
composition, or complex atmospheric scenes

STEP 2 - For ALL requests, provide:
  description: A rich English natural-language scene description. Write full \
sentences that capture semantic relationships, composition, mood, atmosphere, \
and spatial arrangements. Do NOT just restate tags as prose.
  tags: An array of English NovelAI tags for concrete visual elements \
(character count, hair color, eye color, clothing, background objects, etc.)
  negative_tags: An array of English tags for elements to avoid
  is_complex: boolean

STEP 3 - For COMPLEX scenes (is_complex: true), ALSO provide:
  characters: An array of objects, each with:
    prompt: NovelAI tags for this character's visual features \
(e.g., "1girl, silver hair, blue eyes, white dress, happy, sitting"). \
Must include a character-count tag (1girl / 1boy / etc.).
    negative_prompt: Tags this character should avoid \
(e.g., "bad hands, bad anatomy")
    center: {"x": <0.1-0.9>, "y": <0.1-0.9>} position within the image.
      x: 0.1=left, 0.5=center, 0.9=right
      y: 0.1=top, 0.5=middle, 0.9=bottom

Guidelines:
- description and tags must complement, not duplicate: description handles \
relationships/mood/composition; tags handle concrete visual attributes
- For two characters, spread them horizontally (e.g., x:0.3 and x:0.7)
- Place sitting characters around y:0.5, standing around y:0.4
- Keep characters between x:0.2-0.8 and y:0.3-0.7

Return ONLY valid JSON. No markdown fences or commentary."""


class PromptConversionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PositionCoord:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class CharacterPromptDef:
    prompt: str
    negative_prompt: str
    center: PositionCoord


@dataclass(frozen=True, slots=True)
class ConvertedPrompt:
    description: str
    tags: tuple[str, ...]
    negative_tags: tuple[str, ...]
    is_complex: bool = False
    characters: tuple[CharacterPromptDef, ...] = ()


@dataclass(frozen=True, slots=True)
class ComposedPrompt:
    base_caption: str
    negative_caption: str
    char_captions: tuple[dict[str, Any], ...] = ()
    character_prompts: tuple[dict[str, Any], ...] = ()
    use_coords: bool = False


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


def _parse_characters(value: object) -> tuple[CharacterPromptDef, ...]:
    if not isinstance(value, list):
        return ()
    result: list[CharacterPromptDef] = []
    for char in value:
        if not isinstance(char, dict):
            continue
        prompt = char.get("prompt", "")
        if not isinstance(prompt, str) or not prompt.strip():
            continue
        neg = char.get("negative_prompt", "")
        if not isinstance(neg, str):
            neg = ""
        center_raw = char.get("center", {})
        if not isinstance(center_raw, dict):
            center_raw = {}
        raw_x = center_raw.get("x", 0.5)
        raw_y = center_raw.get("y", 0.5)
        x = raw_x if isinstance(raw_x, (int, float)) else 0.5
        y = raw_y if isinstance(raw_y, (int, float)) else 0.5
        x = max(0.1, min(0.9, x))
        y = max(0.1, min(0.9, y))
        result.append(
            CharacterPromptDef(
                prompt=prompt.strip(),
                negative_prompt=neg.strip(),
                center=PositionCoord(x=x, y=y),
            )
        )
    return tuple(result)


def parse_converted_prompt(text: str) -> ConvertedPrompt:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise PromptConversionError("Prompt conversion returned no JSON object")
    try:
        value: Any = json.loads(text[start : end + 1])
        description = _required_text(value["description"])
        tags = _unique_strings(value["tags"])
        negative_tags = _unique_strings(value["negative_tags"], required=False)
        is_complex = bool(value.get("is_complex", False))
        characters = _parse_characters(value.get("characters", []))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise PromptConversionError("Prompt conversion returned invalid JSON") from exc
    return ConvertedPrompt(description, tags, negative_tags, is_complex, characters)


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
) -> ComposedPrompt:
    defaults = [item.strip() for item in default_negative.split(",") if item.strip()]
    negative = ", ".join(_unique_strings([*defaults, *converted.negative_tags]))

    if not converted.is_complex or not converted.characters:
        positive = ", ".join((converted.description, *converted.tags))
        return ComposedPrompt(base_caption=positive, negative_caption=negative)

    char_captions: list[dict[str, Any]] = []
    character_prompts: list[dict[str, Any]] = []
    for char_def in converted.characters:
        char_captions.append(
            {
                "char_caption": char_def.prompt,
                "centers": [{"x": char_def.center.x, "y": char_def.center.y}],
            }
        )
        character_prompts.append(
            {
                "prompt": char_def.prompt,
                "uc": char_def.negative_prompt,
                "center": {"x": char_def.center.x, "y": char_def.center.y},
                "enabled": True,
            }
        )

    return ComposedPrompt(
        base_caption=converted.description,
        negative_caption=negative,
        char_captions=tuple(char_captions),
        character_prompts=tuple(character_prompts),
        use_coords=True,
    )
