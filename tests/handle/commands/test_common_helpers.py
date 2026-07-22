"""测试 common.py 中新增的权限检查和审计函数。"""

from typing import Any, cast
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
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands import (
    common as common_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.common import (
    selected_adapter_handle,
)

_GROUP_ID = 123456789
_TARGET_USER_ID = 999


class _FakeSessionContext:
    """Async context manager that yields a fixed mock session."""

    def __init__(self, session: Any) -> None:
        self._session = session

    async def __aenter__(self) -> Any:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        return None


@pytest.fixture
def mock_session() -> MagicMock:
    """Provide a mock AsyncSession for common helpers that require a session."""
    return MagicMock(name="async_session")


# ================= check_target_privilege 测试 =================


class TestCheckTargetPrivilege:
    """check_target_privilege 权限检查测试。"""

    @pytest.mark.asyncio
    async def test_member_target_passes(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """目标为普通成员时通过检查。"""
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            return_value={"role": "member"}
        )
        matcher = MagicMock()
        matcher.finish = AsyncMock()

        result = await check_target_privilege(
            mock_session,
            mock_onebot11_bot,
            mock_onebot11_event,
            _TARGET_USER_ID,
            matcher,
        )

        assert result is True
        matcher.finish.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_target_rejects_non_owner_operator(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """目标为管理员且操作者为普通成员时拒绝。"""
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            side_effect=[{"role": "admin"}, {"role": "member"}]
        )
        matcher = MagicMock()
        matcher.finish = AsyncMock()

        result = await check_target_privilege(
            mock_session,
            mock_onebot11_bot,
            mock_onebot11_event,
            _TARGET_USER_ID,
            matcher,
        )

        assert result is False
        matcher.finish.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_target_passes_for_owner_operator(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """目标为管理员且操作者为群主时通过。"""
        mock_onebot11_bot.get_group_member_info = AsyncMock(
            side_effect=[{"role": "admin"}, {"role": "owner"}]
        )
        matcher = MagicMock()
        matcher.finish = AsyncMock()

        result = await check_target_privilege(
            mock_session,
            mock_onebot11_bot,
            mock_onebot11_event,
            _TARGET_USER_ID,
            matcher,
        )

        assert result is True
        matcher.finish.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_target_passes_for_superuser_operator(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: MagicMock,
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
                mock_session,
                mock_onebot11_bot,
                mock_onebot11_event,
                _TARGET_USER_ID,
                matcher,
            )

        assert result is True
        matcher.finish.assert_not_called()

    @pytest.mark.asyncio
    async def test_protected_target_rejects_non_superuser(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: MagicMock,
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
                mock_session,
                mock_onebot11_bot,
                mock_onebot11_event,
                _TARGET_USER_ID,
                matcher,
            )

        assert result is False
        matcher.finish.assert_awaited_once()
        mock_onebot11_bot.get_group_member_info.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_protected_target_passes_for_repository_superuser(
        self,
        mock_onebot11_bot: MagicMock,
        mock_onebot11_event: MagicMock,
        mock_session: MagicMock,
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
                mock_session,
                mock_onebot11_bot,
                mock_onebot11_event,
                _TARGET_USER_ID,
                matcher,
            )

        assert result is True
        matcher.finish.assert_not_called()
        mock_onebot11_bot.get_group_member_info.assert_not_awaited()


class TestOperatorIsSuperuserOnebot11:
    """仓库 SUPERUSERS 解析测试。"""

    @pytest.mark.asyncio
    async def test_returns_true_for_bound_superuser(
        self, mock_session: MagicMock
    ) -> None:
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
            result = await operator_is_superuser_onebot11(mock_session, 123)

        assert result is True
        get_user.assert_awaited_once_with(mock_session, "qq", "123")
        is_superuser.assert_awaited_once_with(mock_session, "uid-1")

    @pytest.mark.asyncio
    async def test_returns_false_without_bound_uid(
        self, mock_session: MagicMock
    ) -> None:
        with patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default.common.permission_repo.get_user_by_platform_account",
            AsyncMock(return_value=None),
        ):
            result = await operator_is_superuser_onebot11(mock_session, 123)

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
        with (
            patch(
                "src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default.common.get_session",
                return_value=_FakeSessionContext(MagicMock()),
            ),
            patch(
                "src.plugins.nonebot_plugin_lingchu_bot.repositories.message_store.record_api_call",
                AsyncMock(),
            ) as mock_record,
        ):
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
        audit_event = mock_record.call_args.args[1]
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
        with (
            patch(
                "src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default.common.get_session",
                return_value=_FakeSessionContext(MagicMock()),
            ),
            patch(
                "src.plugins.nonebot_plugin_lingchu_bot.repositories.message_store.record_api_call",
                AsyncMock(side_effect=DatabaseError("连接失败")),
            ),
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
                "src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default.common.get_session",
                return_value=_FakeSessionContext(MagicMock()),
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

        audit_event = mock_record.call_args.args[1]
        assert "group=987654321" in audit_event.data_summary


# ================= selected_adapter_handle / 装饰器路径测试 =================


class TestSelectedAdapterHandle:
    """selected_adapter_handle 装饰器分支覆盖测试。"""

    def test_registers_handler_when_adapter_enabled_and_command_key_given(
        self,
    ) -> None:
        """适配器启用且提供 command_key 时，应用权限与状态包装并注册处理器。"""
        register = MagicMock()
        command: Any = MagicMock()
        command.handle = MagicMock(return_value=register)

        async def handler(*_args: Any, **_kwargs: Any) -> Any:
            return "ok"

        profile = MagicMock()
        profile.platform_id = "qq"

        with (
            patch.object(common_module, "is_adapter_enabled", return_value=True),
            patch.object(common_module, "get_platform_profile", return_value=profile),
        ):
            decorator = selected_adapter_handle(command, "~onebot.v11", "remote_mute")
            returned = decorator(handler)

        # 装饰器始终返回原函数
        assert returned is handler
        # _lingchu_command_key 被设置
        assert command._lingchu_command_key == "remote_mute"
        # command.handle() 被调用，注册器接收包装后的 handler
        command.handle.assert_called_once()
        register.assert_called_once()
        registered = register.call_args.args[0]
        assert registered is not handler  # 已被包装
        assert callable(registered)

    def test_skips_permission_wrapper_when_command_key_is_none(self) -> None:
        """command_key 为 None 时不应用权限包装，但仍注册状态包装后的 handler。"""
        register = MagicMock()
        command: Any = MagicMock()
        command.handle = MagicMock(return_value=register)

        async def handler(*_args: Any, **_kwargs: Any) -> Any:
            return "ok"

        profile = MagicMock()
        profile.platform_id = "qq"

        with (
            patch.object(common_module, "is_adapter_enabled", return_value=True),
            patch.object(common_module, "get_platform_profile", return_value=profile),
        ):
            decorator = selected_adapter_handle(command, "~onebot.v11", None)
            decorator(handler)

        command.handle.assert_called_once()
        register.assert_called_once()
        # command_key 为 None 时不调用 _permission_wrapper，仅应用状态包装
        # 注册的 handler 不是原 handler（已被状态包装）
        registered = register.call_args.args[0]
        assert registered is not handler

    def test_skips_state_wrapper_when_bypass_all(self) -> None:
        """bypass_gate 与 bypass_silent 同时为 True 时不应用状态包装。"""
        register = MagicMock()
        command: Any = MagicMock()
        command.handle = MagicMock(return_value=register)

        async def handler(*_args: Any, **_kwargs: Any) -> Any:
            return "ok"

        profile = MagicMock()
        profile.platform_id = "qq"

        with (
            patch.object(common_module, "is_adapter_enabled", return_value=True),
            patch.object(common_module, "get_platform_profile", return_value=profile),
        ):
            decorator = selected_adapter_handle(
                command,
                "~onebot.v11",
                "remote_mute",
                bypass_gate=True,
                bypass_silent=True,
            )
            decorator(handler)

        # 即使全部 bypass，command.handle() 仍被调用注册 handler
        command.handle.assert_called_once()
        register.assert_called_once()

    def test_uses_empty_platform_id_when_profile_missing(self) -> None:
        """get_platform_profile 返回 None 时 platform_id 回退为空字符串。"""
        register = MagicMock()
        command: Any = MagicMock()
        command.handle = MagicMock(return_value=register)

        async def handler(*_args: Any, **_kwargs: Any) -> Any:
            return "ok"

        with (
            patch.object(common_module, "is_adapter_enabled", return_value=True),
            patch.object(common_module, "get_platform_profile", return_value=None),
            patch.object(
                common_module, "_state_wrapper", wraps=common_module._state_wrapper
            ) as state_wrapper_spy,
        ):
            decorator = selected_adapter_handle(command, "~onebot.v11", "remote_mute")
            decorator(handler)

        state_wrapper_spy.assert_called_once()
        assert state_wrapper_spy.call_args.kwargs["platform_id"] == ""

    def test_does_not_register_when_adapter_disabled(self) -> None:
        """适配器未启用时不注册任何 handler。"""
        command: Any = MagicMock()
        command.handle = MagicMock()

        async def handler(*_args: Any, **_kwargs: Any) -> Any:
            return "ok"

        with patch.object(common_module, "is_adapter_enabled", return_value=False):
            decorator = selected_adapter_handle(command, "~onebot.v11", "remote_mute")
            returned = decorator(handler)

        assert returned is handler
        command.handle.assert_not_called()


# ================= _state_wrapper 主体调用测试 =================


class TestStateWrapperBody:
    """_state_wrapper 内部 wrapper 主体调用测试（覆盖行 88-92）。"""

    @pytest.mark.asyncio
    async def test_state_wrapper_blocks_when_gate_inactive(self) -> None:
        """门禁关闭时 wrapper 直接返回 None 且不调用 handler。"""
        from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.common import (
            _state_wrapper,
        )

        called = False

        async def handler(*_args: Any, **_kwargs: Any) -> Any:
            nonlocal called
            called = True
            return "result"

        command: Any = MagicMock()
        wrapped = _state_wrapper(command, handler, platform_id="qq", check_gate=True)

        with patch.object(common_module, "is_handle_active", return_value=False):
            result = await wrapped()

        assert result is None
        assert called is False

    @pytest.mark.asyncio
    async def test_state_wrapper_normal_path_calls_handler(self) -> None:
        """门禁开启且静默关闭时直接调用 handler。"""
        from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.common import (
            _state_wrapper,
        )

        async def handler(*_args: Any, **_kwargs: Any) -> Any:
            return "normal-result"

        command: Any = MagicMock()
        wrapped = _state_wrapper(command, handler, platform_id="qq", check_gate=True)

        with (
            patch.object(common_module, "is_handle_active", return_value=True),
            patch.object(common_module, "is_silent_mode", return_value=False),
        ):
            result = await wrapped()

        assert result == "normal-result"


# ================= _silent_call 恢复测试 =================


class _SilentCallFakeCommand:
    """模拟匹配器命令类，用于 _silent_call 单元测试。"""

    @classmethod
    async def finish(cls, _message: Any = None, **_kwargs: Any) -> Any:
        """模拟 finish 方法。"""
        return "original"


class TestSilentCallBody:
    """_silent_call 主体调用测试（覆盖行 104-117）。"""

    @pytest.mark.asyncio
    async def test_restores_finish_on_exception(self) -> None:
        """_silent_call 在处理器抛出异常时仍恢复原始 finish。"""
        from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.common import (
            _silent_call,
        )

        original = _SilentCallFakeCommand.__dict__["finish"]

        async def handler(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("error")

        with pytest.raises(RuntimeError, match="error"):
            await _silent_call(cast("Any", _SilentCallFakeCommand), handler)

        assert _SilentCallFakeCommand.__dict__["finish"] is original
