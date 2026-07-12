import json
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.contracts import (
    SubpluginLLMError,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image import intent


def _payload(**overrides: object) -> str:
    value: dict[str, object] = {
        "source_language": "zh",
        "english_description": "A girl beneath cherry blossoms",
        "base_tags": ["1girl", " cherry blossoms ", "1GIRL"],
        "generation": {
            "width": 832,
            "height": 1216,
            "steps": 28,
            "scale": 5.5,
            "sampler": "k_euler",
            "seed": 42,
            "negative_tags": ["lowres", " LOWRES "],
        },
        "characters": [],
        "search_required": False,
        "search_query": None,
        "search_reason": None,
    }
    value.update(overrides)
    return json.dumps(value)


def test_parse_chinese_result_and_normalizes_tags() -> None:
    result = intent.parse_prompt_intent(_payload())

    assert result.source_language == "zh"
    assert result.english_description == "A girl beneath cherry blossoms"
    assert result.base_tags == ("1girl", "cherry blossoms")
    assert result.generation.negative_tags == ("lowres",)


def test_parse_english_passthrough_result() -> None:
    result = intent.parse_prompt_intent(
        _payload(source_language="en", english_description="A red fox in snow")
    )
    assert result.english_description == "A red fox in snow"


def test_parse_search_required_with_query_and_reason() -> None:
    result = intent.parse_prompt_intent(
        _payload(
            search_required=True,
            search_query="Frieren canonical costume",
            search_reason="Named fictional character",
        )
    )
    assert result.search_query == "Frieren canonical costume"
    assert result.search_reason == "Named fictional character"


def test_parse_search_required_without_query_fails() -> None:
    with pytest.raises(intent.IntentAnalysisError, match="requires a query"):
        intent.parse_prompt_intent(_payload(search_required=True, search_query=None))


def test_parse_search_not_required_discards_query_and_reason() -> None:
    result = intent.parse_prompt_intent(
        _payload(search_query="ignored", search_reason="ignored")
    )
    assert result.search_query is None
    assert result.search_reason is None


def test_parse_generation_hints_and_multiple_clamped_characters() -> None:
    characters = [
        {
            "description": "left heroine",
            "tags": ["blue hair", "Blue Hair"],
            "negative_tags": ["hat"],
            "center": {"x": -2, "y": 0.4},
        },
        {
            "description": "right hero",
            "tags": ["black hair"],
            "negative_tags": [],
            "center": {"x": 2, "y": 1.5},
        },
    ]
    result = intent.parse_prompt_intent(_payload(characters=characters))

    assert result.generation.width == 832
    assert result.generation.scale == 5.5
    assert result.characters[0].tags == ("blue hair",)
    assert (result.characters[0].center.x, result.characters[0].center.y) == (0.1, 0.4)
    assert (result.characters[1].center.x, result.characters[1].center.y) == (0.9, 0.9)


@pytest.mark.parametrize(
    "characters",
    [
        "not-a-list",
        [{"description": "x", "tags": [], "negative_tags": [], "center": {}}],
        [
            {
                "description": 1,
                "tags": [],
                "negative_tags": [],
                "center": {"x": 0.5, "y": 0.5},
            }
        ],
    ],
)
def test_parse_rejects_malformed_characters(characters: object) -> None:
    with pytest.raises(intent.IntentAnalysisError):
        intent.parse_prompt_intent(_payload(characters=characters))


def test_parse_rejects_missing_english_description() -> None:
    with pytest.raises(intent.IntentAnalysisError):
        intent.parse_prompt_intent(_payload(english_description="  "))


def test_parse_rejects_non_object_json() -> None:
    with pytest.raises(intent.IntentAnalysisError, match="JSON object"):
        intent.parse_prompt_intent("[]")


@pytest.mark.parametrize(
    "wrapper",
    [
        "[] {payload}",
        "{payload} []",
        "{payload} true",
        "{payload} trailing prose",
    ],
)
def test_parse_rejects_content_outside_the_single_json_object(wrapper: str) -> None:
    with pytest.raises(intent.IntentAnalysisError, match="exactly one JSON object"):
        intent.parse_prompt_intent(wrapper.format(payload=_payload()))


@pytest.mark.parametrize(
    "text",
    [
        _payload(
            characters=[
                {
                    "description": "x",
                    "tags": [],
                    "negative_tags": [],
                    "center": {"x": float("nan"), "y": 0.5},
                }
            ]
        ),
        _payload(
            characters=[
                {
                    "description": "x",
                    "tags": [],
                    "negative_tags": [],
                    "center": {"x": float("inf"), "y": 0.5},
                }
            ]
        ),
        _payload(
            generation={
                "width": None,
                "height": None,
                "steps": None,
                "scale": float("-inf"),
                "sampler": None,
                "seed": None,
                "negative_tags": [],
            }
        ),
    ],
)
def test_parse_rejects_non_finite_numbers(text: str) -> None:
    with pytest.raises(intent.IntentAnalysisError):
        intent.parse_prompt_intent(text)


@pytest.mark.parametrize(
    "text",
    [
        _payload(
            characters=[
                {
                    "description": "x",
                    "tags": [],
                    "negative_tags": [],
                    "center": {"x": 0.5, "y": 0.5},
                }
            ]
        ).replace('"x": 0.5', '"x": 1e999'),
        _payload().replace('"scale": 5.5', '"scale": -1e999'),
    ],
)
def test_parse_rejects_overflowing_finite_syntax(text: str) -> None:
    with pytest.raises(intent.IntentAnalysisError):
        intent.parse_prompt_intent(text)


async def test_analyze_calls_default_contract_with_complete_schema_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    complete = AsyncMock(return_value=_payload())
    monkeypatch.setattr(intent, "complete_subplugin_chat_default", complete)

    await intent.analyze_prompt_intent("画一个原创的雨中少女 --steps 30")

    assert complete.await_args is not None
    messages = complete.await_args.args[0]
    assert [message["role"] for message in messages] == ["system", "user"]
    system = messages[0]["content"]
    for field in (
        "source_language",
        "english_description",
        "base_tags",
        "generation",
        "characters",
        "search_required",
        "search_query",
        "search_reason",
    ):
        assert field in system
    assert "exactly one JSON object" in system
    assert "current or canonical visual facts" in system
    assert "generic original scenes" in system
    assert "untrusted data" in system
    assert "command option precedence" in system
    assert messages[1]["content"] == "画一个原创的雨中少女 --steps 30"


async def test_analyze_translates_parent_llm_failure_to_intent_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    complete = AsyncMock(side_effect=SubpluginLLMError("provider unavailable"))
    monkeypatch.setattr(intent, "complete_subplugin_chat_default", complete)

    with pytest.raises(intent.IntentAnalysisError) as exc_info:
        await intent.analyze_prompt_intent("a cat")

    assert isinstance(exc_info.value.__cause__, SubpluginLLMError)
