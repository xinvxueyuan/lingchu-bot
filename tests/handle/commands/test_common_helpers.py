"""测试 common.py 中新增的权限检查和审计函数。"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from nonebot.adapters.onebot.v11.exception import ActionFailed as Onebot11ActionFailed
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud import DatabaseError
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default.common import (
    CommandAudit,
    check_bot_privilege,
    check_target_privilege,
    format_user_display_name,
    operator_is_superuser_onebot11,
    record_audit_fire_and_forget,
    record_command_audit,
)

_GROUP_ID = 123456789
_TARGET_USER_ID = 999


# ================= check_target_privilege 测试 =================


class TestCheckTargetPrivilege:
    """check_target_privilege 权限检查测试。"""

    @pytest.mark.asyncio
    async def test_member_target_passes(
        self, mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
    ) -> None:
        """目标为普通成员时通过检查。"""
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            return_value={"role": "member"}
        )
        matcher = MagicMock()
        matcher.finish = AsyncMock()

        result = await check_target_privilege(
            mock_onebot11_bot, mock_onebot11_event, _TARGET_USER_ID, matcher
        )

        assert result is True
        matcher.finish.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_target_rejects_non_owner_operator(
        self, mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
    ) -> None:
        """目标为管理员且操作者为普通成员时拒绝。"""
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            side_effect=[{"role": "admin"}, {"role": "member"}]
        )
        matcher = MagicMock()
        matcher.finish = AsyncMock()

        result = await check_target_privilege(
            mock_onebot11_bot, mock_onebot11_event, _TARGET_USER_ID, matcher
        )

        assert result is False
        matcher.finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_target_passes_for_owner_operator(
        self, mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
    ) -> None:
        """目标为管理员且操作者为群主时通过。"""
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            side_effect=[{"role": "admin"}, {"role": "owner"}]
        )
        matcher = MagicMock()
        matcher.finish = AsyncMock()

        result = await check_target_privilege(
            mock_onebot11_bot, mock_onebot11_event, _TARGET_USER_ID, matcher
        )

        assert result is True
        matcher.finish.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_target_passes_for_superuser_operator(
        self, mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
    ) -> None:
        """目标为管理员且操作者为超级用户时通过。"""
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            side_effect=[{"role": "admin"}, {"role": "member"}]
        )
        matcher = MagicMock()
        matcher.finish = AsyncMock()

        with patch("nonebot.get_driver") as mock_get_driver:
            mock_config = MagicMock()
            mock_config.superusers = {str(mock_onebot11_event.user_id)}
            mock_get_driver.return_value.config = mock_config

            result = await check_target_privilege(
                mock_onebot11_bot, mock_onebot11_event, _TARGET_USER_ID, matcher
            )

        assert result is True
        matcher.finish.assert_not_called()

    @pytest.mark.asyncio
    async def test_protected_target_rejects_non_superuser(
        self, mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
    ) -> None:
        """白名单保护目标拒绝非 SUPERUSERS。"""
        matcher = MagicMock()
        matcher.finish = AsyncMock()
        matcher._lingchu_command_key = "kick_member"

        with (
            patch(
                "src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default.common.find_active_subject_policy",
                AsyncMock(return_value=MagicMock()),
            ),
            patch(
                "src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default.common.operator_is_superuser_onebot11",
                AsyncMock(return_value=False),
            ),
        ):
            result = await check_target_privilege(
                mock_onebot11_bot, mock_onebot11_event, _TARGET_USER_ID, matcher
            )

        assert result is False
        matcher.finish.assert_awaited_once()
        mock_onebot11_bot.get_group_member_info.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_protected_target_passes_for_repository_superuser(
        self, mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
    ) -> None:
        """白名单保护目标只允许仓库 SUPERUSERS 绕过。"""
        matcher = MagicMock()
        matcher.finish = AsyncMock()
        matcher._lingchu_command_key = "kick_member"

        with (
            patch(
                "src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default.common.find_active_subject_policy",
                AsyncMock(return_value=MagicMock()),
            ),
            patch(
                "src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default.common.operator_is_superuser_onebot11",
                AsyncMock(return_value=True),
            ),
        ):
            result = await check_target_privilege(
                mock_onebot11_bot, mock_onebot11_event, _TARGET_USER_ID, matcher
            )

        assert result is True
        matcher.finish.assert_not_called()
        mock_onebot11_bot.get_group_member_info.assert_not_awaited()


class TestOperatorIsSuperuserOnebot11:
    """仓库 SUPERUSERS 解析测试。"""

    @pytest.mark.asyncio
    async def test_returns_true_for_bound_superuser(self) -> None:
        user = MagicMock(uid="uid-1")
        with (
            patch(
                "src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default.common.permission_repo.get_user_by_platform_account",
                AsyncMock(return_value=user),
            ) as get_user,
            patch(
                "src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default.common.permission_repo.is_superuser",
                AsyncMock(return_value=True),
            ) as is_superuser,
        ):
            result = await operator_is_superuser_onebot11(123)

        assert result is True
        get_user.assert_awaited_once_with("qq", "123")
        is_superuser.assert_awaited_once_with("uid-1")

    @pytest.mark.asyncio
    async def test_returns_false_without_bound_uid(self) -> None:
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default.common.permission_repo.get_user_by_platform_account",
            AsyncMock(return_value=None),
        ):
            result = await operator_is_superuser_onebot11(123)

        assert result is False


# ================= check_bot_privilege 测试 =================


class TestCheckBotPrivilege:
    """check_bot_privilege 机器人权限检查测试。"""

    @pytest.mark.asyncio
    async def test_bot_admin_passes(self, mock_onebot11_bot: MagicMock) -> None:
        """机器人为管理员时通过检查。"""
        mock_onebot11_bot.self_id = "12345"
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            return_value={"role": "admin"}
        )
        matcher = MagicMock()
        matcher.finish = AsyncMock()

        result = await check_bot_privilege(mock_onebot11_bot, _GROUP_ID, matcher)

        assert result is True
        matcher.finish.assert_not_called()

    @pytest.mark.asyncio
    async def test_bot_owner_passes(self, mock_onebot11_bot: MagicMock) -> None:
        """机器人为群主时通过检查。"""
        mock_onebot11_bot.self_id = "12345"
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            return_value={"role": "owner"}
        )
        matcher = MagicMock()
        matcher.finish = AsyncMock()

        result = await check_bot_privilege(mock_onebot11_bot, _GROUP_ID, matcher)

        assert result is True
        matcher.finish.assert_not_called()

    @pytest.mark.asyncio
    async def test_bot_member_rejects(self, mock_onebot11_bot: MagicMock) -> None:
        """机器人为普通成员时拒绝。"""
        mock_onebot11_bot.self_id = "12345"
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            return_value={"role": "member"}
        )
        matcher = MagicMock()
        matcher.finish = AsyncMock()

        result = await check_bot_privilege(mock_onebot11_bot, _GROUP_ID, matcher)

        assert result is False
        matcher.finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_info_failure_rejects(self, mock_onebot11_bot: MagicMock) -> None:
        """获取机器人信息失败时拒绝。"""
        mock_onebot11_bot.self_id = "12345"
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            side_effect=Onebot11ActionFailed(message="权限不足")
        )
        matcher = MagicMock()
        matcher.finish = AsyncMock()

        result = await check_bot_privilege(mock_onebot11_bot, _GROUP_ID, matcher)

        assert result is False
        matcher.finish.assert_called_once()


# ================= record_command_audit 测试 =================


class TestRecordCommandAudit:
    """record_command_audit 审计记录测试。"""

    @pytest.mark.asyncio
    async def test_normal_record(
        self, mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
    ) -> None:
        """正常记录审计日志。"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.repositories.message_store.record_api_call",
            AsyncMock(),
        ) as mock_record:
            await record_command_audit(
                mock_onebot11_bot,
                mock_onebot11_event,
                CommandAudit(
                    action="member_mute",
                    target_user_id=_TARGET_USER_ID,
                    duration=300,
                    reason="违规",
                ),
            )

        mock_record.assert_called_once()
        audit_event = mock_record.call_args.args[0]
        assert audit_event.api_name == "command:member_mute"
        assert audit_event.audit_type == "command"
        assert "target=999" in audit_event.data_summary
        assert "duration=300" in audit_event.data_summary
        assert "reason=违规" in audit_event.data_summary

    @pytest.mark.asyncio
    async def test_database_error_silent(
        self, mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
    ) -> None:
        """数据库异常时静默处理，不抛出异常。"""
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.repositories.message_store.record_api_call",
            AsyncMock(side_effect=DatabaseError("连接失败")),
        ):
            await record_command_audit(
                mock_onebot11_bot,
                mock_onebot11_event,
                CommandAudit(action="member_unmute", target_user_id=_TARGET_USER_ID),
            )


