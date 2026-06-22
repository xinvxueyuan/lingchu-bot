"""
测试禁言命令 - 边界行为覆盖
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot_plugin_alconna.uniseg import At

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    mute as mute_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.mute import (
    member_mute_cmd,
    member_unmute_cmd,
    onebot11_mute,
    onebot11_unmute,
    onebot11_whole_mute,
    onebot11_whole_unmute,
    whole_mute_cmd,
    whole_unmute_cmd,
)


def finish_message(mock_finish: MagicMock) -> object:
    """返回 matcher.finish 收到的 message 参数。"""
    if mock_finish.call_args:
        if "message" in mock_finish.call_args.kwargs:
            return mock_finish.call_args.kwargs["message"]
        if mock_finish.call_args.args:
            return mock_finish.call_args.args[0]
    return ""


def finish_text(mock_finish: MagicMock) -> str:
    """返回 matcher.finish 收到的 message 参数文本。"""
    return str(finish_message(mock_finish))


@pytest.fixture
def mock_at() -> MagicMock:
    """创建模拟的 @ 提及对象。"""
    at = MagicMock(spec=At)
    at.target = "987654321"
    at.display = "测试用户"
    return at


class TestOneBot11Mute:
    """OneBot11 禁言 API 映射测试。"""

    @pytest.fixture(autouse=True)
    def _mock_record_audit_fire_and_forget(self):
        """避免审计记录触发后台任务和数据库调用。"""
        with patch.object(mute_module, "record_audit_fire_and_forget", new=AsyncMock()):
            yield

    @pytest.mark.asyncio
    async def test_onebot11_mute_calls_set_group_ban(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_at: MagicMock,
    ) -> None:
        mock_onebot11_bot.set_group_ban = AsyncMock()
        # check_target_privilege: 目标为普通成员（通过）
        # check_bot_privilege: 机器人为管理员（通过）
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            side_effect=[{"role": "member"}, {"role": "admin"}]
        )

        with patch.object(member_mute_cmd, "finish") as mock_finish:
            await onebot11_mute(
                user=mock_at,
                duration=300,
                reason="违规",
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
            )

        mock_onebot11_bot.set_group_ban.assert_called_once_with(
            group_id=mock_onebot11_event.group_id,
            user_id=987654321,
            duration=300,
        )
        assert "已禁言:" in finish_text(mock_finish)
        assert "名称: @测试用户" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_onebot11_unmute_calls_set_group_ban_duration_zero(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_at: MagicMock,
    ) -> None:
        mock_onebot11_bot.set_group_ban = AsyncMock()

        with patch.object(member_unmute_cmd, "finish") as mock_finish:
            await onebot11_unmute(
                user=mock_at, bot=mock_onebot11_bot, event=mock_onebot11_event
            )

        mock_onebot11_bot.set_group_ban.assert_called_once_with(
            group_id=mock_onebot11_event.group_id,
            user_id=987654321,
            duration=0,
        )
        assert "已解禁:" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_onebot11_whole_mute_calls_set_group_whole_ban(
        self, mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
    ) -> None:
        mock_onebot11_bot.set_group_whole_ban = AsyncMock()
        # check_bot_privilege: 机器人为管理员（通过）
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            return_value={"role": "admin"}
        )

        with patch.object(whole_mute_cmd, "finish") as mock_finish:
            await onebot11_whole_mute(bot=mock_onebot11_bot, event=mock_onebot11_event)

        mock_onebot11_bot.set_group_whole_ban.assert_called_once_with(
            group_id=mock_onebot11_event.group_id, enable=True
        )
        assert finish_text(mock_finish) == "全体禁言成功"

    @pytest.mark.asyncio
    async def test_onebot11_whole_unmute_calls_set_group_whole_ban(
        self, mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
    ) -> None:
        mock_onebot11_bot.set_group_whole_ban = AsyncMock()

        with patch.object(whole_unmute_cmd, "finish") as mock_finish:
            await onebot11_whole_unmute(
                bot=mock_onebot11_bot, event=mock_onebot11_event
            )

        mock_onebot11_bot.set_group_whole_ban.assert_called_once_with(
            group_id=mock_onebot11_event.group_id, enable=False
        )
        assert finish_text(mock_finish) == "全体解禁成功"
