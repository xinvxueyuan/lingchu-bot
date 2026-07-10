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
    assert prompt.compose_prompts(
        converted,
        default_negative="lowres, text",
    ) == (
        "A girl under blossoms, 1girl, Blue Hair",
        "lowres, text",
    )


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
