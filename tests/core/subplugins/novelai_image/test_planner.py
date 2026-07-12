from typing import Any

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.config import (
    NovelAIConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.models import (
    CharacterIntent,
    GenerationHints,
    GenerationOverrides,
    PositionCoord,
    PromptIntent,
    TipoPrompt,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.planner import (
    InvalidGenerationOverrideError,
    build_generation_plan,
)


def intent(
    *,
    generation: GenerationHints | None = None,
    characters: tuple[CharacterIntent, ...] = (),
) -> PromptIntent:
    return PromptIntent(
        source_language="en",
        english_description="A rainy station",
        base_tags=("night", "cinematic"),
        generation=generation or GenerationHints(),
        characters=characters,
        search_required=False,
        search_query=None,
        search_reason=None,
    )


@pytest.mark.parametrize(
    ("field", "explicit", "inferred", "default"),
    [
        ("width", 1024, 960, 832),
        ("height", 768, 1024, 1216),
        ("steps", 32, 30, 28),
        ("scale", 6.5, 5.5, 5.0),
        ("sampler", "k_euler", "k_dpmpp_2m", "k_euler_ancestral"),
        ("seed", 123, 456, 789),
    ],
)
def test_scalar_precedence_is_explicit_then_inferred_then_default(
    field: str,
    explicit: object,
    inferred: object,
    default: object,
) -> None:
    config_values: dict[str, Any] = {field: default}
    hint_values: dict[str, Any] = {field: inferred}
    override_values: dict[str, Any] = {field: explicit}

    explicit_plan = build_generation_plan(
        intent(generation=GenerationHints(**hint_values)),
        tipo_prompt=None,
        overrides=GenerationOverrides(**override_values),
        config=NovelAIConfig(**config_values),
        random_seed=999,
    )
    inferred_plan = build_generation_plan(
        intent(generation=GenerationHints(**hint_values)),
        tipo_prompt=None,
        overrides=GenerationOverrides(),
        config=NovelAIConfig(**config_values),
        random_seed=999,
    )
    default_plan = build_generation_plan(
        intent(),
        tipo_prompt=None,
        overrides=GenerationOverrides(),
        config=NovelAIConfig(**config_values),
        random_seed=999,
    )

    assert getattr(explicit_plan, field) == explicit
    assert getattr(inferred_plan, field) == inferred
    assert getattr(default_plan, field) == (999 if field == "seed" else default)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("width", 63),
        ("height", 2049),
        ("steps", 0),
        ("scale", 0),
        ("sampler", "  "),
        ("seed", 2**32),
    ],
)
def test_invalid_explicit_scalar_raises(field: str, value: object) -> None:
    with pytest.raises(InvalidGenerationOverrideError, match=field):
        invalid_overrides: dict[str, Any] = {field: value}
        build_generation_plan(
            intent(),
            tipo_prompt=None,
            overrides=GenerationOverrides(**invalid_overrides),
            config=NovelAIConfig(),
            random_seed=42,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("width", 63),
        ("height", 2049),
        ("steps", 0),
        ("scale", 0),
        ("sampler", "  "),
    ],
)
def test_invalid_inferred_scalar_uses_config_default(field: str, value: object) -> None:
    config = NovelAIConfig()
    invalid_hints: dict[str, Any] = {field: value}
    plan = build_generation_plan(
        intent(generation=GenerationHints(**invalid_hints)),
        tipo_prompt=None,
        overrides=GenerationOverrides(),
        config=config,
        random_seed=42,
    )

    assert getattr(plan, field) == getattr(config, field)


@pytest.mark.parametrize("seed", (-1, 2**32))
def test_invalid_inferred_seed_uses_random_seed(seed: int) -> None:
    plan = build_generation_plan(
        intent(generation=GenerationHints(seed=seed)),
        tipo_prompt=None,
        overrides=GenerationOverrides(),
        config=NovelAIConfig(),
        random_seed=42,
    )

    assert plan.seed == 42


def test_negative_prompt_precedence_merges_and_deduplicates_sources() -> None:
    plan = build_generation_plan(
        intent(
            generation=GenerationHints(negative_tags=("text", "bad hands")),
            characters=(
                CharacterIntent(
                    description="girl",
                    tags=("1girl",),
                    negative_tags=("bad hands", "extra fingers"),
                    center=PositionCoord(0.3, 0.5),
                ),
            ),
        ),
        tipo_prompt=None,
        overrides=GenerationOverrides(negative_prompt="watermark, TEXT"),
        config=NovelAIConfig(negative_prompt="lowres, text"),
        random_seed=42,
    )

    assert plan.negative_prompt == "lowres, text, bad hands, extra fingers, watermark"


def test_tipo_replaces_fallback_prompt_only_when_complete() -> None:
    fallback = build_generation_plan(
        intent(),
        tipo_prompt=None,
        overrides=GenerationOverrides(),
        config=NovelAIConfig(),
        random_seed=42,
    )
    tipo = build_generation_plan(
        intent(),
        tipo_prompt=TipoPrompt("Rain glitters under neon", ("masterpiece", "rain")),
        overrides=GenerationOverrides(),
        config=NovelAIConfig(),
        random_seed=42,
    )

    assert fallback.prompt == "A rainy station, night, cinematic"
    assert fallback.base_caption == "A rainy station"
    assert tipo.prompt == "Rain glitters under neon, masterpiece, rain"
    assert tipo.base_caption == "Rain glitters under neon"


def test_characters_retain_intent_prompts_negatives_and_coordinates() -> None:
    characters = (
        CharacterIntent(
            description="A silver-haired girl",
            tags=("1girl", "silver hair"),
            negative_tags=("bad hands",),
            center=PositionCoord(0.3, 0.5),
        ),
        CharacterIntent(
            description="A dark-haired boy",
            tags=("1boy", "black hair"),
            negative_tags=("bad eyes",),
            center=PositionCoord(0.7, 0.5),
        ),
    )
    plan = build_generation_plan(
        intent(characters=characters),
        tipo_prompt=TipoPrompt("TIPO scene", ("detailed",)),
        overrides=GenerationOverrides(),
        config=NovelAIConfig(),
        random_seed=42,
    )

    assert plan.use_coords is True
    assert plan.char_captions == (
        {
            "char_caption": "A silver-haired girl, 1girl, silver hair",
            "centers": [{"x": 0.3, "y": 0.5}],
        },
        {
            "char_caption": "A dark-haired boy, 1boy, black hair",
            "centers": [{"x": 0.7, "y": 0.5}],
        },
    )
    assert plan.character_prompts[0] == {
        "prompt": "A silver-haired girl, 1girl, silver hair",
        "uc": "bad hands",
        "center": {"x": 0.3, "y": 0.5},
        "enabled": True,
    }
    assert plan.character_prompts[1]["uc"] == "bad eyes"


def test_simple_scene_has_no_character_fields_and_fixed_seed_is_deterministic() -> None:
    intent_value = intent()
    first = build_generation_plan(
        intent=intent_value,
        tipo_prompt=None,
        overrides=GenerationOverrides(),
        config=NovelAIConfig(),
        random_seed=42,
    )
    second = build_generation_plan(
        intent=intent_value,
        tipo_prompt=None,
        overrides=GenerationOverrides(),
        config=NovelAIConfig(),
        random_seed=42,
    )

    assert first == second
    assert first.char_captions == ()
    assert first.character_prompts == ()
    assert first.use_coords is False
