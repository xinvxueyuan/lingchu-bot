"""
测试群生命周期命令 - OneBot11 群 API 映射覆盖
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.lifecycle import (
    onebot11_quit_group,
    onebot11_restart_protocol_endpoint,
    quit_group_cmd,
    restart_protocol_endpoint_cmd,
)
from src.plugins.nonebot_plugin_lingchu_bot.services import protocol_restart_feedback
from tests.handle.commands.conftest import finish_text


@pytest.fixture(autouse=True)
def clear_restart_feedback() -> None:
    protocol_restart_feedback.clear_pending_restart_feedback()


@pytest.mark.asyncio
async def test_onebot11_quit_group_calls_set_group_leave(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
) -> None:
    mock_onebot11_bot.set_group_leave = AsyncMock()

    with patch.object(quit_group_cmd, "finish") as mock_finish:
        await onebot11_quit_group(bot=mock_onebot11_bot, event=mock_onebot11_event)

    mock_onebot11_bot.set_group_leave.assert_called_once_with(
        group_id=mock_onebot11_event.group_id, is_dismiss=False
    )
    assert finish_text(mock_finish) == "退出当前群"


@pytest.mark.asyncio
async def test_onebot11_restart_protocol_endpoint_calls_set_restart(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
) -> None:
    mock_onebot11_bot.self_id = "12345"
    mock_onebot11_bot.call_api = AsyncMock(return_value={})

    with (
        patch.object(restart_protocol_endpoint_cmd, "finish") as mock_finish,
        patch.object(
            restart_protocol_endpoint_cmd, "send", new_callable=AsyncMock
        ) as mock_send,
    ):
        await onebot11_restart_protocol_endpoint(
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            platform=None,
        )

    mock_send.assert_awaited_once_with("已请求重启协议端，重新连接后会发送反馈")
    mock_onebot11_bot.call_api.assert_awaited_once_with("set_restart")
    mock_finish.assert_not_called()
    pending = protocol_restart_feedback.list_pending_restart_feedback()
    assert len(pending) == 1
    assert pending[0].conversation_id == str(mock_onebot11_event.group_id)


@pytest.mark.asyncio
async def test_onebot11_restart_protocol_endpoint_does_not_restart_when_send_fails(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
) -> None:
    mock_onebot11_bot.self_id = "12345"
    mock_onebot11_bot.call_api = AsyncMock(return_value={})

    with (
        patch.object(
            restart_protocol_endpoint_cmd,
            "send",
            new_callable=AsyncMock,
            side_effect=RuntimeError("send failed"),
        ),
        pytest.raises(RuntimeError, match="send failed"),
    ):
        await onebot11_restart_protocol_endpoint(
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            platform=None,
        )

    mock_onebot11_bot.call_api.assert_not_called()
    assert protocol_restart_feedback.list_pending_restart_feedback() == ()


@pytest.mark.asyncio
async def test_onebot11_restart_protocol_endpoint_accepts_current_platform_alias(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
) -> None:
    mock_onebot11_bot.self_id = "12345"
    mock_onebot11_bot.call_api = AsyncMock(return_value={})

    with (
        patch.object(restart_protocol_endpoint_cmd, "finish"),
        patch.object(restart_protocol_endpoint_cmd, "send", new_callable=AsyncMock),
    ):
        await onebot11_restart_protocol_endpoint(
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            platform="当前平台",
        )

    mock_onebot11_bot.call_api.assert_awaited_once_with("set_restart")


@pytest.mark.asyncio
async def test_onebot11_restart_protocol_endpoint_rejects_other_platform(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
) -> None:
    mock_onebot11_bot.call_api = AsyncMock()

    with (
        patch.object(restart_protocol_endpoint_cmd, "finish") as mock_finish,
        patch.object(restart_protocol_endpoint_cmd, "send", new_callable=AsyncMock),
    ):
        await onebot11_restart_protocol_endpoint(
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            platform="telegram",
        )

    mock_onebot11_bot.call_api.assert_not_called()
    assert finish_text(mock_finish) == "当前仅支持重启当前 QQ OneBot V11 协议端"


@pytest.mark.asyncio
async def test_onebot11_restart_protocol_endpoint_reports_action_failed(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
) -> None:
    mock_onebot11_bot.self_id = "12345"
    mock_onebot11_bot.call_api = AsyncMock(side_effect=OneBot11ActionFailed())

    with (
        patch.object(restart_protocol_endpoint_cmd, "finish") as mock_finish,
        patch.object(restart_protocol_endpoint_cmd, "send", new_callable=AsyncMock),
    ):
        await onebot11_restart_protocol_endpoint(
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            platform=None,
        )

    assert finish_text(mock_finish) == "重启协议端失败，操作被拒绝"
    assert protocol_restart_feedback.list_pending_restart_feedback() == ()


@pytest.mark.asyncio
async def test_onebot11_restart_protocol_endpoint_failed_bot_keeps_other_pending(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
) -> None:
    protocol_restart_feedback.register_pending_restart_feedback(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="bot-a",
        conversation_type="group",
        conversation_id="10001",
    )
    mock_onebot11_bot.self_id = "bot-b"
    mock_onebot11_bot.call_api = AsyncMock(side_effect=OneBot11ActionFailed())

    with (
        patch.object(restart_protocol_endpoint_cmd, "finish"),
        patch.object(restart_protocol_endpoint_cmd, "send", new_callable=AsyncMock),
    ):
        await onebot11_restart_protocol_endpoint(
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            platform=None,
        )

    pending = protocol_restart_feedback.list_pending_restart_feedback()
    assert len(pending) == 1
    assert pending[0].bot_id == "bot-a"
    assert pending[0].conversation_id == "10001"
