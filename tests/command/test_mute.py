"""
测试禁言命令 - 补充测试
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot.adapters.milky.message import Mention as At
from nonebot_plugin_alconna import UniMessage

from src.plugins.nonebot_plugin_lingchu_bot.command.mute import (
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
    return event


@pytest.fixture
def mock_at() -> MagicMock:
    """创建模拟的 @ 提及对象"""
    at = MagicMock(spec=At)
    at.data = {"user_id": 987654321}
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
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.whole_mute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_mute(
                bot=mock_bot,
                event=mock_event,
                status=True,
            )

        mock_bot.set_group_whole_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id, is_mute=True
        )
        mock_finish.assert_called_once()
        assert str(mock_finish.call_args[1]["message"]) == "全体禁言成功"

    @pytest.mark.asyncio
    async def test_whole_mute_disable(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试关闭全体禁言（通过 status=False）"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.whole_mute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_mute(
                bot=mock_bot,
                event=mock_event,
                status=False,
            )

        # status=False 时不应调用 API（函数内部有条件判断）
        mock_bot.set_group_whole_mute.assert_not_called()
        mock_finish.assert_called_once()
        assert str(mock_finish.call_args[1]["message"]) == "全体禁言成功"

    @pytest.mark.asyncio
    async def test_whole_mute_default_true(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试默认参数（status=True）"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.whole_mute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_mute(
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_whole_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id, is_mute=True
        )
        mock_finish.assert_called_once()

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
                status=True,
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
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.member_unmute_cmd.finish"
        ) as mock_finish:
            await milkybot_unmute(
                user=mock_at,
                bot=mock_bot,
                event=mock_event,
            )

        # 解禁时 duration 应该为 0
        mock_bot.set_group_member_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id,
            user_id=mock_at.data["user_id"],
            duration=0,
        )
        mock_finish.assert_called_once()
        assert (
            str(mock_finish.call_args[1]["message"])
            == f"已解禁用户 {mock_at.data['user_id']}"
        )

    @pytest.mark.asyncio
    async def test_unmute_multiple_users(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试解禁多个用户"""
        users = [111111, 222222, 333333]

        for user_id in users:
            at = MagicMock(spec=At)
            at.data = {"user_id": user_id}

            with patch(
                "src.plugins.nonebot_plugin_lingchu_bot.command.mute.member_unmute_cmd.finish"
            ):
                await milkybot_unmute(
                    user=at,
                    bot=mock_bot,
                    event=mock_event,
                )

            mock_bot.set_group_member_mute.assert_called_with(
                group_id=mock_event.data.peer_id,
                user_id=user_id,
                duration=0,
            )

    @pytest.mark.asyncio
    async def test_unmute_user_not_muted(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试解禁未被禁言的用户（API 应该仍然正常调用）"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.member_unmute_cmd.finish"
        ) as mock_finish:
            await milkybot_unmute(
                user=mock_at,
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_called_once()
        mock_finish.assert_called_once()

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


# ================= 全体解禁测试 =================


class TestWholeUnmute:
    """全体解禁功能测试"""

    @pytest.mark.asyncio
    async def test_whole_unmute_disable(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试关闭全体禁言（解禁）"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.whole_unmute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_unmute(
                bot=mock_bot,
                event=mock_event,
                status=False,
            )

        mock_bot.set_group_whole_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id, is_mute=False
        )
        mock_finish.assert_called_once()
        assert str(mock_finish.call_args[1]["message"]) == "全体解禁成功"

    @pytest.mark.asyncio
    async def test_whole_unmute_with_true_status(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试 status=True 时不应调用 API（因为函数内有 if not status）"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.whole_unmute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_unmute(
                bot=mock_bot,
                event=mock_event,
                status=True,
            )

        # status=True 时条件 if not status 为 False，不应调用 API
        mock_bot.set_group_whole_mute.assert_not_called()
        mock_finish.assert_called_once()
        assert str(mock_finish.call_args[1]["message"]) == "全体解禁成功"

    @pytest.mark.asyncio
    async def test_whole_unmute_default_false(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试默认参数（status=False）"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.whole_unmute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_unmute(
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_whole_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id, is_mute=False
        )
        mock_finish.assert_called_once()

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
                status=False,
            )


# ================= 边界条件测试 =================


