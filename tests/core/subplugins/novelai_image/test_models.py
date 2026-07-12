from dataclasses import FrozenInstanceError

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.models import (
    CharacterIntent,
    GenerationHints,
    GenerationOverrides,
    NovelAIGenerationPlan,
    PositionCoord,
    PromptIntent,
    TipoPrompt,
    TipoRequest,
    VisualResearch,
    normalize_negative_prompt,
)


def test_position_coord_clamps_to_novelai_safe_range() -> None:
    assert PositionCoord(x=-1, y=2) == PositionCoord(x=0.1, y=0.9)


def test_tags_are_trimmed_and_deduplicated_case_insensitively() -> None:
    value = TipoPrompt(
        natural_language="portrait",
        tags=("1girl", " 1GIRL ", "blue hair", ""),
    )

    assert value.tags == ("1girl", "blue hair")


def test_collection_fields_are_immutable_tuples() -> None:
    character = CharacterIntent(
        description="girl",
        tags=["blue hair"],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        negative_tags=["text"],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        center=PositionCoord(0.5, 0.5),
    )
    intent = PromptIntent(
        source_language="zh",
        english_description="a girl",
        base_tags=["1girl"],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        generation=GenerationHints(
            negative_tags=["watermark"],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        ),
        characters=[character],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        search_required=False,
        search_query=None,
        search_reason=None,
    )
    research = VisualResearch(
        facts=["blue coat"],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        sources=["https://example.test"],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
    )
    request = TipoRequest(
        description="a girl",
        tags=["1girl"],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        visual_facts=["blue coat"],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        seed=1,
    )

    assert intent.base_tags == ("1girl",)
    assert intent.characters == (character,)
    assert intent.generation.negative_tags == ("watermark",)
    assert character.tags == ("blue hair",)
    assert research.facts == ("blue coat",)
    assert research.sources == ("https://example.test",)
    assert request.tags == ("1girl",)
    assert request.visual_facts == ("blue coat",)
    with pytest.raises(FrozenInstanceError):
        request.seed = 2  # type: ignore[misc]  # ty: ignore[invalid-assignment]


@pytest.mark.parametrize("seed", [-1, 2**32])
def test_intermediate_seed_fields_preserve_values_for_planner_validation(
    seed: int,
) -> None:
    assert GenerationHints(seed=seed).seed == seed
    assert GenerationOverrides(seed=seed).seed == seed


@pytest.mark.parametrize("seed", [-1, 2**32])
def test_final_seed_fields_reject_values_outside_unsigned_32_bit_range(
    seed: int,
) -> None:
    with pytest.raises(ValueError, match="seed"):
        TipoRequest(description="scene", tags=(), visual_facts=(), seed=seed)
    with pytest.raises(ValueError, match="seed"):
        NovelAIGenerationPlan(
            prompt="portrait",
            negative_prompt="text",
            width=832,
            height=1216,
            steps=28,
            scale=5.0,
            sampler="k_euler_ancestral",
            seed=seed,
            base_caption="portrait",
            char_captions=(),
            character_prompts=(),
            use_coords=False,
        )


def test_negative_prompt_splits_and_deduplicates_normalized_tags() -> None:
    assert normalize_negative_prompt(" text, Watermark\nTEXT ,, bad hands ") == (
        "text",
        "Watermark",
        "bad hands",
    )


def test_generation_plan_normalizes_nested_collections() -> None:
    char_caption = {"char_caption": "blue hair"}
    character_prompt = {"prompt": "blue hair"}
    value = NovelAIGenerationPlan(
        prompt="portrait",
        negative_prompt="text",
        width=832,
        height=1216,
        steps=28,
        scale=5.0,
        sampler="k_euler_ancestral",
        seed=1,
        base_caption="portrait",
        char_captions=[char_caption],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        character_prompts=[character_prompt],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        use_coords=True,
    )

    assert value.char_captions == (char_caption,)
    assert value.character_prompts == (character_prompt,)
