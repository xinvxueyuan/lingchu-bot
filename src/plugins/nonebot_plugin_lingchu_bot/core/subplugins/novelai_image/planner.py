"""Pure deterministic planning for NovelAI image generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import NovelAIGenerationPlan, normalize_negative_prompt, normalize_tags

if TYPE_CHECKING:
    from collections.abc import Callable

    from .config import NovelAIConfig
    from .models import GenerationOverrides, PromptIntent, TipoPrompt

_MAX_SEED = 2**32 - 1
_MIN_DIMENSION = 64
_MAX_DIMENSION = 2048
_MAX_STEPS = 50
_MAX_SCALE = 20

_NOVELAI_SAMPLERS = frozenset({
    "k_euler",
    "k_euler_ancestral",
    "k_dpmpp_2m",
    "k_dpmpp_2s_ancestral",
    "k_dpmpp_sde",
    "k_dpmpp_2m_sde",
    "ddim_v3",
})

_SAMPLER_ALIASES = {
    "euler": "k_euler",
    "euler a": "k_euler_ancestral",
    "euler_a": "k_euler_ancestral",
    "euler ancestral": "k_euler_ancestral",
    "euler-ancestral": "k_euler_ancestral",
    "dpm++ 2m": "k_dpmpp_2m",
    "dpm++2m": "k_dpmpp_2m",
    "dpm++ 2s a": "k_dpmpp_2s_ancestral",
    "dpm++ sde": "k_dpmpp_sde",
    "dpm++ 2m sde": "k_dpmpp_2m_sde",
    "ddim": "ddim_v3",
    "ddim_v3": "ddim_v3",
}


def _normalize_sampler(value: str) -> str | None:
    """Map a sampler name (NovelAI native or WebUI alias) to NovelAI form.

    Returns ``None`` when the name is unrecognized so the caller can fall
    back to the configured default instead of sending an invalid value.
    """
    key = value.strip().casefold()
    if key in _NOVELAI_SAMPLERS:
        return key
    return _SAMPLER_ALIASES.get(key)


class InvalidGenerationOverrideError(ValueError):
    """Raised when an explicit generation override is outside safe limits."""

    def __init__(self, field: str) -> None:
        super().__init__(f"invalid {field} override")


def _choose[T: (int, float, str)](
    name: str,
    explicit: T | None,
    inferred: T | None,
    default: T,
    valid: Callable[[T], bool],
) -> T:
    if explicit is not None:
        if not valid(explicit):
            raise InvalidGenerationOverrideError(name)
        return explicit
    if inferred is not None and valid(inferred):
        return inferred
    return default


def _joined(description: str, tags: tuple[str, ...]) -> str:
    return ", ".join((description, *tags))


def _dimension_is_valid(value: int) -> bool:
    return _MIN_DIMENSION <= value <= _MAX_DIMENSION


def build_generation_plan(
    intent: PromptIntent,
    *,
    tipo_prompt: TipoPrompt | None,
    overrides: GenerationOverrides,
    config: NovelAIConfig,
    random_seed: int,
) -> NovelAIGenerationPlan:
    """Merge explicit, inferred, and configured values into a final plan."""
    width = _choose(
        "width",
        overrides.width,
        intent.generation.width,
        config.width,
        _dimension_is_valid,
    )
    height = _choose(
        "height",
        overrides.height,
        intent.generation.height,
        config.height,
        _dimension_is_valid,
    )
    steps = _choose(
        "steps",
        overrides.steps,
        intent.generation.steps,
        config.steps,
        lambda value: 1 <= value <= _MAX_STEPS,
    )
    scale = _choose(
        "scale",
        overrides.scale,
        intent.generation.scale,
        config.scale,
        lambda value: 0 < value <= _MAX_SCALE,
    )
    sampler = _choose(
        "sampler",
        overrides.sampler,
        intent.generation.sampler,
        config.sampler,
        lambda v: _normalize_sampler(v) is not None,
    )
    sampler = _normalize_sampler(sampler) or config.sampler
    seed = _choose(
        "seed",
        overrides.seed,
        intent.generation.seed,
        random_seed,
        lambda v: 0 <= v <= _MAX_SEED,
    )

    tipo_is_valid = bool(
        tipo_prompt
        and tipo_prompt.natural_language.strip()
        and normalize_tags(tipo_prompt.tags)
    )
    if tipo_is_valid and tipo_prompt is not None:
        base_caption = tipo_prompt.natural_language.strip()
        prompt_tags = normalize_tags(tipo_prompt.tags)
    else:
        base_caption = intent.english_description
        prompt_tags = intent.base_tags
    prompt = _joined(base_caption, prompt_tags)

    negative_tags = normalize_tags((
        *normalize_negative_prompt(config.negative_prompt),
        *intent.generation.negative_tags,
        *(tag for character in intent.characters for tag in character.negative_tags),
        *normalize_negative_prompt(overrides.negative_prompt),
    ))

    char_captions: list[dict[str, object]] = []
    character_prompts: list[dict[str, object]] = []
    for character in intent.characters:
        character_prompt = _joined(character.description, character.tags)
        center = {"x": character.center.x, "y": character.center.y}
        char_captions.append({
            "char_caption": character_prompt,
            "centers": [center.copy()],
        })
        character_prompts.append({
            "prompt": character_prompt,
            "uc": ", ".join(character.negative_tags),
            "center": center,
            "enabled": True,
        })

    return NovelAIGenerationPlan(
        prompt=prompt,
        negative_prompt=", ".join(negative_tags),
        width=width,
        height=height,
        steps=steps,
        scale=scale,
        sampler=sampler,
        seed=seed,
        base_caption=base_caption,
        char_captions=tuple(char_captions),
        character_prompts=tuple(character_prompts),
        use_coords=bool(intent.characters),
    )
