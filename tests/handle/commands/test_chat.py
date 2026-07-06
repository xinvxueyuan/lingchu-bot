"""测试聊天命令 - LLM 对话功能"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    chat as chat_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.chat import chat_cmd
from src.plugins.nonebot_plugin_lingchu_bot.services.llm import LLMProviderError


def finish_text(mock_finish: MagicMock) -> str:
    """返回 matcher.finish 收到的 message 参数文本。"""
    call_args = mock_finish.call_args
    if call_args is None:
        return ""
    if "message" in call_args.kwargs:
        return str(call_args.kwargs["message"])
    if call_args.args:
        return str(call_args.args[0])
    return ""


def _make_config(
    *, enabled: bool = True, system_prompt: str = "你是一个友好的群聊助手。"
) -> MagicMock:
    """创建模拟的 handle config。"""
    config = MagicMock()
    config.enabled = enabled
    config.defaults = {"system_prompt": system_prompt}
    return config


def _mock_config_manager(config: MagicMock) -> MagicMock:
    manager = MagicMock()
    manager.get_config = AsyncMock(return_value=config)
    return manager


class TestOneBot11Chat:
    """OneBot11 聊天命令测试。"""

    @pytest.mark.asyncio
    async def test_chat_success(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
    ) -> None:
        """测试聊天成功路径：LLM 返回文本，finish 收到响应。"""
        config = _make_config()
        with (
            patch.object(
                chat_module,
                "complete_chat",
                new=AsyncMock(return_value="你好！有什么可以帮你的吗？"),
            ) as mock_complete,
            patch.object(
                chat_module,
                "get_handle_config_manager",
                return_value=_mock_config_manager(config),
            ),
            patch.object(chat_cmd, "finish", new=AsyncMock()) as mock_finish,
        ):
            await chat_module.onebot11_chat(
                text=["你好"],
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
            )

        mock_complete.assert_awaited_once()
        assert finish_text(mock_finish) == "你好！有什么可以帮你的吗？"

    @pytest.mark.asyncio
    async def test_chat_llm_error(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
    ) -> None:
        """测试 LLM 错误路径：complete_chat 抛 LLMError，finish 收到错误消息。"""
        config = _make_config()
        with (
            patch.object(
                chat_module,
                "complete_chat",
                new=AsyncMock(side_effect=LLMProviderError()),
            ),
            patch.object(
                chat_module,
                "get_handle_config_manager",
                return_value=_mock_config_manager(config),
            ),
            patch.object(chat_cmd, "finish", new=AsyncMock()) as mock_finish,
        ):
            await chat_module.onebot11_chat(
                text=["你好"],
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
            )

        assert finish_text(mock_finish) == "LLM 服务暂时不可用，请稍后再试"

    @pytest.mark.asyncio
    async def test_chat_disabled(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
    ) -> None:
        """测试功能禁用路径：config.enabled=False，finish 收到禁用消息。"""
        config = _make_config(enabled=False)
        with (
            patch.object(
                chat_module, "complete_chat", new=AsyncMock()
            ) as mock_complete,
            patch.object(
                chat_module,
                "get_handle_config_manager",
                return_value=_mock_config_manager(config),
            ),
            patch.object(chat_cmd, "finish", new=AsyncMock()) as mock_finish,
        ):
            await chat_module.onebot11_chat(
                text=["你好"],
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
            )

        mock_complete.assert_not_awaited()
        assert finish_text(mock_finish) == "该功能已禁用"

    @pytest.mark.asyncio
    async def test_chat_system_prompt(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
    ) -> None:
        """测试 system_prompt 传递：complete_chat 收到含 system message 的 messages。"""
        config = _make_config(system_prompt="你是一个毒舌助手")
        with (
            patch.object(
                chat_module,
                "complete_chat",
                new=AsyncMock(return_value="ok"),
            ) as mock_complete,
            patch.object(
                chat_module,
                "get_handle_config_manager",
                return_value=_mock_config_manager(config),
            ),
            patch.object(chat_cmd, "finish", new=AsyncMock()),
        ):
            await chat_module.onebot11_chat(
                text=["你好", "世界"],
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
            )

        call_kwargs = mock_complete.call_args
        messages = (
            call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs["messages"]
        )
        assert messages[0] == {"role": "system", "content": "你是一个毒舌助手"}
        assert messages[1] == {"role": "user", "content": "你好 世界"}