# ================= format_user_display_name 测试 =================


class TestFormatUserDisplayName:
    """format_user_display_name 用户显示名称格式化测试。"""

    def test_at_style_with_name(self) -> None:
        """At 样式带名称时输出 @名称。"""
        assert format_user_display_name(123, "测试用户") == "@测试用户"

    def test_at_style_without_name_falls_back_to_id(self) -> None:
        """At 样式无名称时回退到 ID。"""
        assert format_user_display_name(123, None) == "123"
        assert format_user_display_name(123, "") == "123"

    def test_detail_style_with_name(self) -> None:
        """Detail 样式带名称时输出 名称(ID)。"""
        assert (
            format_user_display_name(123, "测试用户", style="detail") == "测试用户(123)"
        )

    def test_detail_style_without_name_falls_back_to_id(self) -> None:
        """Detail 样式无名称时回退到 ID。"""
        assert format_user_display_name(123, None, style="detail") == "123"
        assert format_user_display_name(123, "", style="detail") == "123"


# ================= record_audit_fire_and_forget 测试 =================


class TestRecordAuditFireAndForget:
    """record_audit_fire_and_forget fire-and-forget 审计调度测试。"""

    @pytest.mark.asyncio
    async def test_schedules_audit_task_with_audit_prefix(
        self, mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
    ) -> None:
        """调度时使用 audit:<action> 命名。"""
        captured: list[tuple[Any, str]] = []

        def _spy(coro: Any, *, name: str = "fire_and_forget") -> Any:
            captured.append((coro, name))
            return MagicMock()

        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.core.async_utils.fire_and_forget",
            side_effect=_spy,
        ):
            await record_audit_fire_and_forget(
                mock_onebot11_bot,
                mock_onebot11_event,
                CommandAudit(
                    action="member_mute",
                    target_user_id=_TARGET_USER_ID,
                    duration=300,
                    reason="违规",
                ),
            )

        assert len(captured) == 1
        coro, name = captured[0]
        assert name == "audit:member_mute"
        coro.close()

    @pytest.mark.asyncio
    async def test_schedules_audit_task_without_optional_fields(
        self, mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
    ) -> None:
        """可选字段缺省时仍正确调度。"""
        captured: list[tuple[Any, str]] = []

        def _spy(coro: Any, *, name: str = "fire_and_forget") -> Any:
            captured.append((coro, name))
            return MagicMock()

        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.core.async_utils.fire_and_forget",
            side_effect=_spy,
        ):
            await record_audit_fire_and_forget(
                mock_onebot11_bot,
                mock_onebot11_event,
                CommandAudit(action="whole_mute"),
            )

        assert len(captured) == 1
        coro, name = captured[0]
        assert name == "audit:whole_mute"
        coro.close()

    @pytest.mark.asyncio
    async def test_schedules_structured_remote_audit_with_group_id(
        self, mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock
    ) -> None:
        """远程命令通过结构化审计对象携带目标群。"""
        captured: list[tuple[Any, str]] = []

        def _spy(coro: Any, *, name: str = "fire_and_forget") -> Any:
            captured.append((coro, name))
            return MagicMock()

        with (
            patch(
                "src.plugins.nonebot_plugin_lingchu_bot.core.async_utils.fire_and_forget",
                side_effect=_spy,
            ),
            patch(
                "src.plugins.nonebot_plugin_lingchu_bot.repositories.message_store.record_api_call",
                AsyncMock(),
            ) as mock_record,
        ):
            await record_audit_fire_and_forget(
                mock_onebot11_bot,
                mock_onebot11_event,
                CommandAudit(
                    action="remote_mute",
                    target_user_id=_TARGET_USER_ID,
                    duration=300,
                    reason="违规",
                    group_id=987654321,
                ),
            )
            coro, name = captured[0]
            assert name == "audit:remote_mute"
            await coro

        audit_event = mock_record.call_args.args[0]
        assert "group=987654321" in audit_event.data_summary
