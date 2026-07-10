from unittest.mock import AsyncMock

import pytest
from nonebot.exception import FinishedException

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image import (
    handler,
    i18n,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client import (
    MissingNovelAITokenError,
    NovelAIProviderError,
    NovelAITransportError,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.config import (
    NovelAIConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.prompt import (
    ConvertedPrompt,
    PromptConversionError,
)


@pytest.fixture(autouse=True)
def mock_finish(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    finish = AsyncMock(side_effect=FinishedException)
    monkeypatch.setattr(handler.novelai_image_cmd, "finish", finish)
    return finish


def test_command_trigger_is_locale_exclusive() -> None:
    assert handler.command_for_locale("zh_CN") == "生图"
    assert handler.command_for_locale("en_US") == "novelai-image"


def test_child_messages_follow_configured_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(i18n, "get_configured_locale", lambda: "zh_CN")
    assert i18n.translate("empty") == "生图描述不能为空"

    monkeypatch.setattr(i18n, "get_configured_locale", lambda: "en_US")
    assert i18n.translate("empty") == "The image description cannot be empty"


async def test_empty_prompt_never_calls_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    convert = AsyncMock()
    monkeypatch.setattr(handler, "convert_prompt", convert)

    with pytest.raises(FinishedException):
        await handler.run_novelai_image([], config=NovelAIConfig())

    convert.assert_not_awaited()


async def test_conversion_failure_never_calls_novelai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        handler,
        "convert_prompt",
        AsyncMock(side_effect=PromptConversionError("bad")),
    )
    generate = AsyncMock()
    monkeypatch.setattr(handler, "generate_image", generate)

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(["画猫"], config=NovelAIConfig())

    generate.assert_not_awaited()


async def test_success_sends_image(
    monkeypatch: pytest.MonkeyPatch,
    mock_finish: AsyncMock,
) -> None:
    monkeypatch.setattr(
        handler,
        "convert_prompt",
        AsyncMock(
            return_value=ConvertedPrompt("A cat", ("cat",), ("text",)),
        ),
    )
    generate = AsyncMock(return_value=b"image")
    monkeypatch.setattr(handler, "generate_image", generate)

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(
            ["画猫"],
            config=NovelAIConfig(token="token"),
        )

    generate.assert_awaited_once()
    assert mock_finish.await_args is not None
    assert mock_finish.await_args.args[0].type == "image"


@pytest.mark.parametrize(
    "error,message_key",
    [
        (MissingNovelAITokenError(), "token_missing"),
        (NovelAIProviderError(), "generation_failed"),
        (NovelAITransportError(), "generation_failed"),
    ],
)
async def test_generation_errors_are_localized(
    monkeypatch: pytest.MonkeyPatch,
    mock_finish: AsyncMock,
    error: Exception,
    message_key: str,
) -> None:
    monkeypatch.setattr(
        handler,
        "convert_prompt",
        AsyncMock(return_value=ConvertedPrompt("A cat", ("cat",), ("text",))),
    )
    monkeypatch.setattr(handler, "generate_image", AsyncMock(side_effect=error))

    with pytest.raises(FinishedException):
        await handler.run_novelai_image(
            ["画猫"],
            config=NovelAIConfig(token="token"),
        )

    assert mock_finish.await_args is not None
    assert mock_finish.await_args.args[0] == handler.translate(message_key)