class TestEdgeCases:
    """边界条件测试"""

    @pytest.mark.asyncio
    async def test_mute_max_duration(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试最大禁言时长"""
        max_duration = 24 * 60 * 60  # 24小时

        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.member_mute_cmd.finish"
        ):
            await milkybot_mute(
                user=mock_at,
                duration=max_duration,
                reason="最大时长测试",
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id,
            user_id=mock_at.data["user_id"],
            duration=max_duration,
        )

    @pytest.mark.asyncio
    async def test_mute_negative_duration(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试负数禁言时长（应该正常传递，由 API 处理）"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.member_mute_cmd.finish"
        ):
            await milkybot_mute(
                user=mock_at,
                duration=-1,
                reason="负数测试",
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_called_once_with(
            group_id=mock_event.data.peer_id,
            user_id=mock_at.data["user_id"],
            duration=-1,
        )

    @pytest.mark.asyncio
    async def test_mute_empty_reason(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试空字符串原因"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.member_mute_cmd.finish"
        ) as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=60,
                reason="",
                bot=mock_bot,
                event=mock_event,
            )

        expected_msg = f"已禁言 {mock_at.data['user_id']}，时长 60 秒，原因："
        assert str(mock_finish.call_args[1]["message"]) == expected_msg

    @pytest.mark.asyncio
    async def test_mute_very_long_reason(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试超长原因字符串"""
        long_reason = "A" * 1000

        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.member_mute_cmd.finish"
        ) as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=60,
                reason=long_reason,
                bot=mock_bot,
                event=mock_event,
            )

        expected_msg = (
            f"已禁言 {mock_at.data['user_id']}，时长 60 秒，原因：{long_reason}"
        )
        assert str(mock_finish.call_args[1]["message"]) == expected_msg


# ================= 集成场景测试 =================


class TestIntegrationScenarios:
    """集成场景测试"""

    @pytest.mark.asyncio
    async def test_mute_then_unmute_sequential(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试先禁言后解禁的顺序操作"""
        # 1. 禁言
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.member_mute_cmd.finish"
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
            user_id=mock_at.data["user_id"],
            duration=600,
        )

        # 2. 解禁
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.member_unmute_cmd.finish"
        ):
            await milkybot_unmute(
                user=mock_at,
                bot=mock_bot,
                event=mock_event,
            )

        mock_bot.set_group_member_mute.assert_called_with(
            group_id=mock_event.data.peer_id,
            user_id=mock_at.data["user_id"],
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

            with patch(
                "src.plugins.nonebot_plugin_lingchu_bot.command.mute.member_mute_cmd.finish"
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
                user_id=mock_at.data["user_id"],
                duration=300,
            )


# ================= UniMessage 测试 =================


class TestUniMessage:
    """UniMessage 消息格式测试"""

    @pytest.mark.asyncio
    async def test_message_is_uni_message_instance(
        self, mock_bot: MagicMock, mock_event: MagicMock, mock_at: MagicMock
    ) -> None:
        """测试返回的消息是 UniMessage 实例"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.member_mute_cmd.finish"
        ) as mock_finish:
            await milkybot_mute(
                user=mock_at,
                duration=60,
                reason="测试",
                bot=mock_bot,
                event=mock_event,
            )

        result_message = mock_finish.call_args[1]["message"]
        assert isinstance(result_message, UniMessage)

    @pytest.mark.asyncio
    async def test_whole_mute_message_format(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体禁言消息格式"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.whole_mute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_mute(
                bot=mock_bot,
                event=mock_event,
                status=True,
            )

        result_message = mock_finish.call_args[1]["message"]
        assert isinstance(result_message, UniMessage)
        assert str(result_message) == "全体禁言成功"

    @pytest.mark.asyncio
    async def test_whole_unmute_message_format(
        self, mock_bot: MagicMock, mock_event: MagicMock
    ) -> None:
        """测试全体解禁消息格式"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.command.mute.whole_unmute_cmd.finish"
        ) as mock_finish:
            await milkybot_whole_unmute(
                bot=mock_bot,
                event=mock_event,
                status=False,
            )

        result_message = mock_finish.call_args[1]["message"]
        assert isinstance(result_message, UniMessage)
        assert str(result_message) == "全体解禁成功"
