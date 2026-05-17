"""
测试禁言命令 - 补充测试
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.milky.exception import ActionFailed, NetworkError
from nonebot_plugin_alconna import UniMessage
from nonebot_plugin_alconna.uniseg import At

from src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute import (
    milkybot_mute,
    milkybot_unmute,
    milkybot_whole_mute,
    milkybot_whole_unmute,
)


@pytest.fixture
def mock_bot() -> MagicMock:
    """创建模拟的 Bot 对象"""
    bot = MagicMock(spec=MilkyBot)
    bot.set_group_member_mute = AsyncMock()
    bot.set_group_whole_mute = AsyncMock()
    return bot


@pytest.fixture
def mock_event() -> MagicMock:
    """创建模拟的群消息事件"""
    event = MagicMock(spec=MilkyGroupMessageEvent)
    event.data = MagicMock()
    event.data.peer_id = 123456789
    event.data.sender_id = 111111
    event.data.segments = []
    return event


@pytest.fixture
def mock_at() -> MagicMock:
    """创建模拟的 @ 提及对象"""
    at = MagicMock(spec=At)
    at.target = "987654321"
    at.display = "测试用户"
    return at


# ================= 全体禁言测试 =================


class TestWholeMute:
    """全体禁言功能测试"""

    @pytest.mark.asyncio
    async def test_whole_mute_enable(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试开启全体禁言"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.whole_mute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_mute(
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_whole_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id, is_mute=True
        )
        mock_finish.assert_called_once_with(message="全体禁言成功")

    @pytest.mark.asyncio
    async def test_whole_mute_api_error(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体禁言 API 调用失败"""
        mock_bot.set_group_whole_mute.side_effect = Exception("API 调用失败")

        with pytest.raises(Exception, match="API 调用失败"):
            await milkybot_whole_mute(
                bot=mock_bot,
                event=mock_event,
            )

    @pytest.mark.asyncio
    async def test_whole_mute_network_error(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体禁言网络异常返回错误消息"""
        mock_bot.set_group_whole_mute.side_effect = NetworkError("连接失败")

        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.whole_mute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_mute(
                bot=mock_bot,
                event=mock_event,
            )

        mock_finish.assert_called_once()
        assert "全体禁言失败，网络异常" in mock_finish.call_args.kwargs["message"]

    @pytest.mark.asyncio
    async def test_whole_mute_action_failed(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体禁言操作被拒绝返回错误消息"""
        mock_bot.set_group_whole_mute.side_effect = ActionFailed(message="权限不足")

        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.whole_mute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_mute(
                bot=mock_bot,
                event=mock_event,
            )

        mock_finish.assert_called_once()
        assert "全体禁言失败，操作被拒绝" in mock_finish.call_args.kwargs["message"]


# ================= 禁言用户测试 =================


class TestMute:
    """禁言用户功能测试"""

    @pytest.mark.asyncio
    async def test_mute_uses_at_target(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试从 At.target 获取禁言用户"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.member_mute_cmd.finish"
        ) as mock_finish:
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
        mock_finish.assert_called_once()
        result_message = mock_finish.call_args.kwargs["message"]
        assert isinstance(result_message, UniMessage)
        assert "已禁言:" in str(result_message)
        assert "名称: @测试用户" in str(result_message)
        assert "时长: 60 秒" in str(result_message)
        assert "原因: 测试" in str(result_message)
        assert "标识: 987654321" in str(result_message)

    @pytest.mark.asyncio
    async def test_mute_prefers_mention_segment_user_id(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试存在 mention 消息段时优先使用消息段中的用户 ID"""
        mock_event.data.segments = [
            {"type": "mention", "data": {"user_id": 222222, "name": "段用户"}}
        ]

        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.member_mute_cmd.finish"
        ) as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=300,
                reason="违规",
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id,
            user_id=222222,
            duration=300,
        )
        result_message = mock_finish.call_args.kwargs["message"]
        assert "名称: @段用户" in str(result_message)
        assert "时长: 300 秒" in str(result_message)
        assert "原因: 违规" in str(result_message)
        assert "标识: 222222" in str(result_message)

    @pytest.mark.asyncio
    async def test_mute_skips_self(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试目标用户是发送者本人时不调用禁言 API"""
        mock_event.data.sender_id = 987654321

        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.member_mute_cmd.finish"
        ) as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=60,
                reason="测试",
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_not_called()
        mock_finish.assert_not_called()

    @pytest.mark.asyncio
    async def test_mute_api_error(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试禁言 API 调用失败"""
        mock_bot.set_group_member_mute.side_effect = Exception("API 调用失败")

        with pytest.raises(Exception, match="API 调用失败"):
            await milkybot_mute(
                user=mock_at,
                duration=60,
                reason="测试",
                bot=mock_bot,
                event=mock_event,
            )


# ================= 解禁用户测试 =================


class TestUnmute:
    """解禁用户功能测试"""

    @pytest.mark.asyncio
    async def test_unmute_basic(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试基本解禁功能"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.member_unmute_cmd.finish"
        ) as mock_finish:
            await milkybot_unmute(
                user=mock_at,
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id,
            user_id=987654321,
            duration=0,
        )
        mock_finish.assert_called_once()
        result_message = mock_finish.call_args.kwargs["message"]
        assert isinstance(result_message, UniMessage)
        assert "已解禁:" in str(result_message)
        assert "名称: 测试用户" in str(result_message)
        assert "原因: 管理员操作「默认」" in str(result_message)
        assert "标识: 987654321" in str(result_message)

    @pytest.mark.asyncio
    async def test_unmute_prefers_mention_segment_user_id(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试存在 mention 消息段时优先解禁消息段中的用户"""
        mock_event.data.segments = [
            {"type": "mention", "data": {"user_id": 333333, "name": "段用户"}}
        ]

        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.member_unmute_cmd.finish"
        ) as mock_finish:
            await milkybot_unmute(
                user=mock_at,
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id,
            user_id=333333,
            duration=0,
        )
        assert "名称: 段用户" in str(mock_finish.call_args.kwargs["message"])

    @pytest.mark.asyncio
    async def test_unmute_api_error(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试解禁 API 调用失败"""
        mock_bot.set_group_member_mute.side_effect = Exception("API 调用失败")

        with pytest.raises(Exception, match="API 调用失败"):
            await milkybot_unmute(
                user=mock_at,
                bot=mock_bot,
                event=mock_event,
            )

    @pytest.mark.asyncio
    async def test_unmute_network_error(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试解禁网络异常返回错误消息"""
        mock_bot.set_group_member_mute.side_effect = NetworkError("连接失败")

        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.member_unmute_cmd.finish"
        ) as mock_finish:
            await milkybot_unmute(
                user=mock_at,
                bot=mock_bot,
                event=mock_event,
            )

        mock_finish.assert_called_once()
        assert "解禁失败，网络异常" in mock_finish.call_args.kwargs["message"]

    @pytest.mark.asyncio
    async def test_unmute_action_failed(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试解禁操作被拒绝返回错误消息"""
        mock_bot.set_group_member_mute.side_effect = ActionFailed(message="权限不足")

        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.member_unmute_cmd.finish"
        ) as mock_finish:
            await milkybot_unmute(
                user=mock_at,
                bot=mock_bot,
                event=mock_event,
            )

        mock_finish.assert_called_once()
        assert "解禁失败，操作被拒绝" in mock_finish.call_args.kwargs["message"]


# ================= 全体解禁测试 =================


class TestWholeUnmute:
    """全体解禁功能测试"""

    @pytest.mark.asyncio
    async def test_whole_unmute_disable(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试关闭全体禁言（解禁）"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.whole_unmute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_unmute(
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_whole_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id, is_mute=False
        )
        mock_finish.assert_called_once_with(message="全体解禁成功")

    @pytest.mark.asyncio
    async def test_whole_unmute_api_error(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体解禁 API 调用失败"""
        mock_bot.set_group_whole_mute.side_effect = Exception("API 调用失败")

        with pytest.raises(Exception, match="API 调用失败"):
            await milkybot_whole_unmute(
                bot=mock_bot,
                event=mock_event,
            )

    @pytest.mark.asyncio
    async def test_whole_unmute_network_error(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体解禁网络异常返回错误消息"""
        mock_bot.set_group_whole_mute.side_effect = NetworkError("连接失败")

        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.whole_unmute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_unmute(
                bot=mock_bot,
                event=mock_event,
            )

        mock_finish.assert_called_once()
        assert "全体解禁失败，网络异常" in mock_finish.call_args.kwargs["message"]

    @pytest.mark.asyncio
    async def test_whole_unmute_action_failed(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体解禁操作被拒绝返回错误消息"""
        mock_bot.set_group_whole_mute.side_effect = ActionFailed(message="权限不足")

        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.whole_unmute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_unmute(
                bot=mock_bot,
                event=mock_event,
            )

        mock_finish.assert_called_once()
        assert "全体解禁失败，操作被拒绝" in mock_finish.call_args.kwargs["message"]


# ================= 集成场景测试 =================


class TestIntegrationScenarios:
    """集成场景测试"""

    @pytest.mark.asyncio
    async def test_mute_then_unmute_sequential(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试先禁言后解禁的顺序操作"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.member_mute_cmd.finish"
        ):
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

        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.member_unmute_cmd.finish"
        ):
            await milkybot_unmute(
                user=mock_at,
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_called_with(
            group_id=mock_event.data.peer_id,
            user_id=987654321,
            duration=0,
        )

    @pytest.mark.asyncio
    async def test_multiple_operations_different_groups(
        self, mock_bot: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试不同群组的操作"""
        group_ids = [111111, 222222, 333333]

        for group_id in group_ids:
            event = MagicMock(spec=MilkyGroupMessageEvent)
            event.data = MagicMock()
            event.data.peer_id = group_id
            event.data.sender_id = 111111
            event.data.segments = []

            with patch(
                "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.member_mute_cmd.finish"
            ):
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
    """UniMessage 消息格式测试"""

    @pytest.mark.asyncio
    async def test_unmute_message_is_uni_message_instance(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试解禁返回的消息是 UniMessage 实例"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.member_unmute_cmd.finish"
        ) as mock_finish:
            await milkybot_unmute(
                user=mock_at,
                bot=mock_bot,
                event=mock_event,
            )

        result_message = mock_finish.call_args.kwargs["message"]
        assert isinstance(result_message, UniMessage)

    @pytest.mark.asyncio
    async def test_whole_mute_message_format(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体禁言消息格式"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.whole_mute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_mute(
                bot=mock_bot,
                event=mock_event,
            )

        assert mock_finish.call_args.kwargs["message"] == "全体禁言成功"

    @pytest.mark.asyncio
    async def test_whole_unmute_message_format(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体解禁消息格式"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.command.mute.whole_unmute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_unmute(
                bot=mock_bot,
                event=mock_event,
            )

        assert mock_finish.call_args.kwargs["message"] == "全体解禁成功"
