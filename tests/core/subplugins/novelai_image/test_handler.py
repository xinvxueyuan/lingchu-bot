from unittest.mock import AsyncMock, Mock

import pytest
from nonebot.exception import FinishedException

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.contracts import (
    SubpluginLLMError,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image import (
    handler,
    i18n,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image import (
    intent as intent_boundary,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client import (
    MissingNovelAITokenError,
    NovelAIProviderError,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.config import (
    NovelAIConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.intent import (
    IntentAnalysisError,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.models import (
    GenerationHints,
    GenerationOverrides,
    NovelAIGenerationPlan,
    PromptIntent,
    TipoPrompt,
    VisualResearch,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.tipo import (
    TipoProviderError,
)


@pytest.fixture(autouse=True)
def mock_finish(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    finish = AsyncMock(side_effect=FinishedException)
    monkeypatch.setattr(handler.novelai_image_cmd, "finish", finish)
    return finish


@pytest.fixture
def intent() -> PromptIntent:
    return PromptIntent(
        source_language="zh",
        english_description="A cat",
        base_tags=("cat",),
        generation=GenerationHints(),
        characters=(),
        search_required=False,
        search_query=None,
        search_reason=None,
    )


@pytest.fixture
def plan() -> NovelAIGenerationPlan:
    return NovelAIGenerationPlan(
        prompt="A cat, cat",
        negative_prompt="text",
        width=832,
        height=1216,
        steps=28,
        scale=5.0,
        sampler="k_euler_ancestral",
        seed=7,
        base_caption="A cat",
        char_captions=(),
        character_prompts=(),
        use_coords=False,
    )


def test_command_trigger_is_locale_exclusive() -> None:
    from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.contracts import (
        SubpluginTrigger,
        get_subplugin_trigger,
    )

    trigger = get_subplugin_trigger("novelai_image")
    assert isinstance(trigger, SubpluginTrigger)
    assert trigger.primary
    assert trigger.aliases


def test_child_messages_follow_configured_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(i18n, "get_configured_locale", lambda: "zh_CN")
    assert i18n.translate("parameter_invalid") == "生图参数无效，请检查后重试"
    monkeypatch.setattr(i18n, "get_configured_locale", lambda: "en_US")
    assert i18n.translate("parameter_invalid") == "Invalid image parameters"


def test_command_options_are_parsed_into_overrides() -> None:
    command = handler.build_novelai_image_command()
    trigger = handler._novelai_trigger.primary
    result = command.parse(
        f"{trigger} a cat --width 1024 --height 768 --steps 30 --scale 6 "
        "--sampler k_euler --seed 42 --negative text,watermark"
    )
    assert result.matched
    assert handler.generation_overrides_from_args(result.all_matched_args) == (
        GenerationOverrides(
            width=1024,
            height=768,
            steps=30,
            scale=6.0,
            sampler="k_euler",
            seed=42,
            negative_prompt="text,watermark",
        )
    )


def test_omitted_options_remain_none() -> None:
    result = handler.build_novelai_image_command().parse(
        f"{handler._novelai_trigger.primary} a cat"
    )
    assert result.matched
    assert handler.generation_overrides_from_args(result.all_matched_args) == (
        GenerationOverrides()
    )


@pytest.mark.parametrize(
    "overrides",
    [
        GenerationOverrides(width=1),
        GenerationOverrides(height=4096),
        GenerationOverrides(steps=0),
        GenerationOverrides(scale=21),
        GenerationOverrides(sampler=" "),
        GenerationOverrides(seed=2**32),
    ],
)
async def test_invalid_override_stops_before_intent(
    monkeypatch: pytest.MonkeyPatch,
    mock_finish: AsyncMock,
    overrides: GenerationOverrides,
) -> None:
    analyze = AsyncMock()
    generate = AsyncMock()
    monkeypatch.setattr(handler, "analyze_prompt_intent", analyze)
    monkeypatch.setattr(handler, "generate_image", generate)

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(
            ["cat"],
            overrides=overrides,
            config=NovelAIConfig(token="token"),
        )

    analyze.assert_not_awaited()
    generate.assert_not_awaited()
    mock_finish.assert_awaited_once_with(handler.translate("parameter_invalid"))


async def test_pipeline_without_search_passes_each_stage_once(
    monkeypatch: pytest.MonkeyPatch,
    intent: PromptIntent,
    plan: NovelAIGenerationPlan,
    mock_finish: AsyncMock,
) -> None:
    analyze = AsyncMock(return_value=intent)
    research = AsyncMock(return_value=VisualResearch((), ()))
    tipo = TipoPrompt("A detailed cat", ("cat", "detailed"))
    expand = AsyncMock(return_value=tipo)
    build = Mock(return_value=plan)
    generate = AsyncMock(return_value=b"image")
    monkeypatch.setattr(handler, "analyze_prompt_intent", analyze)
    monkeypatch.setattr(handler, "research_visual_facts", research)
    monkeypatch.setattr(handler, "expand_with_tipo", expand)
    monkeypatch.setattr(handler, "build_generation_plan", build)
    monkeypatch.setattr(handler, "generate_image", generate)
    monkeypatch.setattr(handler.secrets, "randbelow", lambda _: 7)

    config = NovelAIConfig(token="token")
    overrides = GenerationOverrides(width=1024)
    with pytest.raises(FinishedException):
        await handler.run_novelai_image(["画猫"], overrides=overrides, config=config)

    analyze.assert_awaited_once_with("画猫")
    research.assert_not_awaited()
    assert expand.await_count == 1
    assert expand.await_args is not None
    tipo_request = expand.await_args.args[0]
    assert tipo_request.description == intent.english_description
    assert tipo_request.tags == intent.base_tags
    assert tipo_request.visual_facts == ()
    assert tipo_request.seed == 7
    expand.assert_awaited_once_with(tipo_request, config=config)
    build.assert_called_once_with(
        intent,
        tipo_prompt=tipo,
        overrides=overrides,
        config=config,
        random_seed=7,
    )
    generate.assert_awaited_once_with(plan, config=config)
    assert mock_finish.await_args is not None
    assert mock_finish.await_args.args[0].type == "image"


async def test_requested_search_facts_are_passed_to_tipo(
    monkeypatch: pytest.MonkeyPatch,
    intent: PromptIntent,
    plan: NovelAIGenerationPlan,
) -> None:
    searched_intent = PromptIntent(
        source_language=intent.source_language,
        english_description=intent.english_description,
        base_tags=intent.base_tags,
        generation=intent.generation,
        characters=intent.characters,
        search_required=True,
        search_query="canonical cat",
        search_reason="accuracy",
    )
    research_value = VisualResearch(("blue collar",), ("https://example.test",))
    monkeypatch.setattr(
        handler, "analyze_prompt_intent", AsyncMock(return_value=searched_intent)
    )
    research = AsyncMock(return_value=research_value)
    monkeypatch.setattr(handler, "research_visual_facts", research)
    expand = AsyncMock(return_value=TipoPrompt("cat", ("cat",)))
    monkeypatch.setattr(handler, "expand_with_tipo", expand)
    monkeypatch.setattr(handler, "build_generation_plan", Mock(return_value=plan))
    monkeypatch.setattr(handler, "generate_image", AsyncMock(return_value=b"image"))

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(["cat"], config=NovelAIConfig(token="token"))

    research.assert_awaited_once_with(searched_intent)
    assert expand.await_args is not None
    assert expand.await_args.args[0].visual_facts == research_value.facts


async def test_empty_research_still_reaches_tipo(
    monkeypatch: pytest.MonkeyPatch,
    intent: PromptIntent,
    plan: NovelAIGenerationPlan,
) -> None:
    searched_intent = PromptIntent(
        source_language=intent.source_language,
        english_description=intent.english_description,
        base_tags=intent.base_tags,
        generation=intent.generation,
        characters=intent.characters,
        search_required=True,
        search_query="cat",
        search_reason="accuracy",
    )
    monkeypatch.setattr(
        handler, "analyze_prompt_intent", AsyncMock(return_value=searched_intent)
    )
    monkeypatch.setattr(
        handler,
        "research_visual_facts",
        AsyncMock(return_value=VisualResearch((), ())),
    )
    expand = AsyncMock(return_value=TipoPrompt("cat", ("cat",)))
    monkeypatch.setattr(handler, "expand_with_tipo", expand)
    monkeypatch.setattr(handler, "build_generation_plan", Mock(return_value=plan))
    monkeypatch.setattr(handler, "generate_image", AsyncMock(return_value=b"image"))

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(["cat"], config=NovelAIConfig(token="token"))
    assert expand.await_args is not None
    assert expand.await_args.args[0].visual_facts == ()


async def test_tipo_failure_uses_intent_fallback(
    monkeypatch: pytest.MonkeyPatch,
    intent: PromptIntent,
    plan: NovelAIGenerationPlan,
) -> None:
    monkeypatch.setattr(
        handler, "analyze_prompt_intent", AsyncMock(return_value=intent)
    )
    monkeypatch.setattr(
        handler, "expand_with_tipo", AsyncMock(side_effect=TipoProviderError("bad"))
    )
    build = Mock(return_value=plan)
    monkeypatch.setattr(handler, "build_generation_plan", build)
    generate = AsyncMock(return_value=b"image")
    monkeypatch.setattr(handler, "generate_image", generate)

    config = NovelAIConfig(token="token")
    with pytest.raises(FinishedException):
        await handler.run_novelai_image(["cat"], config=config)

    assert build.call_args.kwargs["tipo_prompt"] is None
    generate.assert_awaited_once_with(plan, config=config)


async def test_disabled_tipo_skips_tipo_call(
    monkeypatch: pytest.MonkeyPatch,
    intent: PromptIntent,
    plan: NovelAIGenerationPlan,
) -> None:
    monkeypatch.setattr(
        handler, "analyze_prompt_intent", AsyncMock(return_value=intent)
    )
    expand = AsyncMock()
    monkeypatch.setattr(handler, "expand_with_tipo", expand)
    build = Mock(return_value=plan)
    monkeypatch.setattr(handler, "build_generation_plan", build)
    monkeypatch.setattr(handler, "generate_image", AsyncMock(return_value=b"image"))

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(
            ["cat"], config=NovelAIConfig(token="token", tipo_enabled=False)
        )
    expand.assert_not_awaited()
    assert build.call_args.kwargs["tipo_prompt"] is None


async def test_intent_failure_stops_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        handler,
        "analyze_prompt_intent",
        AsyncMock(side_effect=IntentAnalysisError("bad")),
    )
    expand = AsyncMock()
    generate = AsyncMock()
    monkeypatch.setattr(handler, "expand_with_tipo", expand)
    monkeypatch.setattr(handler, "generate_image", generate)

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(["cat"], config=NovelAIConfig(token="token"))
    expand.assert_not_awaited()
    generate.assert_not_awaited()


async def test_parent_llm_failure_returns_localized_prompt_error(
    monkeypatch: pytest.MonkeyPatch,
    mock_finish: AsyncMock,
) -> None:
    monkeypatch.setattr(
        intent_boundary,
        "complete_subplugin_chat_default",
        AsyncMock(side_effect=SubpluginLLMError("provider unavailable")),
    )
    monkeypatch.setattr(
        handler, "analyze_prompt_intent", intent_boundary.analyze_prompt_intent
    )
    generate = AsyncMock()
    monkeypatch.setattr(handler, "generate_image", generate)

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(["cat"], config=NovelAIConfig(token="token"))

    mock_finish.assert_awaited_once_with(handler.translate("prompt_failed"))
    generate.assert_not_awaited()


@pytest.mark.parametrize(
    ("error", "message_key"),
    [
        (MissingNovelAITokenError(), "token_missing"),
        (NovelAIProviderError(), "generation_failed"),
    ],
)
async def test_generation_errors_are_localized(  # noqa: PLR0913
    monkeypatch: pytest.MonkeyPatch,
    mock_finish: AsyncMock,
    intent: PromptIntent,
    plan: NovelAIGenerationPlan,
    error: Exception,
    message_key: str,
) -> None:
    monkeypatch.setattr(
        handler, "analyze_prompt_intent", AsyncMock(return_value=intent)
    )
    monkeypatch.setattr(handler, "expand_with_tipo", AsyncMock(return_value=None))
    monkeypatch.setattr(handler, "build_generation_plan", Mock(return_value=plan))
    monkeypatch.setattr(handler, "generate_image", AsyncMock(side_effect=error))

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(["cat"], config=NovelAIConfig(token="token"))
    mock_finish.assert_awaited_once_with(handler.translate(message_key))
