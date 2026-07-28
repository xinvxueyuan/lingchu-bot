from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

from nonebot.exception import FinishedException
from nonebot_plugin_alconna.uniseg import Image as UniImage
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.contracts import (
    SubpluginLLMError,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image import (
    handler,
    i18n,
    intent as intent_boundary,
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
def mock_mcp_client(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Mock the NovelAI MCP client singleton."""
    client = AsyncMock()
    monkeypatch.setattr(handler, "get_novelai_mcp_client", lambda _: client)
    return client


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
    ("command_text", "path"),
    [
        ("tags ca", "tags"),
        ("account subscription", "account"),
    ],
)
def test_command_parser_recognizes_full_api_subcommands(
    command_text: str,
    path: str,
) -> None:
    result = handler.build_novelai_image_command().parse(
        f"{handler._novelai_trigger.primary} {command_text}"
    )
    assert result.matched
    assert result.find(path)


@pytest.mark.parametrize(
    ("action", "tool_name"),
    [
        ("img2img", "image_to_image"),
        ("inpaint", "inpaint"),
        ("vibe", "generate_image"),
        ("tool", "director_tool"),
        ("upscale", "upscale_image"),
        ("annotate", "annotate_image"),
        ("tags", "suggest_tags"),
        ("account", "get_subscription"),
    ],
)
async def test_full_api_action_dispatches_to_mcp_tool(
    monkeypatch: pytest.MonkeyPatch,
    mock_finish: AsyncMock,
    mock_mcp_client: AsyncMock,
    action: str,
    tool_name: str,
) -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + (3).to_bytes(4) + (5).to_bytes(4)
    segment = UniImage(raw=png)
    args: dict[str, Any] = {
        "action_prompt": ["cat"],
        "image": segment,
        "mask": segment,
        "reference": segment,
        "tool_name": "lineart",
        "tag_prefix": "ca",
        "account_kind": "subscription",
    }

    class Result:
        all_matched_args = args

        def find(self, path: str) -> bool:
            return path == action

    if action in {"tags", "account"}:
        mock_mcp_client.call_tool = AsyncMock(return_value="text result")
    else:
        mock_mcp_client.call_tool = AsyncMock(return_value=png)
    monkeypatch.setattr(
        handler,
        "get_novelai_config",
        lambda: NovelAIConfig(token="token"),
    )

    with pytest.raises(FinishedException):
        await handler.run_novelai_api_action(cast("Any", Result()))

    mock_mcp_client.call_tool.assert_awaited_once()
    assert mock_mcp_client.call_tool.await_args.args[0] == tool_name
    mock_finish.assert_awaited_once()


async def test_uniseg_image_reader_supports_path_and_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + (3).to_bytes(4) + (5).to_bytes(4)
    image_path = Path("image.png")
    config = NovelAIConfig(token="token")
    stream = SimpleNamespace(read=AsyncMock(return_value=png))

    class OpenContext:
        async def __aenter__(self) -> Any:
            return stream

        async def __aexit__(self, *args: object) -> None:
            return None

    open_file = Mock(return_value=OpenContext())
    monkeypatch.setattr(handler.aiofiles, "open", open_file)

    assert (
        await handler._read_uniseg_image(UniImage(path=image_path), config=config)
        == png
    )
    open_file.assert_called_once_with(image_path, "rb")
    stream.read.assert_awaited_once_with(config.image_download_max_bytes + 1)

    download = AsyncMock(return_value=png)
    monkeypatch.setattr(handler, "download_public_http_bytes", download)
    assert (
        await handler._read_uniseg_image(
            UniImage(url="https://example.test/image.png"), config=config
        )
        == png
    )
    download.assert_awaited_once_with(
        "https://example.test/image.png",
        max_bytes=config.image_download_max_bytes,
        request_timeout=config.timeout,
    )
    with pytest.raises(ValueError):
        await handler._read_uniseg_image(UniImage(), config=config)


async def test_full_api_action_maps_validation_failure_to_localized_error(
    monkeypatch: pytest.MonkeyPatch,
    mock_finish: AsyncMock,
    mock_mcp_client: AsyncMock,
) -> None:
    class Result:
        def __init__(self) -> None:
            self.all_matched_args = {"action_prompt": []}

        @staticmethod
        def find(path: str) -> bool:
            return path == "img2img"

    monkeypatch.setattr(
        handler,
        "get_novelai_config",
        lambda: NovelAIConfig(token="token"),
    )

    with pytest.raises(FinishedException):
        await handler.run_novelai_api_action(cast("Any", Result()))

    mock_mcp_client.call_tool.assert_not_awaited()
    mock_finish.assert_awaited_once_with(handler.translate("action_failed"))


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
    mock_mcp_client: AsyncMock,
    overrides: GenerationOverrides,
) -> None:
    analyze = AsyncMock()
    monkeypatch.setattr(handler, "analyze_prompt_intent", analyze)

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(
            ["cat"],
            overrides=overrides,
            config=NovelAIConfig(token="token"),
        )

    analyze.assert_not_awaited()
    mock_mcp_client.call_tool.assert_not_awaited()
    mock_finish.assert_awaited_once_with(handler.translate("parameter_invalid"))


async def test_pipeline_without_search_passes_each_stage_once(
    monkeypatch: pytest.MonkeyPatch,
    intent: PromptIntent,
    plan: NovelAIGenerationPlan,
    mock_finish: AsyncMock,
    mock_mcp_client: AsyncMock,
) -> None:
    analyze = AsyncMock(return_value=intent)
    research = AsyncMock(return_value=VisualResearch((), ()))
    tipo = TipoPrompt("A detailed cat", ("cat", "detailed"))
    expand = AsyncMock(return_value=tipo)
    build = Mock(return_value=plan)
    monkeypatch.setattr(handler, "analyze_prompt_intent", analyze)
    monkeypatch.setattr(handler, "research_visual_facts", research)
    monkeypatch.setattr(handler, "expand_with_tipo", expand)
    monkeypatch.setattr(handler, "build_generation_plan", build)
    mock_mcp_client.call_tool = AsyncMock(return_value=b"image")
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
    mock_mcp_client.call_tool.assert_awaited_once()
    assert mock_mcp_client.call_tool.await_args.args[0] == "generate_image"
    mcp_args = mock_mcp_client.call_tool.await_args.args[1]
    assert mcp_args["prompt"] == plan.prompt
    assert mcp_args["negative_prompt"] == plan.negative_prompt
    assert mcp_args["model"] == config.model
    assert mcp_args["width"] == plan.width
    assert mcp_args["height"] == plan.height
    assert mcp_args["steps"] == plan.steps
    assert mcp_args["scale"] == plan.scale
    assert mcp_args["sampler"] == plan.sampler
    assert mcp_args["seed"] == plan.seed
    assert mcp_args["n_samples"] == config.n_samples
    assert mock_finish.await_args is not None
    assert mock_finish.await_args.args[0].type == "image"


async def test_requested_search_facts_are_passed_to_tipo(
    monkeypatch: pytest.MonkeyPatch,
    mock_mcp_client: AsyncMock,
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
    mock_mcp_client.call_tool = AsyncMock(return_value=b"image")

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(["cat"], config=NovelAIConfig(token="token"))

    research.assert_awaited_once_with(searched_intent)
    assert expand.await_args is not None
    assert expand.await_args.args[0].visual_facts == research_value.facts


async def test_empty_research_still_reaches_tipo(
    monkeypatch: pytest.MonkeyPatch,
    mock_mcp_client: AsyncMock,
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
    mock_mcp_client.call_tool = AsyncMock(return_value=b"image")

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(["cat"], config=NovelAIConfig(token="token"))
    assert expand.await_args is not None
    assert expand.await_args.args[0].visual_facts == ()


async def test_tipo_failure_uses_intent_fallback(
    monkeypatch: pytest.MonkeyPatch,
    mock_mcp_client: AsyncMock,
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
    mock_mcp_client.call_tool = AsyncMock(return_value=b"image")

    config = NovelAIConfig(token="token")
    with pytest.raises(FinishedException):
        await handler.run_novelai_image(["cat"], config=config)

    assert build.call_args.kwargs["tipo_prompt"] is None
    mock_mcp_client.call_tool.assert_awaited_once()
    assert mock_mcp_client.call_tool.await_args.args[0] == "generate_image"


async def test_disabled_tipo_skips_tipo_call(
    monkeypatch: pytest.MonkeyPatch,
    mock_mcp_client: AsyncMock,
    intent: PromptIntent,
    plan: NovelAIGenerationPlan,
) -> None:
    monkeypatch.setattr(
        handler, "analyze_prompt_intent", AsyncMock(return_value=intent)
    )
    expand = AsyncMock()
    monkeypatch.setattr(handler, "expand_with_tipo", expand)
    monkeypatch.setattr(handler, "build_generation_plan", Mock(return_value=plan))
    mock_mcp_client.call_tool = AsyncMock(return_value=b"image")

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(
            ["cat"], config=NovelAIConfig(token="token", tipo_enabled=False)
        )
    expand.assert_not_awaited()
    assert mock_mcp_client.call_tool.await_args.args[0] == "generate_image"


async def test_intent_failure_stops_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    mock_mcp_client: AsyncMock,
) -> None:
    monkeypatch.setattr(
        handler,
        "analyze_prompt_intent",
        AsyncMock(side_effect=IntentAnalysisError("bad")),
    )
    expand = AsyncMock()
    monkeypatch.setattr(handler, "expand_with_tipo", expand)

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(["cat"], config=NovelAIConfig(token="token"))
    expand.assert_not_awaited()
    mock_mcp_client.call_tool.assert_not_awaited()


async def test_parent_llm_failure_returns_localized_prompt_error(
    monkeypatch: pytest.MonkeyPatch,
    mock_finish: AsyncMock,
    mock_mcp_client: AsyncMock,
) -> None:
    monkeypatch.setattr(
        intent_boundary,
        "complete_subplugin_chat_default",
        AsyncMock(side_effect=SubpluginLLMError("provider unavailable")),
    )
    monkeypatch.setattr(
        handler, "analyze_prompt_intent", intent_boundary.analyze_prompt_intent
    )

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(["cat"], config=NovelAIConfig(token="token"))

    mock_finish.assert_awaited_once_with(handler.translate("prompt_failed"))
    mock_mcp_client.call_tool.assert_not_awaited()


@pytest.mark.parametrize(
    "error",
    [ValueError("bad"), OSError("io"), RuntimeError("runtime"), Exception("generic")],
)
async def test_generation_errors_are_localized(
    monkeypatch: pytest.MonkeyPatch,
    mock_finish: AsyncMock,
    mock_mcp_client: AsyncMock,
    intent: PromptIntent,
    plan: NovelAIGenerationPlan,
    error: Exception,
) -> None:
    monkeypatch.setattr(
        handler, "analyze_prompt_intent", AsyncMock(return_value=intent)
    )
    monkeypatch.setattr(handler, "expand_with_tipo", AsyncMock(return_value=None))
    monkeypatch.setattr(handler, "build_generation_plan", Mock(return_value=plan))
    mock_mcp_client.call_tool = AsyncMock(side_effect=error)

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(["cat"], config=NovelAIConfig(token="token"))
    mock_finish.assert_awaited_once_with(handler.translate("generation_failed"))


def test_b64_encodes_bytes_as_ascii_base64() -> None:
    assert handler._b64(b"test") == "dGVzdA=="
    assert handler._b64(b"") == ""


def test_plan_to_mcp_args_maps_plan_fields() -> None:
    plan = NovelAIGenerationPlan(
        prompt="portrait",
        negative_prompt="text",
        width=832,
        height=1216,
        steps=28,
        scale=5.0,
        sampler="k_euler_ancestral",
        seed=7,
        base_caption="portrait",
        char_captions=(),
        character_prompts=(),
        use_coords=False,
    )
    config = NovelAIConfig()

    args = handler._plan_to_mcp_args(plan, config=config)

    assert args["prompt"] == "portrait"
    assert args["negative_prompt"] == "text"
    assert args["model"] == config.model
    assert args["width"] == 832
    assert args["height"] == 1216
    assert args["steps"] == 28
    assert args["scale"] == 5.0
    assert args["sampler"] == "k_euler_ancestral"
    assert args["seed"] == 7
    assert args["n_samples"] == config.n_samples
    assert args["quality"] == config.quality
    assert args["uc_preset"] == config.uc_preset
    assert args["noise_schedule"] == config.noise_schedule
    assert args["cfg_rescale"] == config.cfg_rescale
    assert "character_prompts" not in args


def test_plan_to_mcp_args_includes_character_prompts() -> None:
    character_prompt: dict[str, object] = {
        "prompt": "blue hair",
        "uc": "bad hands",
        "center": {"x": 0.5, "y": 0.5},
        "enabled": True,
    }
    plan = NovelAIGenerationPlan(
        prompt="portrait",
        negative_prompt="text",
        width=832,
        height=1216,
        steps=28,
        scale=5.0,
        sampler="k_euler_ancestral",
        seed=7,
        base_caption="portrait",
        char_captions=(),
        character_prompts=(character_prompt,),
        use_coords=True,
    )

    args = handler._plan_to_mcp_args(plan, config=NovelAIConfig())

    assert args["character_prompts"] == [character_prompt]
