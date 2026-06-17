"""
测试禁言命令 - 边界行为覆盖
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.milky.exception import ActionFailed, NetworkError
from nonebot_plugin_alconna import UniMessage
from nonebot_plugin_alconna.uniseg import At

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.group.mute import (
    member_mute_cmd,
    member_unmute_cmd,
    milkybot_mute,
    milkybot_unmute,
    milkybot_whole_mute,
    milkybot_whole_unmute,
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
def mock_bot() -> MagicMock:
    """创建模拟的 Bot 对象。"""
    bot = MagicMock(spec=MilkyBot)
    bot.adapter = MagicMock()
    bot.adapter.get_name.return_value = "Milky"
    bot.self_id = "bot-1"
    bot.set_group_member_mute = AsyncMock()
    bot.set_group_whole_mute = AsyncMock()
    bot.get_group_member_info = AsyncMock(return_value=MagicMock(card="", nickname=""))
    return bot


@pytest.fixture
def mock_event() -> MagicMock:
    """创建模拟的群消息事件。"""
    event = MagicMock(spec=MilkyGroupMessageEvent)
    event.data = MagicMock()
    event.data.peer_id = 123456789
    event.data.sender = MagicMock()
    event.data.sender.user_id = 111111
    event.data.segments = []
    return event


@pytest.fixture
def mock_at() -> MagicMock:
    """创建模拟的 @ 提及对象。"""
    at = MagicMock(spec=At)
    at.target = "987654321"
    at.display = "测试用户"
    return at


# ================= 全体禁言测试 =================


class TestWholeMute:
    """全体禁言功能测试。"""

    @pytest.mark.asyncio
    async def test_whole_mute_enable(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试开启全体禁言。"""
        with patch.object(whole_mute_cmd, "finish") as mock_finish:
            await milkybot_whole_mute(bot=mock_bot, event=mock_event)

        mock_bot.set_group_whole_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id, is_mute=True
        )
        assert finish_text(mock_finish) == "全体禁言成功"

    @pytest.mark.asyncio
    async def test_whole_mute_api_error(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体禁言未捕获的 API 调用失败。"""
        mock_bot.set_group_whole_mute.side_effect = Exception("API 调用失败")

        with pytest.raises(Exception, match="API 调用失败"):
            await milkybot_whole_mute(bot=mock_bot, event=mock_event)

    @pytest.mark.asyncio
    async def test_whole_mute_network_error(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体禁言网络异常返回错误消息。"""
        mock_bot.set_group_whole_mute.side_effect = NetworkError("连接失败")

        with patch.object(whole_mute_cmd, "finish") as mock_finish:
            await milkybot_whole_mute(bot=mock_bot, event=mock_event)

        assert "全体禁言失败，网络异常" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_whole_mute_action_failed(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体禁言操作被拒绝返回错误消息。"""
        mock_bot.set_group_whole_mute.side_effect = ActionFailed(message="权限不足")

        with patch.object(whole_mute_cmd, "finish") as mock_finish:
            await milkybot_whole_mute(bot=mock_bot, event=mock_event)

        assert "全体禁言失败，操作被拒绝" in finish_text(mock_finish)


# ================= 禁言用户测试 =================


class TestMute:
    """禁言用户功能测试。"""

    @pytest.mark.asyncio
    async def test_mute_uses_at_target(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试从 At.target 获取禁言用户。"""
        with patch.object(member_mute_cmd, "finish") as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=60,
                reason="测试",
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id,
            user_id=987654321,
            duration=60,
        )
        result_message = finish_message(mock_finish)
        assert isinstance(result_message, UniMessage)
        assert "已禁言:" in str(result_message)
        assert "名称: @测试用户" in str(result_message)
        assert "时长: 60 秒" in str(result_message)
        assert "原因: 测试" in str(result_message)
        assert "标识: 987654321" in str(result_message)

    @pytest.mark.asyncio
    async def test_mute_matches_mention_segment_by_at_target(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试存在多个 mention 消息段时按 At.target 匹配目标。"""
        mock_at.target = "333333"
        mock_at.display = None
        mock_event.data.segments = [
            {"type": "text", "data": {"text": "前缀"}},
            {"type": "mention", "data": {"user_id": 222222, "name": "第一用户"}},
            {"type": "mention", "data": {"user_id": 333333, "name": "第二用户"}},
        ]

        with patch.object(member_mute_cmd, "finish") as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=300,
                reason="违规",
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id,
            user_id=333333,
            duration=300,
        )
        result_message = finish_text(mock_finish)
        assert "名称: @第二用户" in result_message
        assert "标识: 333333" in result_message
        assert "第一用户" not in result_message

    @pytest.mark.asyncio
    async def test_mute_ignores_non_mention_segments(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试非 mention 消息段会被忽略。"""
        mock_event.data.segments = [
            {"type": "text", "data": {"text": "@不是mention"}},
            {"type": "image", "data": {"url": "https://example.invalid/a.png"}},
        ]

        with patch.object(member_mute_cmd, "finish") as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=120,
                reason="测试",
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id,
            user_id=987654321,
            duration=120,
        )
        assert "名称: @测试用户" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_mute_allows_targeting_sender(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试目标用户是发送者本人时返回不能禁言自己。"""
        mock_event.data.sender.user_id = 987654321

        with patch.object(member_mute_cmd, "finish") as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=60,
                reason="测试",
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_not_called()
        assert "不能禁言自己" in finish_text(mock_finish)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("duration", [1, 30, 2592000])
    async def test_mute_passes_duration_through(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_at: MagicMock,
        duration: int,
    ) -> None:
        """测试禁言时长边界值原样传给 API。"""
        with patch.object(member_mute_cmd, "finish") as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=duration,
                reason="边界时长",
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id,
            user_id=987654321,
            duration=duration,
        )
        assert f"时长: {duration} 秒" in finish_text(mock_finish)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("reason", ["", "  空白 原因\n第二行 !@#  "])
    async def test_mute_passes_reason_through(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_at: MagicMock,
        reason: str,
    ) -> None:
        """测试禁言原因原样写入成功消息。"""
        with patch.object(member_mute_cmd, "finish") as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=60,
                reason=reason,
                bot=mock_bot,
                event=mock_event,
            )

        assert f"原因: {reason}" in finish_text(mock_finish)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("display", ["", None])
    async def test_mute_empty_display_uses_user_id_as_name(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_at: MagicMock,
        display: str | None,
    ) -> None:
        """测试 At.display 为空时名称回退为用户 ID。"""
        mock_at.display = display

        with patch.object(member_mute_cmd, "finish") as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=60,
                reason="测试",
                bot=mock_bot,
                event=mock_event,
            )

        assert "名称: 987654321\n" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_mute_invalid_at_target_finishes_with_error(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试 At.target 非数字时结束匹配器且不调用 API。"""
        mock_at.target = "not-a-number"

        with patch.object(member_mute_cmd, "finish") as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=60,
                reason="测试",
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_not_called()
        assert "无效的用户 ID: 'not-a-number'" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_mute_converts_matching_mention_target_to_int(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试匹配的 mention 目标按 At.target 安全转换为 int。"""
        mock_at.target = "222222"
        mock_at.display = ""
        mock_event.data.segments = [
            {"type": "mention", "data": {"user_id": "222222", "name": "字符串ID"}}
        ]

        with patch.object(member_mute_cmd, "finish") as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=60,
                reason="测试",
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id,
            user_id=222222,
            duration=60,
        )
        assert "标识: 222222" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_mute_api_error(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试禁言未捕获的 API 调用失败。"""
        mock_bot.set_group_member_mute.side_effect = Exception("API 调用失败")

        with pytest.raises(Exception, match="API 调用失败"):
            await milkybot_mute(
                user=mock_at,
                duration=60,
                reason="测试",
                bot=mock_bot,
                event=mock_event,
            )

    @pytest.mark.asyncio
    async def test_mute_network_error(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试禁言网络异常返回错误消息。"""
        mock_bot.set_group_member_mute.side_effect = NetworkError("连接失败")

        with patch.object(member_mute_cmd, "finish") as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=60,
                reason="测试",
                bot=mock_bot,
                event=mock_event,
            )

        assert "禁言失败，网络异常" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_mute_action_failed(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试禁言操作被拒绝返回错误消息。"""
        mock_bot.set_group_member_mute.side_effect = ActionFailed(message="权限不足")

        with patch.object(member_mute_cmd, "finish") as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=60,
                reason="测试",
                bot=mock_bot,
                event=mock_event,
            )

        assert "禁言失败，操作被拒绝" in finish_text(mock_finish)


# ================= 解禁用户测试 =================


class TestUnmute:
    """解禁用户功能测试。"""

    @pytest.mark.asyncio
    async def test_unmute_basic(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试基本解禁功能。"""
        with patch.object(member_unmute_cmd, "finish") as mock_finish:
            await milkybot_unmute(user=mock_at, bot=mock_bot, event=mock_event)

        mock_bot.set_group_member_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id,
            user_id=987654321,
            duration=0,
        )
        result_message = finish_message(mock_finish)
        assert isinstance(result_message, UniMessage)
        assert "已解禁:" in str(result_message)
        assert "名称: @测试用户" in str(result_message)
        assert "原因: 管理员操作「默认」" in str(result_message)
        assert "标识: 987654321" in str(result_message)

    @pytest.mark.asyncio
    async def test_unmute_matches_mention_segment_by_at_target(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试存在多个 mention 消息段时按 At.target 解禁目标。"""
        mock_at.target = "444444"
        mock_at.display = None
        mock_event.data.segments = [
            {"type": "mention", "data": {"user_id": 333333, "name": "第一用户"}},
            {"type": "mention", "data": {"user_id": 444444, "name": "第二用户"}},
        ]

        with patch.object(member_unmute_cmd, "finish") as mock_finish:
            await milkybot_unmute(user=mock_at, bot=mock_bot, event=mock_event)

        mock_bot.set_group_member_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id,
            user_id=444444,
            duration=0,
        )
        result_message = finish_text(mock_finish)
        assert "名称: @第二用户" in result_message
        assert "第一用户" not in result_message

    @pytest.mark.asyncio
    async def test_unmute_ignores_non_mention_segments(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试解禁时非 mention 消息段会被忽略。"""
        mock_event.data.segments = [{"type": "text", "data": {"text": "hello"}}]

        with patch.object(member_unmute_cmd, "finish") as mock_finish:
            await milkybot_unmute(user=mock_at, bot=mock_bot, event=mock_event)

        mock_bot.set_group_member_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id,
            user_id=987654321,
            duration=0,
        )
        assert "名称: @测试用户" in finish_text(mock_finish)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("display", ["", None])
    async def test_unmute_empty_display_uses_user_id_as_name(
        self,
        mock_bot: MagicMock,
        mock_event: MagicMock,
        mock_at: MagicMock,
        display: str | None,
    ) -> None:
        """测试解禁时 At.display 为空会使用用户 ID 作为名称。"""
        mock_at.display = display

        with patch.object(member_unmute_cmd, "finish") as mock_finish:
            await milkybot_unmute(user=mock_at, bot=mock_bot, event=mock_event)

        assert "名称: 987654321\n" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_unmute_invalid_at_target_finishes_with_error(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试解禁 At.target 非数字时结束匹配器且不调用 API。"""
        mock_at.target = "not-a-number"

        with patch.object(member_unmute_cmd, "finish") as mock_finish:
            await milkybot_unmute(user=mock_at, bot=mock_bot, event=mock_event)

        mock_bot.set_group_member_mute.assert_not_called()
        assert "无效的用户 ID: 'not-a-number'" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_unmute_api_error(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试解禁未捕获的 API 调用失败。"""
        mock_bot.set_group_member_mute.side_effect = Exception("API 调用失败")

        with pytest.raises(Exception, match="API 调用失败"):
            await milkybot_unmute(user=mock_at, bot=mock_bot, event=mock_event)

    @pytest.mark.asyncio
    async def test_unmute_network_error(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试解禁网络异常返回错误消息。"""
        mock_bot.set_group_member_mute.side_effect = NetworkError("连接失败")

        with patch.object(member_unmute_cmd, "finish") as mock_finish:
            await milkybot_unmute(user=mock_at, bot=mock_bot, event=mock_event)

        assert "解禁失败，网络异常" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_unmute_action_failed(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试解禁操作被拒绝返回错误消息。"""
        mock_bot.set_group_member_mute.side_effect = ActionFailed(message="权限不足")

        with patch.object(member_unmute_cmd, "finish") as mock_finish:
            await milkybot_unmute(user=mock_at, bot=mock_bot, event=mock_event)

        assert "解禁失败，操作被拒绝" in finish_text(mock_finish)


# ================= 全体解禁测试 =================


class TestWholeUnmute:
    """全体解禁功能测试。"""

    @pytest.mark.asyncio
    async def test_whole_unmute_disable(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试关闭全体禁言（解禁）。"""
        with patch.object(whole_unmute_cmd, "finish") as mock_finish:
            await milkybot_whole_unmute(bot=mock_bot, event=mock_event)

        mock_bot.set_group_whole_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id, is_mute=False
        )
        assert finish_text(mock_finish) == "全体解禁成功"

    @pytest.mark.asyncio
    async def test_whole_unmute_api_error(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体解禁未捕获的 API 调用失败。"""
        mock_bot.set_group_whole_mute.side_effect = Exception("API 调用失败")

        with pytest.raises(Exception, match="API 调用失败"):
            await milkybot_whole_unmute(bot=mock_bot, event=mock_event)

    @pytest.mark.asyncio
    async def test_whole_unmute_network_error(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体解禁网络异常返回错误消息。"""
        mock_bot.set_group_whole_mute.side_effect = NetworkError("连接失败")

        with patch.object(whole_unmute_cmd, "finish") as mock_finish:
            await milkybot_whole_unmute(bot=mock_bot, event=mock_event)

        assert "全体解禁失败，网络异常" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_whole_unmute_action_failed(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体解禁操作被拒绝返回错误消息。"""
        mock_bot.set_group_whole_mute.side_effect = ActionFailed(message="权限不足")

        with patch.object(whole_unmute_cmd, "finish") as mock_finish:
            await milkybot_whole_unmute(bot=mock_bot, event=mock_event)

        assert "全体解禁失败，操作被拒绝" in finish_text(mock_finish)


# ================= 集成场景测试 =================


class TestIntegrationScenarios:
    """集成场景测试。"""

    @pytest.mark.asyncio
    async def test_mute_then_unmute_sequential(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试先禁言后解禁的顺序操作。"""
        with patch.object(member_mute_cmd, "finish"):
            await milkybot_mute(
                user=mock_at,
                duration=600,
                reason="测试禁言",
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_called_with(
            group_id=mock_event.data.peer_id,
            user_id=987654321,
            duration=600,
        )

        with patch.object(member_unmute_cmd, "finish"):
            await milkybot_unmute(user=mock_at, bot=mock_bot, event=mock_event)

        mock_bot.set_group_member_mute.assert_called_with(
            group_id=mock_event.data.peer_id,
            user_id=987654321,
            duration=0,
        )

    @pytest.mark.asyncio
    async def test_multiple_operations_different_groups(
        self, mock_bot: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试不同群组的操作。"""
        group_ids = [111111, 222222, 333333]

        for group_id in group_ids:
            event = MagicMock(spec=MilkyGroupMessageEvent)
            event.data = MagicMock()
            event.data.peer_id = group_id
            event.data.sender = MagicMock()
            event.data.sender.user_id = 111111
            event.data.segments = []

            with patch.object(member_mute_cmd, "finish"):
                await milkybot_mute(
                    user=mock_at,
                    duration=300,
                    reason=f"群组{group_id}测试",
                    bot=mock_bot,
                    event=event,
                )

            mock_bot.set_group_member_mute.assert_called_with(
                group_id=group_id,
                user_id=987654321,
                duration=300,
            )


# ================= UniMessage 测试 =================


class TestUniMessage:
    """UniMessage 消息格式测试。"""

    @pytest.mark.asyncio
    async def test_mute_message_is_uni_message_instance(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试禁言返回的消息是 UniMessage 实例。"""
        with patch.object(member_mute_cmd, "finish") as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=60,
                reason="测试",
                bot=mock_bot,
                event=mock_event,
            )

        assert isinstance(finish_message(mock_finish), UniMessage)

    @pytest.mark.asyncio
    async def test_unmute_message_is_uni_message_instance(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试解禁返回的消息是 UniMessage 实例。"""
        with patch.object(member_unmute_cmd, "finish") as mock_finish:
            await milkybot_unmute(user=mock_at, bot=mock_bot, event=mock_event)

        assert isinstance(finish_message(mock_finish), UniMessage)

    @pytest.mark.asyncio
    async def test_whole_mute_message_format(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体禁言导出后的消息格式。"""
        with patch.object(whole_mute_cmd, "finish") as mock_finish:
            await milkybot_whole_mute(bot=mock_bot, event=mock_event)

        assert finish_text(mock_finish) == "全体禁言成功"

    @pytest.mark.asyncio
    async def test_whole_unmute_message_format(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体解禁导出后的消息格式。"""
        with patch.object(whole_unmute_cmd, "finish") as mock_finish:
            await milkybot_whole_unmute(bot=mock_bot, event=mock_event)

        assert finish_text(mock_finish) == "全体解禁成功"


class TestOneBot11Mute:
    """OneBot11 禁言 API 映射测试。"""

    @pytest.mark.asyncio
    async def test_onebot11_mute_calls_set_group_ban(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_at: MagicMock,
    ) -> None:
        mock_onebot11_bot.set_group_ban = AsyncMock()

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
