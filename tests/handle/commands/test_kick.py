from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.handle_config_manager import (
    HandleConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    kick as kick_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands import (
    kick as kick_commands_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.kick import (
    kick_member_cmd,
)
from tests.handle.commands.conftest import finish_text

# 测试用 user_id 常量（避免 PLR2004 魔数值警告）
# 注意：不能与 conftest.py 中 mock_onebot11_event.user_id (111222333) 相同
_TEST_KICK_USER_ID = 555666777
_TEST_BOT_SELF_ID = "999999"


@pytest.fixture
def mock_session() -> Mock:
    """Provide a mock AsyncSession for kick handler Depends() injection."""
    sess = AsyncMock()
    sess.add = MagicMock()
    sess.add_all = MagicMock()
    return sess


@pytest.fixture(autouse=True)
def _mock_record_audit_fire_and_forget():
    """避免审计记录触发后台任务和数据库调用。"""
    with patch.object(kick_module, "record_audit_fire_and_forget", new=MagicMock()):
        yield


@pytest.fixture(autouse=True)
def _mock_check_target_privilege():
    """绕过 check_target_privilege 的真实 DB 调用（find_active_subject_policy）。

    kick_member 命令在 protected_subject_feature_keys 默认列表内，会触发
    find_active_subject_policy → get_one(session, ...) 的真实查询。使用 mock_session
    时 get_one 返回 coroutine 对象而非 None，导致 AttributeError。这里将
    check_target_privilege 直接 mock 为返回 True（通过权限检查），让测试聚焦于
    find_active_block 的 session 透传断言。
    """
    with patch.object(
        kick_module, "check_target_privilege", new=AsyncMock(return_value=True)
    ):
        yield


@pytest.fixture(autouse=True)
def _mock_handle_config_manager():
    """Mock get_handle_config_manager 返回启用的配置。"""
    enabled_config = HandleConfig(enabled=True, defaults={}, policies={})

    class MockManager:
        async def get_config(self, command_key: str) -> HandleConfig:
            return enabled_config

    with patch.object(
        kick_module, "get_handle_config_manager", return_value=MockManager()
    ):
        yield


@pytest.mark.asyncio
async def test_onebot11_kick_member_with_at(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
    mock_session: Mock,
) -> None:
    """测试使用 At 对象踢出群成员（**与黑名单无关**）"""
    mock_onebot11_bot.set_group_kick = AsyncMock()
    # check_target_privilege: 已由 autouse fixture mock 为返回 True
    # check_bot_privilege: 机器人为管理员（通过）
    mock_onebot11_bot.get_group_member_info = AsyncMock(side_effect=[{"role": "admin"}])

    with patch.object(kick_member_cmd, "finish") as mock_finish:
        await kick_module.onebot11_kick_member(
            user=mock_at,
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    # 踢出是独立的群管操作：目标不在黑名单里也必须能踢（用户 2026-10-08 报的 bug）
    assert not hasattr(kick_module, "find_active_block")
    mock_onebot11_bot.set_group_kick.assert_awaited_once_with(
        group_id=mock_onebot11_event.group_id,
        user_id=987654321,
        reject_add_request=False,
    )
    assert "已踢出群成员" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_kick_member_with_direct_user_id(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_session: Mock,
) -> None:
    """测试直接传入 user_id (int) 踢出群成员（与黑名单无关）"""
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

    with patch.object(kick_member_cmd, "finish") as mock_finish:
        await kick_module.onebot11_kick_member(
            user=_TEST_KICK_USER_ID,
            reason="测试原因",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    mock_onebot11_bot.set_group_kick.assert_awaited_once_with(
        group_id=mock_onebot11_event.group_id,
        user_id=_TEST_KICK_USER_ID,
        reject_add_request=False,
    )
    assert "已踢出群成员" in finish_text(mock_finish)
    assert "测试原因" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_kick_member_works_without_blocklist(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
    mock_session: Mock,
) -> None:
    """**回归**：目标不在黑名单里也要能踢出（用户 2026-10-08 报的 bug）。

    踢出是独立的群管操作；此前它要求目标必须在黑名单中（「不在黑名单中，无法执行
    踢出操作」），导致普通成员根本踢不掉 —— 而该判定取出的 entry 除判空外从未被使用，
    属于残留耦合。
    """
    mock_onebot11_bot.set_group_kick = AsyncMock()
    mock_onebot11_bot.get_group_member_info = AsyncMock(side_effect=[{"role": "admin"}])

    with patch.object(kick_member_cmd, "finish") as mock_finish:
        await kick_module.onebot11_kick_member(
            user=mock_at,
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    mock_onebot11_bot.set_group_kick.assert_awaited_once()
    assert "已踢出群成员" in finish_text(mock_finish)


def test_kick_has_no_blocklist_dependency() -> None:
    """静态守卫：踢出处理器不得再引用黑名单（防止后人把耦合加回来）。

    黑名单一旦重新成为踢出的前置条件，「不在黑名单中，无法执行踢出操作」就会复现，
    而那是运行时才暴露的体验问题 —— 用源码断言把它挡在提交前。
    """
    import inspect
    import re

    source = inspect.getsource(kick_module)
    # 去掉注释与文档字符串，避免「提到黑名单」的说明性文字造成误判
    body = re.sub(r'"""[\s\S]*?"""', "", source)
    body = re.sub(r"#.*", "", body)

    assert "find_active_block" not in body
    assert "blocklist" not in body
    assert "不在黑名单中" not in body


@pytest.mark.asyncio
async def test_onebot11_kick_member_cannot_kick_self(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_session: Mock,
) -> None:
    """测试不能踢出自己"""
    mock_onebot11_bot.get_group_member_info = AsyncMock(
        return_value={"card": "", "nickname": ""}
    )

    with patch.object(kick_member_cmd, "finish") as mock_finish:
        await kick_module.onebot11_kick_member(
            user=mock_onebot11_event.user_id,  # 踢自己
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    assert "不能踢出自己" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_kick_member_cannot_kick_bot(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_session: Mock,
) -> None:
    """测试不能踢出机器人"""
    mock_onebot11_bot.self_id = _TEST_BOT_SELF_ID
    mock_onebot11_bot.get_group_member_info = AsyncMock(
        return_value={"card": "", "nickname": ""}
    )

    with patch.object(kick_member_cmd, "finish") as mock_finish:
        await kick_module.onebot11_kick_member(
            user=int(_TEST_BOT_SELF_ID),  # 踢机器人
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    assert "不能踢出机器人" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_kick_member_action_failed(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
    mock_session: Mock,
) -> None:
    """测试踢出操作失败的情况（权限检查通过，但 API 调用失败）"""
    from nonebot.adapters.onebot.v11.exception import ActionFailed

    mock_onebot11_bot.set_group_kick = AsyncMock(side_effect=ActionFailed())
    # check_target_privilege: 已由 autouse fixture mock 为返回 True
    # check_bot_privilege: 机器人为管理员（通过）
    mock_onebot11_bot.get_group_member_info = AsyncMock(side_effect=[{"role": "admin"}])

    with patch.object(kick_member_cmd, "finish") as mock_finish:
        await kick_module.onebot11_kick_member(
            user=mock_at,
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
            session=mock_session,
        )

    assert "踢出群成员失败" in finish_text(mock_finish)


def test_lazy_export_resolves_onebot11_kick_member() -> None:
    """__getattr__ 成功解析懒导出的 onebot11_kick_member 并缓存到 globals()。"""
    kick_commands_module.__dict__.pop("onebot11_kick_member", None)

    value = kick_commands_module.onebot11_kick_member

    assert value is kick_module.onebot11_kick_member
    assert kick_commands_module.__dict__.get("onebot11_kick_member") is value


def test_lazy_export_raises_attribute_error_for_unknown_name() -> None:
    """__getattr__ 对不在 _LAZY_EXPORTS 中的属性名抛出 AttributeError。"""
    with pytest.raises(AttributeError):
        _ = kick_commands_module.nonexistent_lazy_export
