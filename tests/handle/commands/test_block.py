from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    block as block_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands import (
    block as block_cmd_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.block import (
    block_member_cmd,
    clear_blocklist_cmd,
    global_block_member_cmd,
    global_clear_blocklist_cmd,
    global_unblock_member_cmd,
    unblock_member_cmd,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.triggers import (
    COMMAND_TRIGGERS,
)
from tests.handle.commands.conftest import finish_text

# 测试用 user_id 常量（避免 PLR2004 魔数值警告）
_TEST_USER_ID_BLOCK = 111222333
_TEST_USER_ID_UNBLOCK = 444555666
_TEST_BLOCK_DURATION = 60


@pytest.fixture
def mock_session() -> Mock:
    """Provide a mock AsyncSession for block handler Depends() injection pilot."""
    sess = AsyncMock()
    sess.add = MagicMock()
    sess.add_all = MagicMock()
    return sess


@pytest.fixture(autouse=True)
def _mock_record_audit_fire_and_forget():
    """避免审计记录触发后台任务和数据库调用。"""
    with patch.object(block_module, "record_audit_fire_and_forget", new=AsyncMock()):
        yield


@pytest.fixture(autouse=True)
def _mock_check_target_privilege():
    """绕过 check_target_privilege 的真实 DB 调用（find_active_subject_policy）。

    block_member 命令在 protected_subject_feature_keys 默认列表内，会触发
    find_active_subject_policy → get_one(session, ...) 的真实查询。使用 mock_session
    时 get_one 返回 coroutine 对象而非 None，导致 AttributeError。这里将
    check_target_privilege 直接 mock 为返回 True（通过权限检查），让测试聚焦于
    store_block_record / remove_block / clear_blocklist 的 session 透传断言。
    """
    with patch.object(
        block_module, "check_target_privilege", new=AsyncMock(return_value=True)
    ):
        yield


@pytest.mark.asyncio
async def test_onebot11_block_member_stores_record_and_kicks(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
    mock_session: Mock,
) -> None:
    mock_onebot11_bot.set_group_kick = AsyncMock()
    # check_target_privilege: 已由 autouse fixture mock 为返回 True
    # check_bot_privilege: 机器人为管理员（通过）
    mock_onebot11_bot.get_group_member_info = AsyncMock(side_effect=[{"role": "admin"}])

    with (
        patch.object(block_module, "store_block_record", AsyncMock()) as upsert_mock,
        patch.object(block_member_cmd, "finish") as mock_finish,
    ):
        await block_module.onebot11_block_member(
            user=mock_at,
            duration=None,
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    upsert_mock.assert_awaited_once()
    assert upsert_mock.call_args.args[0] is mock_session
    assert upsert_mock.call_args.kwargs["scope"] == "group"
    assert upsert_mock.call_args.kwargs["reason"] == "违反群规"
    assert upsert_mock.call_args.kwargs["duration"] is None
    mock_onebot11_bot.set_group_kick.assert_awaited_once_with(
        group_id=mock_onebot11_event.group_id,
        user_id=987654321,
        reject_add_request=False,
    )
    assert "已拉黑并踢出" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_global_block_member_uses_global_scope_and_kicks(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
    mock_session: Mock,
) -> None:
    mock_onebot11_bot.set_group_kick = AsyncMock()
    # check_target_privilege: 已由 autouse fixture mock 为返回 True
    # check_bot_privilege: 机器人为管理员（通过）
    mock_onebot11_bot.get_group_member_info = AsyncMock(side_effect=[{"role": "admin"}])

    with (
        patch.object(block_module, "store_block_record", AsyncMock()) as upsert_mock,
        patch.object(global_block_member_cmd, "finish"),
    ):
        await block_module.onebot11_global_block_member(
            user=mock_at,
            duration=_TEST_BLOCK_DURATION,
            reason="spam",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    assert upsert_mock.call_args.args[0] is mock_session
    assert upsert_mock.call_args.kwargs["scope"] == "global"
    assert upsert_mock.call_args.kwargs["reason"] == "spam"
    assert upsert_mock.call_args.kwargs["duration"] == _TEST_BLOCK_DURATION
    mock_onebot11_bot.set_group_kick.assert_awaited_once_with(
        group_id=mock_onebot11_event.group_id,
        user_id=987654321,
        reject_add_request=False,
    )


@pytest.mark.asyncio
async def test_onebot11_unblock_member_removes_group_entry(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
    mock_session: Mock,
) -> None:
    with (
        patch.object(
            block_module,
            "remove_block",
            AsyncMock(return_value=(1, True)),
        ) as remove_mock,
        patch.object(unblock_member_cmd, "finish") as mock_finish,
    ):
        await block_module.onebot11_unblock_member(
            user=mock_at,
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    assert remove_mock.call_args.args[0] is mock_session
    assert remove_mock.call_args.kwargs["scope"] == "group"
    assert "删除记录: 1" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_global_unblock_member_removes_global_entry(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
    mock_session: Mock,
) -> None:
    with (
        patch.object(
            block_module,
            "remove_block",
            AsyncMock(return_value=(1, True)),
        ) as remove_mock,
        patch.object(global_unblock_member_cmd, "finish"),
    ):
        await block_module.onebot11_global_unblock_member(
            user=mock_at,
            reason="appeal",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    assert remove_mock.call_args.args[0] is mock_session
    assert remove_mock.call_args.kwargs["scope"] == "global"


@pytest.mark.asyncio
async def test_onebot11_clear_blocklist_clears_group_scope(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_session: Mock,
) -> None:
    with (
        patch.object(
            block_module,
            "clear_blocklist",
            AsyncMock(return_value=(2, True)),
        ) as clear_mock,
        patch.object(clear_blocklist_cmd, "finish") as mock_finish,
    ):
        await block_module.onebot11_clear_blocklist(
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    assert clear_mock.call_args.args[0] is mock_session
    assert clear_mock.call_args.kwargs["scope"] == "group"
    assert "删除记录: 2" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_global_clear_blocklist_clears_global_scope(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_session: Mock,
) -> None:
    with (
        patch.object(
            block_module,
            "clear_blocklist",
            AsyncMock(return_value=(2, True)),
        ) as clear_mock,
        patch.object(global_clear_blocklist_cmd, "finish"),
    ):
        await block_module.onebot11_global_clear_blocklist(
            reason="reset",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    assert clear_mock.call_args.args[0] is mock_session
    assert clear_mock.call_args.kwargs["scope"] == "global"


@pytest.mark.asyncio
async def test_blocklisted_group_message_triggers_kick(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_session: Mock,
) -> None:
    mock_onebot11_bot.set_group_kick = AsyncMock()
    find_block_mock = AsyncMock(
        return_value=SimpleNamespace(reason="blocked"),
    )

    with patch.object(block_module, "find_active_block", find_block_mock):
        await block_module.onebot11_kick_blocklisted_message(
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    find_block_mock.assert_awaited_once()
    assert find_block_mock.call_args.args[0] is mock_session
    mock_onebot11_bot.set_group_kick.assert_awaited_once_with(
        group_id=mock_onebot11_event.group_id,
        user_id=mock_onebot11_event.user_id,
        reject_add_request=False,
    )


@pytest.mark.asyncio
async def test_non_blocklisted_group_message_does_not_kick(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_session: Mock,
) -> None:
    mock_onebot11_bot.set_group_kick = AsyncMock()
    find_block_mock = AsyncMock(return_value=None)

    with patch.object(block_module, "find_active_block", find_block_mock):
        await block_module.onebot11_kick_blocklisted_message(
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    find_block_mock.assert_awaited_once()
    assert find_block_mock.call_args.args[0] is mock_session
    mock_onebot11_bot.set_group_kick.assert_not_awaited()


@pytest.mark.asyncio
async def test_blocklisted_group_add_request_is_rejected(
    mock_onebot11_bot: MagicMock,
    mock_session: Mock,
) -> None:
    event = SimpleNamespace(
        sub_type="add",
        group_id=123456789,
        user_id=987654321,
        flag="flag-1",
    )
    mock_onebot11_bot.set_group_add_request = AsyncMock()
    find_block_mock = AsyncMock(
        return_value=SimpleNamespace(reason="blocked"),
    )

    with patch.object(block_module, "find_active_block", find_block_mock):
        await block_module.onebot11_reject_blocklisted_group_request(
            bot=mock_onebot11_bot,
            event=event,
            session=mock_session,
        )

    find_block_mock.assert_awaited_once()
    assert find_block_mock.call_args.args[0] is mock_session
    mock_onebot11_bot.set_group_add_request.assert_awaited_once_with(
        flag="flag-1",
        sub_type="add",
        approve=False,
        reason="blocked",
    )


@pytest.mark.asyncio
async def test_invite_request_is_ignored(
    mock_onebot11_bot: MagicMock,
    mock_session: Mock,
) -> None:
    event = SimpleNamespace(
        sub_type="invite",
        group_id=123456789,
        user_id=987654321,
        flag="flag-1",
    )
    mock_onebot11_bot.set_group_add_request = AsyncMock()

    with patch.object(block_module, "find_active_block", AsyncMock()) as find_mock:
        await block_module.onebot11_reject_blocklisted_group_request(
            bot=mock_onebot11_bot,
            event=event,
            session=mock_session,
        )

    find_mock.assert_not_awaited()
    mock_onebot11_bot.set_group_add_request.assert_not_awaited()


def test_block_command_triggers_are_minimal() -> None:
    assert COMMAND_TRIGGERS["block_member"].english_aliases == {"block-member"}
    assert COMMAND_TRIGGERS["global_block_member"].chinese_aliases == {"全局拉黑用户"}
    assert COMMAND_TRIGGERS["clear_blocklist"].english_aliases == set()


@pytest.mark.asyncio
async def test_onebot11_block_member_with_direct_user_id(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_session: Mock,
) -> None:
    """测试直接传入 user_id (int) 进行拉黑操作"""
    mock_onebot11_bot.set_group_kick = AsyncMock()
    # resolve_user: 获取用户名片
    # check_target_privilege: 已由 autouse fixture mock 为返回 True
    # check_bot_privilege: 机器人为管理员（通过）
    mock_onebot11_bot.get_group_member_info = AsyncMock(
        side_effect=[
            {"card": "测试用户", "nickname": "TestUser"},
            {"role": "admin"},
        ]
    )

    with (
        patch.object(block_module, "store_block_record", AsyncMock()) as upsert_mock,
        patch.object(block_member_cmd, "finish") as mock_finish,
    ):
        await block_module.onebot11_block_member(
            user=_TEST_USER_ID_BLOCK,  # 直接传入 user_id (int)
            duration=None,
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    upsert_mock.assert_awaited_once()
    assert upsert_mock.call_args.args[0] is mock_session
    assert upsert_mock.call_args.kwargs["user_id"] == _TEST_USER_ID_BLOCK
    mock_onebot11_bot.set_group_kick.assert_awaited_once_with(
        group_id=mock_onebot11_event.group_id,
        user_id=_TEST_USER_ID_BLOCK,
        reject_add_request=False,
    )
    assert "已拉黑并踢出" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_unblock_member_with_direct_user_id(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_session: Mock,
) -> None:
    """测试直接传入 user_id (int) 进行删黑操作"""
    mock_onebot11_bot.get_group_member_info = AsyncMock(
        return_value={"card": "", "nickname": "TestUser"}
    )

    with (
        patch.object(
            block_module,
            "remove_block",
            AsyncMock(return_value=(1, True)),
        ) as remove_mock,
        patch.object(unblock_member_cmd, "finish") as mock_finish,
    ):
        await block_module.onebot11_unblock_member(
            user=_TEST_USER_ID_UNBLOCK,  # 直接传入 user_id (int)
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    assert remove_mock.call_args.args[0] is mock_session
    assert remove_mock.call_args.kwargs["scope"] == "group"
    assert remove_mock.call_args.kwargs["user_id"] == _TEST_USER_ID_UNBLOCK
    assert "删除记录: 1" in finish_text(mock_finish)


# ================= __getattr__ 懒加载导出测试 =================


class TestLazyExports:
    """commands.block 模块 __getattr__ 懒加载导出测试（覆盖行 97-100）。"""

    def test_lazy_export_returns_handler_and_caches(self) -> None:
        """访问懒导出名时通过 __getattr__ 返回处理器并写入 globals 缓存。"""
        cached = block_cmd_module.__dict__.pop("onebot11_block_member", None)
        try:
            value = block_cmd_module.onebot11_block_member
            assert callable(value)
            assert block_cmd_module.__dict__["onebot11_block_member"] is value
        finally:
            if cached is not None:
                block_cmd_module.__dict__["onebot11_block_member"] = cached

    def test_lazy_export_caches_all_handlers(self) -> None:
        """所有懒导出名都能正确解析到适配器处理器。"""
        names = (
            "onebot11_block_member",
            "onebot11_global_block_member",
            "onebot11_unblock_member",
            "onebot11_global_unblock_member",
            "onebot11_clear_blocklist",
            "onebot11_global_clear_blocklist",
            "onebot11_kick_blocklisted_message",
            "onebot11_reject_blocklisted_group_request",
        )
        originals = {name: block_cmd_module.__dict__.pop(name, None) for name in names}
        try:
            for name in names:
                value = getattr(block_cmd_module, name)
                assert callable(value), f"{name} 应为可调用处理器"
                assert name in block_cmd_module.__dict__
        finally:
            for name, original in originals.items():
                if original is not None:
                    block_cmd_module.__dict__[name] = original

    def test_unknown_attribute_raises_attribute_error(self) -> None:
        """访问未导出的属性名时抛出 AttributeError。"""
        with pytest.raises(AttributeError):
            _ = block_cmd_module.not_a_real_export
