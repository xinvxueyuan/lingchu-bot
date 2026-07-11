from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image import prompt
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.config import (
    NovelAIConfig,
)


def test_parse_and_compose_prompt_deduplicates_tags() -> None:
    converted = prompt.parse_converted_prompt(
        '```json\n{"description":"A girl under blossoms",'
        '"tags":["1girl"," Blue Hair ","1GIRL"],'
        '"negative_tags":["text","TEXT"]}\n```'
    )

    assert converted.tags == ("1girl", "Blue Hair")
    assert not converted.is_complex
    composed = prompt.compose_prompts(converted, default_negative="lowres, text")
    assert composed.base_caption == "A girl under blossoms, 1girl, Blue Hair"
    assert composed.negative_caption == "lowres, text"
    assert composed.char_captions == ()
    assert composed.character_prompts == ()
    assert not composed.use_coords


async def test_convert_prompt_uses_resolved_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    complete = AsyncMock(
        return_value=(
            '{"description":"A cat in a hat","tags":["cat","hat"],'
            '"negative_tags":["text"]}'
        )
    )
    monkeypatch.setattr(prompt, "complete_subplugin_chat", complete)

    result = await prompt.convert_prompt("戴帽子的猫", config=NovelAIConfig())

    assert result.tags == ("cat", "hat")
    assert not result.is_complex
    assert complete.await_args is not None
    assert complete.await_args.kwargs["options"].model


def test_parse_prompt_allows_empty_negative_tags() -> None:
    converted = prompt.parse_converted_prompt(
        '{"description":"A cat","tags":["cat"],"negative_tags":[]}'
    )

    assert converted.negative_tags == ()


def test_parse_prompt_rejects_non_string_description() -> None:
    with pytest.raises(prompt.PromptConversionError):
        prompt.parse_converted_prompt(
            '{"description":42,"tags":["cat"],"negative_tags":[]}'
        )


def test_parse_complex_prompt_with_characters() -> None:
    converted = prompt.parse_converted_prompt(
        '{"description":"A girl embracing a boy under cherry blossoms",'
        '"tags":["1girl","1boy","cherry blossoms","hug"],'
        '"negative_tags":["text"],'
        '"is_complex":true,'
        '"characters":['
        '{"prompt":"1girl, silver hair, blue eyes, white dress","negative_prompt":"bad hands","center":{"x":0.3,"y":0.5}},'
        '{"prompt":"1boy, black hair, red eyes, school uniform","negative_prompt":"bad anatomy","center":{"x":0.7,"y":0.5}}'
        "]}"
        ""
    )

    assert converted.is_complex
    assert len(converted.characters) == 2
    assert (
        converted.characters[0].prompt == "1girl, silver hair, blue eyes, white dress"
    )
    assert converted.characters[0].negative_prompt == "bad hands"
    assert converted.characters[0].center.x == 0.3
    assert converted.characters[1].center.x == 0.7


def test_parse_prompt_defaults_is_complex_false() -> None:
    converted = prompt.parse_converted_prompt(
        '{"description":"A cat","tags":["cat"],"negative_tags":[]}'
    )
    assert not converted.is_complex
    assert converted.characters == ()


def test_parse_prompt_ignores_malformed_characters() -> None:
    converted = prompt.parse_converted_prompt(
        '{"description":"A scene","tags":["1girl"],'
        '"negative_tags":[],'
        '"characters":['
        '{"prompt":"","negative_prompt":"","center":{"x":0.5,"y":0.5}},'
        '{"prompt":"1girl, blue hair","negative_prompt":"","center":null},'
        '"not a dict",'
        '{"prompt":"1boy, red hair","negative_prompt":"bad hands","center":{"x":0.7,"y":0.5}}'
        "]}"
        ""
    )
    assert len(converted.characters) == 2
    assert converted.characters[0].prompt == "1girl, blue hair"
    assert converted.characters[0].center.x == 0.5
    assert converted.characters[1].prompt == "1boy, red hair"


def test_position_coord_clamped_to_valid_range() -> None:
    converted = prompt.parse_converted_prompt(
        '{"description":"A scene","tags":["1girl"],'
        '"negative_tags":[],'
        '"characters":['
        '{"prompt":"1girl","negative_prompt":"","center":{"x":-1.0,"y":2.0}}'
        "]}"
        ""
    )
    assert len(converted.characters) == 1
    assert converted.characters[0].center.x == 0.1
    assert converted.characters[0].center.y == 0.9


def test_compose_prompts_complex_scene_separates_nl_and_tags() -> None:
    converted = prompt.ConvertedPrompt(
        description="A girl embracing a boy under cherry blossoms at sunset",
        tags=("1girl", "1boy", "cherry blossoms", "hug", "sunset"),
        negative_tags=("text",),
        is_complex=True,
        characters=(
            prompt.CharacterPromptDef(
                prompt="1girl, silver hair, blue eyes, white dress",
                negative_prompt="bad hands",
                center=prompt.PositionCoord(x=0.3, y=0.5),
            ),
            prompt.CharacterPromptDef(
                prompt="1boy, black hair, red eyes, school uniform",
                negative_prompt="bad anatomy",
                center=prompt.PositionCoord(x=0.7, y=0.5),
            ),
        ),
    )

    composed = prompt.compose_prompts(converted, default_negative="lowres, bad anatomy")

    assert (
        composed.base_caption
        == "A girl embracing a boy under cherry blossoms at sunset"
    )
    assert composed.negative_caption == "lowres, bad anatomy, text"
    assert composed.use_coords
    assert len(composed.char_captions) == 2
    assert (
        composed.char_captions[0]["char_caption"]
        == "1girl, silver hair, blue eyes, white dress"
    )
    assert composed.char_captions[0]["centers"] == [{"x": 0.3, "y": 0.5}]
    assert len(composed.character_prompts) == 2
    assert (
        composed.character_prompts[1]["prompt"]
        == "1boy, black hair, red eyes, school uniform"
    )
    assert composed.character_prompts[1]["uc"] == "bad anatomy"
    assert composed.character_prompts[1]["center"] == {"x": 0.7, "y": 0.5}


def test_compose_prompts_simple_scene_no_char_captions() -> None:
    converted = prompt.ConvertedPrompt(
        description="A cat sitting on a windowsill",
        tags=("cat", "sitting", "windowsill"),
        negative_tags=("text",),
        is_complex=False,
    )

    composed = prompt.compose_prompts(converted, default_negative="lowres")

    assert (
        composed.base_caption
        == "A cat sitting on a windowsill, cat, sitting, windowsill"
    )
    assert composed.negative_caption == "lowres, text"
    assert composed.char_captions == ()
    assert composed.character_prompts == ()
    assert not composed.use_coords


def test_compose_prompts_complex_without_characters_falls_back() -> None:
    converted = prompt.ConvertedPrompt(
        description="A mysterious forest with fog",
        tags=("forest", "fog", "mysterious"),
        negative_tags=("text",),
        is_complex=True,
        characters=(),
    )

    composed = prompt.compose_prompts(converted, default_negative="lowres")

    assert (
        composed.base_caption == "A mysterious forest with fog, forest, fog, mysterious"
    )
    assert not composed.use_coords
