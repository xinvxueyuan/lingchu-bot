"""测试群成员设置与踢出命令 - OneBot11 群 API 映射覆盖"""

from unittest.mock import AsyncMock, MagicMock, patch

from nonebot.adapters.onebot.v11.exception import ActionFailed as OB11ActionFailed
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.handle_config_manager import (
    HandleConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    common as onebot11_common_module,
    member as onebot11_member_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.kick import (
    kick_member_cmd,
    onebot11_kick_member,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.member import (
    onebot11_set_group_member_admin,
    onebot11_set_group_member_card,
    onebot11_set_group_member_special_title,
    onebot11_unset_group_member_admin,
    set_group_member_admin_cmd,
    set_group_member_card_cmd,
    set_group_member_special_title_cmd,
)
from tests.handle.commands.conftest import finish_text


@pytest.fixture(autouse=True)
def _mock_record_audit_fire_and_forget():
    """避免审计记录触发后台任务和数据库调用。"""
    with patch.object(
        onebot11_member_module, "record_audit_fire_and_forget", new=AsyncMock()
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
        onebot11_member_module,
        "get_handle_config_manager",
        return_value=MockManager(),
    ):
        yield


@pytest.mark.asyncio
async def test_onebot11_set_group_member_card_calls_v11_api(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_onebot11_bot.set_group_card = AsyncMock()
    # check_target_privilege: 目标为普通成员（通过）
    # check_bot_privilege: 机器人为管理员（通过）
    mock_onebot11_bot.get_group_member_info = AsyncMock(
        side_effect=[{"role": "member"}, {"role": "admin"}]
    )

    with patch.object(set_group_member_card_cmd, "finish") as mock_finish:
        await onebot11_set_group_member_card(
            user=mock_at,
            card="新名片",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.set_group_card.assert_called_once_with(
        group_id=mock_onebot11_event.group_id, user_id=987654321, card="新名片"
    )
    assert "已设置群名片: 测试用户(987654321) -> 新名片" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_set_group_member_special_title_calls_v11_api(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_onebot11_bot.set_group_special_title = AsyncMock()
    # check_target_privilege: 目标为普通成员（通过）
    # check_bot_privilege: 机器人为管理员（通过）
    mock_onebot11_bot.get_group_member_info = AsyncMock(
        side_effect=[{"role": "member"}, {"role": "admin"}]
    )

    with patch.object(set_group_member_special_title_cmd, "finish") as mock_finish:
        await onebot11_set_group_member_special_title(
            user=mock_at,
            special_title="精英",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.set_group_special_title.assert_called_once_with(
        group_id=mock_onebot11_event.group_id,
        user_id=987654321,
        special_title="精英",
        duration=-1,
    )
    assert "已设置群头衔: 测试用户(987654321) -> 精英" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_set_group_member_admin_calls_v11_api(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_onebot11_bot.set_group_admin = AsyncMock()
    # check_target_privilege: 目标为普通成员（通过）
    # check_bot_privilege: 机器人为管理员（通过）
    mock_onebot11_bot.get_group_member_info = AsyncMock(
        side_effect=[{"role": "member"}, {"role": "admin"}]
    )

    with patch.object(set_group_member_admin_cmd, "finish") as mock_finish:
        await onebot11_set_group_member_admin(
            user=mock_at,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.set_group_admin.assert_called_once_with(
        group_id=mock_onebot11_event.group_id, user_id=987654321, enable=True
    )
    assert "设置群管理员: 测试用户(987654321)" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_set_group_member_admin_rejects_protected_target(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_onebot11_bot.set_group_admin = AsyncMock()

    with (
        patch.object(set_group_member_admin_cmd, "finish") as mock_finish,
        patch.object(
            onebot11_common_module,
            "find_active_subject_policy",
            new=AsyncMock(return_value=object()),
        ),
        patch.object(
            onebot11_common_module,
            "operator_is_superuser_onebot11",
            new=AsyncMock(return_value=False),
        ),
    ):
        await onebot11_set_group_member_admin(
            user=mock_at,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.set_group_admin.assert_not_called()
    assert "目标用户受白名单保护" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_unset_group_member_admin_calls_v11_api(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_onebot11_bot.set_group_admin = AsyncMock()
    # check_target_privilege: 目标为普通成员（通过）
    # check_bot_privilege: 机器人为管理员（通过）
    mock_onebot11_bot.get_group_member_info = AsyncMock(
        side_effect=[{"role": "member"}, {"role": "admin"}]
    )

    with patch.object(set_group_member_admin_cmd, "finish") as mock_finish:
        await onebot11_unset_group_member_admin(
            user=mock_at, bot=mock_onebot11_bot, event=mock_onebot11_event
        )

    mock_onebot11_bot.set_group_admin.assert_called_once_with(
        group_id=mock_onebot11_event.group_id, user_id=987654321, enable=False
    )
    assert "取消群管理员: 测试用户(987654321)" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_kick_member_calls_v11_api(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock, mock_at: MagicMock
) -> None:
    mock_onebot11_bot.set_group_kick = AsyncMock()
    # check_target_privilege: 目标为普通成员（通过）
    # check_bot_privilege: 机器人为管理员（通过）
    mock_onebot11_bot.get_group_member_info = AsyncMock(
        side_effect=[{"role": "member"}, {"role": "admin"}]
    )

    with patch.object(kick_member_cmd, "finish") as mock_finish:
        await onebot11_kick_member(
            user=mock_at,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.set_group_kick.assert_called_once_with(
        group_id=mock_onebot11_event.group_id,
        user_id=987654321,
        reject_add_request=False,
    )
    assert "已踢出群成员" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_target_user_onebot11_falls_back_to_api_nickname(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock, mock_at: MagicMock
) -> None:
    """At.display 与消息段名称都不存在时，通过 API 获取昵称。"""
    mock_onebot11_bot.set_group_card = AsyncMock()
    mock_at.display = None
    mock_onebot11_event.message = []
    # resolve_user: 获取用户名片
    # check_target_privilege: 目标为普通成员（通过）
    # check_bot_privilege: 机器人为管理员（通过）
    mock_onebot11_bot.get_group_member_info = AsyncMock(
        side_effect=[
            {"card": "", "nickname": "API昵称"},
            {"role": "member"},
            {"role": "admin"},
        ]
    )

    with patch.object(set_group_member_card_cmd, "finish") as mock_finish:
        await onebot11_set_group_member_card(
            user=mock_at,
            card="新名片",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    assert "API昵称(987654321)" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_target_user_onebot11_api_failure_falls_back_to_id(
    mock_onebot11_bot: MagicMock, mock_onebot11_event: MagicMock, mock_at: MagicMock
) -> None:
    """API 调用失败时回退到用户 ID。"""
    mock_onebot11_bot.set_group_card = AsyncMock()
    mock_at.display = None
    mock_onebot11_event.message = []
    mock_onebot11_bot.get_group_member_info = AsyncMock(
        side_effect=[OB11ActionFailed(), OB11ActionFailed(), {"role": "admin"}]
    )

    with patch.object(set_group_member_card_cmd, "finish") as mock_finish:
        await onebot11_set_group_member_card(
            user=mock_at,
            card="新名片",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    assert "已设置群名片: 987654321 -> 新名片" in finish_text(mock_finish)
