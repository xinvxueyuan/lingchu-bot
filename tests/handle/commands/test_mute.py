"""测试禁言命令 - 边界行为覆盖"""

import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from nonebot_plugin_alconna.uniseg import At
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.handle_config_manager import (
    HandleConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    mute as mute_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.mute import (
    member_mute_cmd,
    member_unmute_cmd,
    onebot11_mute,
    onebot11_recall_message,
    onebot11_set_default_mute_duration,
    onebot11_unmute,
    onebot11_whole_mute,
    onebot11_whole_unmute,
    recall_message_cmd,
    set_default_mute_duration_cmd,
    whole_mute_cmd,
    whole_unmute_cmd,
)

RECALL_DELETE_COUNT = 2
RECALL_QUERY_COUNT = 2


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


@pytest.fixture
def mock_session() -> Mock:
    """Provide a mock AsyncSession for mute handler Depends() injection."""
    sess = AsyncMock()
    sess.add = MagicMock()
    sess.add_all = MagicMock()
    return sess


class TestOneBot11Mute:
    """OneBot11 禁言 API 映射测试。"""

    @pytest.fixture(autouse=True)
    def _mock_record_audit_fire_and_forget(self):
        """避免审计记录触发后台任务和数据库调用。"""
        with patch.object(mute_module, "record_audit_fire_and_forget", new=AsyncMock()):
            yield

    @pytest.fixture(autouse=True)
    def _mock_check_target_privilege(self):
        """绕过 check_target_privilege 的真实 DB 调用（find_active_subject_policy）。

        member_mute 命令在 protected_subject_feature_keys 默认列表内，会触发
        find_active_subject_policy → get_one(session, ...) 的真实查询。使用 mock_session
        时 get_one 返回 coroutine 对象而非 None，导致 AttributeError。这里将
        check_target_privilege 直接 mock 为返回 True（通过权限检查），让测试聚焦于
        set_group_ban 等 OneBot API 调用断言。
        """
        with patch.object(
            mute_module, "check_target_privilege", new=AsyncMock(return_value=True)
        ):
            yield

    @pytest.fixture(autouse=True)
    def _mock_handle_config_manager(self):
        """Mock get_handle_config_manager 返回启用的配置。"""
        enabled_config = HandleConfig(enabled=True, defaults={}, policies={})

        class MockManager:
            async def get_config(self, command_key: str) -> HandleConfig:
                return enabled_config

        with patch.object(
            mute_module, "get_handle_config_manager", return_value=MockManager()
        ):
            yield

    @pytest.mark.asyncio
    async def test_onebot11_mute_calls_set_group_ban(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_at: MagicMock,
        mock_session: Mock,
    ) -> None:
        mock_onebot11_bot.set_group_ban = AsyncMock()
        # check_target_privilege: 已由 autouse fixture mock 为返回 True
        # check_bot_privilege: 机器人为管理员（通过）
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            side_effect=[{"role": "admin"}]
        )

        with patch.object(member_mute_cmd, "finish") as mock_finish:
            await onebot11_mute(
                user=mock_at,
                duration=300,
                reason="违规",
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
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
        mock_session: Mock,
    ) -> None:
        mock_onebot11_bot.set_group_ban = AsyncMock()

        with patch.object(member_unmute_cmd, "finish") as mock_finish:
            await onebot11_unmute(
                user=mock_at,
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        mock_onebot11_bot.set_group_ban.assert_called_once_with(
            group_id=mock_onebot11_event.group_id,
            user_id=987654321,
            duration=0,
        )
        assert "已解禁:" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_onebot11_set_default_mute_duration_updates_config(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        config_manager = MagicMock()
        config_manager.get_config = AsyncMock(return_value=MagicMock(enabled=True))
        config_manager.update_config = AsyncMock()

        with (
            patch.object(
                mute_module, "get_handle_config_manager", return_value=config_manager
            ),
            patch.object(set_default_mute_duration_cmd, "finish") as mock_finish,
        ):
            await onebot11_set_default_mute_duration(
                duration=600,
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        config_manager.update_config.assert_awaited_once_with(
            "member_mute",
            {"defaults": {"mute_duration": 600}},
        )
        assert finish_text(mock_finish) == "默认禁言时长已更新为 600 秒"

    @pytest.mark.asyncio
    async def test_onebot11_mute_uses_configured_default_duration(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_at: MagicMock,
        mock_session: Mock,
    ) -> None:
        config_manager = MagicMock()
        config_manager.get_config = AsyncMock(
            return_value=MagicMock(
                enabled=True,
                defaults={"mute_duration": 600, "default_reason": "管理员操作"},
            )
        )
        mock_onebot11_bot.set_group_ban = AsyncMock()
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            return_value={"role": "admin"}
        )

        with (
            patch.object(
                mute_module, "get_handle_config_manager", return_value=config_manager
            ),
            patch.object(member_mute_cmd, "finish") as mock_finish,
        ):
            await onebot11_mute(
                user=mock_at,
                duration=None,
                reason=None,
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        mock_onebot11_bot.set_group_ban.assert_awaited_once_with(
            group_id=mock_onebot11_event.group_id,
            user_id=987654321,
            duration=600,
        )
        assert "时长: 600 秒" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_onebot11_set_default_mute_duration_rejects_duration_above_limit(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        config_manager = MagicMock()
        config_manager.get_config = AsyncMock(return_value=MagicMock(enabled=True))
        config_manager.update_config = AsyncMock()

        with (
            patch.object(
                mute_module, "get_handle_config_manager", return_value=config_manager
            ),
            patch.object(set_default_mute_duration_cmd, "finish") as mock_finish,
        ):
            await onebot11_set_default_mute_duration(
                duration=mute_module.MUTE_DURATION_MAX + 1,
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        config_manager.update_config.assert_not_awaited()
        assert "禁言时长不能超过" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_onebot11_whole_mute_calls_set_group_whole_ban(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        mock_onebot11_bot.set_group_whole_ban = AsyncMock()
        # check_bot_privilege: 机器人为管理员（通过）
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            return_value={"role": "admin"}
        )

        with patch.object(whole_mute_cmd, "finish") as mock_finish:
            await onebot11_whole_mute(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        mock_onebot11_bot.set_group_whole_ban.assert_called_once_with(
            group_id=mock_onebot11_event.group_id, enable=True
        )
        assert finish_text(mock_finish) == "全体禁言成功"

    @pytest.mark.asyncio
    async def test_onebot11_whole_unmute_calls_set_group_whole_ban(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        mock_onebot11_bot.set_group_whole_ban = AsyncMock()

        with patch.object(whole_unmute_cmd, "finish") as mock_finish:
            await onebot11_whole_unmute(
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
                session=mock_session,
            )

        mock_onebot11_bot.set_group_whole_ban.assert_called_once_with(
            group_id=mock_onebot11_event.group_id, enable=False
        )
        assert finish_text(mock_finish) == "全体解禁成功"

    @pytest.mark.asyncio
    async def test_onebot11_recall_message_verifies_and_deletes_recent_messages(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        first_record = MagicMock(
            message_id="101",
            user_id="2001",
            conversation_id=str(mock_onebot11_event.group_id),
        )
        command_record = MagicMock(
            message_id="999",
            user_id="111222333",
            conversation_id=str(mock_onebot11_event.group_id),
        )
        admin_record = MagicMock(
            message_id="102",
            user_id="2002",
            conversation_id=str(mock_onebot11_event.group_id),
        )
        second_record = MagicMock(
            message_id="103",
            user_id="2003",
            conversation_id=str(mock_onebot11_event.group_id),
        )
        mock_onebot11_event.message_id = 999
        mock_onebot11_bot.get_msg = AsyncMock(
            side_effect=[
                {
                    "message_id": 101,
                    "message_type": "group",
                    "group_id": mock_onebot11_event.group_id,
                    "sender": {"user_id": 2001},
                },
                {
                    "message_id": 102,
                    "message_type": "group",
                    "group_id": mock_onebot11_event.group_id,
                    "sender": {"user_id": 2002},
                },
                {
                    "message_id": 103,
                    "message_type": "group",
                    "group_id": mock_onebot11_event.group_id,
                    "sender": {"user_id": 2003},
                },
            ]
        )
        mock_onebot11_bot.delete_msg = AsyncMock()
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            side_effect=[
                {"role": "admin"},  # bot privilege check
                {"role": "member"},
                {"role": "admin"},
                {"role": "member"},
            ]
        )

        with (
            patch.object(
                mute_module.message_repository,
                "list_recent_messages",
                AsyncMock(
                    return_value=[
                        first_record,
                        command_record,
                        admin_record,
                        second_record,
                    ]
                ),
            ) as list_recent,
            patch.object(
                mute_module,
                "find_active_subject_policy",
                AsyncMock(return_value=None),
            ),
            patch.object(recall_message_cmd, "finish") as mock_finish,
        ):
            await onebot11_recall_message(
                session=mock_session,
                target=None,
                count=2,
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
            )

        assert list_recent.await_count == RECALL_QUERY_COUNT
        assert list_recent.call_args.args[0] is mock_session
        assert list_recent.call_args.kwargs["bot_id"] == mock_onebot11_bot.self_id
        mock_onebot11_bot.delete_msg.assert_any_await(message_id=101)
        mock_onebot11_bot.delete_msg.assert_any_await(message_id=103)
        assert mock_onebot11_bot.delete_msg.await_count == RECALL_DELETE_COUNT
        assert "已撤回 2 条消息" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_onebot11_recall_message_uses_legacy_session_records(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: Mock,
    ) -> None:
        record = MagicMock(
            message_id="101",
            user_id="2001",
            conversation_id=f"group_{mock_onebot11_event.group_id}_2001",
            raw_event=json.dumps({"group_id": mock_onebot11_event.group_id}),
        )
        mock_onebot11_event.message_id = 999
        mock_onebot11_bot.get_msg = AsyncMock(
            return_value={
                "message_id": 101,
                "message_type": "group",
                "group_id": mock_onebot11_event.group_id,
                "sender": {"user_id": 2001},
            }
        )
        mock_onebot11_bot.delete_msg = AsyncMock()
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            side_effect=[
                {"role": "admin"},  # bot privilege check
                {"role": "member"},
            ]
        )

        with (
            patch.object(
                mute_module.message_repository,
                "list_recent_messages",
                AsyncMock(side_effect=[[record], []]),
            ) as list_recent,
            patch.object(
                mute_module,
                "find_active_subject_policy",
                AsyncMock(return_value=None),
            ),
            patch.object(recall_message_cmd, "finish") as mock_finish,
        ):
            await onebot11_recall_message(
                session=mock_session,
                target=None,
                count=1,
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
            )

        assert list_recent.await_count == RECALL_QUERY_COUNT
        assert list_recent.await_args_list[0].args[0] is mock_session
        assert "conversation_id" not in list_recent.await_args_list[0].kwargs
        assert list_recent.await_args_list[1].kwargs["conversation_id"] == str(
            mock_onebot11_event.group_id
        )
        mock_onebot11_bot.delete_msg.assert_awaited_once_with(message_id=101)
        assert "已撤回 1 条消息" in finish_text(mock_finish)

    @pytest.mark.asyncio
    async def test_onebot11_recall_message_filters_by_target_user(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_at: MagicMock,
        mock_session: Mock,
    ) -> None:
        record = MagicMock(
            message_id="101",
            user_id="987654321",
            conversation_id=str(mock_onebot11_event.group_id),
        )
        mock_onebot11_event.message_id = 999
        mock_onebot11_bot.get_msg = AsyncMock(
            return_value={
                "message_id": 101,
                "message_type": "group",
                "group_id": mock_onebot11_event.group_id,
                "sender": {"user_id": 987654321},
            }
        )
        mock_onebot11_bot.delete_msg = AsyncMock()
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            side_effect=[
                {"role": "admin"},  # bot privilege check
                {"role": "member"},
            ]
        )

        with (
            patch.object(
                mute_module.message_repository,
                "list_recent_messages",
                AsyncMock(return_value=[record]),
            ) as list_recent,
            patch.object(
                mute_module,
                "find_active_subject_policy",
                AsyncMock(return_value=None),
            ),
            patch.object(recall_message_cmd, "finish") as mock_finish,
        ):
            await onebot11_recall_message(
                session=mock_session,
                target=mock_at,
                count=1,
                bot=mock_onebot11_bot,
                event=mock_onebot11_event,
            )

        assert list_recent.call_args.args[0] is mock_session
        assert list_recent.call_args.kwargs["user_id"] == "987654321"
        assert list_recent.await_count == RECALL_QUERY_COUNT
        mock_onebot11_bot.delete_msg.assert_awaited_once_with(message_id=101)
        assert "目标: @测试用户" in finish_text(mock_finish)
