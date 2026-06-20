from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    kick as kick_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.kick import (
    kick_member_cmd,
)
from tests.handle.commands.conftest import finish_text

# 测试用 user_id 常量（避免 PLR2004 魔数值警告）
# 注意：不能与 conftest.py 中 mock_onebot11_event.user_id (111222333) 相同
_TEST_KICK_USER_ID = 555666777
_TEST_BOT_SELF_ID = "999999"


@pytest.fixture(autouse=True)
def _mock_fire_and_forget():
    """避免审计记录触发后台任务和数据库调用。"""
    captured: list[tuple[Any, str]] = []

    def _spy(coro: Any, *, name: str = "fire_and_forget") -> Any:
        captured.append((coro, name))
        return MagicMock()

    with patch.object(kick_module, "fire_and_forget", side_effect=_spy):
        yield
    for coro, _name in captured:
        coro.close()


@pytest.mark.asyncio
async def test_onebot11_kick_member_with_at(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
) -> None:
    """测试使用 At 对象踢出群成员（用户在黑名单中）"""
    mock_onebot11_bot.set_group_kick = AsyncMock()
    # check_target_privilege: 目标为普通成员（通过）
    # check_bot_privilege: 机器人为管理员（通过）
    mock_onebot11_bot.get_group_member_info = AsyncMock(
        side_effect=[{"role": "member"}, {"role": "admin"}]
    )

    with (
        patch.object(
            kick_module,
            "find_active_block",
            AsyncMock(return_value=SimpleNamespace(reason="测试黑名单")),
        ),
        patch.object(kick_member_cmd, "finish") as mock_finish,
    ):
        await kick_module.onebot11_kick_member(
            user=mock_at,
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

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
) -> None:
    """测试直接传入 user_id (int) 踢出群成员（用户在黑名单中）"""
    mock_onebot11_bot.set_group_kick = AsyncMock()
    # resolve_user: 获取用户名片
    # check_target_privilege: 目标为普通成员（通过）
    # check_bot_privilege: 机器人为管理员（通过）
    mock_onebot11_bot.get_group_member_info = AsyncMock(
        side_effect=[
            {"card": "测试用户", "nickname": "TestUser"},
            {"role": "member"},
            {"role": "admin"},
        ]
    )

    with (
        patch.object(
            kick_module,
            "find_active_block",
            AsyncMock(return_value=SimpleNamespace(reason="测试黑名单")),
        ),
        patch.object(kick_member_cmd, "finish") as mock_finish,
    ):
        await kick_module.onebot11_kick_member(
            user=_TEST_KICK_USER_ID,
            reason="测试原因",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.set_group_kick.assert_awaited_once_with(
        group_id=mock_onebot11_event.group_id,
        user_id=_TEST_KICK_USER_ID,
        reject_add_request=False,
    )
    assert "已踢出群成员" in finish_text(mock_finish)
    assert "测试原因" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_kick_member_not_in_blocklist(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
) -> None:
    """测试用户不在黑名单中时拒绝踢出"""
    mock_onebot11_bot.set_group_kick = AsyncMock()
    with (
        patch.object(kick_module, "find_active_block", AsyncMock(return_value=None)),
        patch.object(kick_member_cmd, "finish") as mock_finish,
    ):
        await kick_module.onebot11_kick_member(
            user=mock_at,
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    assert "不在黑名单中" in finish_text(mock_finish)
    # 确保没有调用踢出 API
    mock_onebot11_bot.set_group_kick.assert_not_called()


@pytest.mark.asyncio
async def test_onebot11_kick_member_database_error(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
) -> None:
    """测试查询黑名单时数据库异常"""
    from src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud import DatabaseError

    mock_onebot11_bot.set_group_kick = AsyncMock()
    with (
        patch.object(
            kick_module,
            "find_active_block",
            AsyncMock(side_effect=DatabaseError("数据库连接失败")),
        ),
        patch.object(kick_member_cmd, "finish") as mock_finish,
    ):
        await kick_module.onebot11_kick_member(
            user=mock_at,
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    assert "查询黑名单失败" in finish_text(mock_finish)
    # 确保没有调用踢出 API
    mock_onebot11_bot.set_group_kick.assert_not_called()


@pytest.mark.asyncio
async def test_onebot11_kick_member_cannot_kick_self(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
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
        )

    assert "不能踢出自己" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_kick_member_cannot_kick_bot(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
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
        )

    assert "不能踢出机器人" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_kick_member_action_failed(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
) -> None:
    """测试踢出操作失败的情况（用户已在黑名单中，但 API 调用失败）"""
    from nonebot.adapters.onebot.v11.exception import ActionFailed

    mock_onebot11_bot.set_group_kick = AsyncMock(side_effect=ActionFailed())
    # check_target_privilege: 目标为普通成员（通过）
    # check_bot_privilege: 机器人为管理员（通过）
    mock_onebot11_bot.get_group_member_info = AsyncMock(
        side_effect=[{"role": "member"}, {"role": "admin"}]
    )

    with (
        patch.object(
            kick_module,
            "find_active_block",
            AsyncMock(return_value=SimpleNamespace(reason="测试黑名单")),
        ),
        patch.object(kick_member_cmd, "finish") as mock_finish,
    ):
        await kick_module.onebot11_kick_member(
            user=mock_at,
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    assert "踢出群成员失败" in finish_text(mock_finish)
