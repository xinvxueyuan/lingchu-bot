from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.group.block import (
    block_member_cmd,
    clear_blocklist_cmd,
    global_block_member_cmd,
    global_clear_blocklist_cmd,
    global_unblock_member_cmd,
    unblock_member_cmd,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.group.command_triggers import (
    COMMAND_TRIGGERS,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.onebot.v11.default.group import (
    block as block_module,
)
from tests.handle.commands.group.conftest import finish_text


@pytest.mark.asyncio
async def test_onebot11_block_member_stores_record_and_kicks(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
) -> None:
    mock_onebot11_bot.set_group_kick = AsyncMock()

    with (
        patch.object(block_module, "upsert_block", AsyncMock()) as upsert_mock,
        patch.object(block_member_cmd, "finish") as mock_finish,
    ):
        await block_module.onebot11_block_member(
            user=mock_at,
            duration=None,
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    upsert_mock.assert_awaited_once()
    assert upsert_mock.call_args.kwargs["scope"] == "group"
    assert upsert_mock.call_args.kwargs["reason"] == "违反群规「默认」"
    assert upsert_mock.call_args.kwargs["expires_at"] is None
    mock_onebot11_bot.set_group_kick.assert_awaited_once_with(
        group_id=mock_onebot11_event.group_id,
        user_id=987654321,
        reject_add_request=True,
    )
    assert "已拉黑并踢出" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_global_block_member_uses_global_scope_and_kicks(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
) -> None:
    mock_onebot11_bot.set_group_kick = AsyncMock()

    with (
        patch.object(block_module, "upsert_block", AsyncMock()) as upsert_mock,
        patch.object(global_block_member_cmd, "finish"),
    ):
        await block_module.onebot11_global_block_member(
            user=mock_at,
            duration=60,
            reason="spam",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    assert upsert_mock.call_args.kwargs["scope"] == "global"
    assert upsert_mock.call_args.kwargs["reason"] == "spam"
    assert upsert_mock.call_args.kwargs["expires_at"] is not None
    mock_onebot11_bot.set_group_kick.assert_awaited_once_with(
        group_id=mock_onebot11_event.group_id,
        user_id=987654321,
        reject_add_request=True,
    )


@pytest.mark.asyncio
async def test_onebot11_unblock_member_removes_group_entry(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
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
        )

    assert remove_mock.call_args.kwargs["scope"] == "group"
    assert "删除记录: 1" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_global_unblock_member_removes_global_entry(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
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
        )

    assert remove_mock.call_args.kwargs["scope"] == "global"


@pytest.mark.asyncio
async def test_onebot11_clear_blocklist_clears_group_scope(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
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
        )

    assert clear_mock.call_args.kwargs["scope"] == "group"
    assert "删除记录: 2" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_global_clear_blocklist_clears_global_scope(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
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
        )

    assert clear_mock.call_args.kwargs["scope"] == "global"


@pytest.mark.asyncio
async def test_blocklisted_group_message_triggers_kick(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
) -> None:
    mock_onebot11_bot.set_group_kick = AsyncMock()

    with patch.object(
        block_module,
        "find_active_block",
        AsyncMock(return_value=SimpleNamespace(reason="blocked")),
    ):
        await block_module.onebot11_kick_blocklisted_message(
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.set_group_kick.assert_awaited_once_with(
        group_id=mock_onebot11_event.group_id,
        user_id=mock_onebot11_event.user_id,
        reject_add_request=True,
    )


@pytest.mark.asyncio
async def test_non_blocklisted_group_message_does_not_kick(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
) -> None:
    mock_onebot11_bot.set_group_kick = AsyncMock()

    with patch.object(
        block_module,
        "find_active_block",
        AsyncMock(return_value=None),
    ):
        await block_module.onebot11_kick_blocklisted_message(
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    mock_onebot11_bot.set_group_kick.assert_not_awaited()


@pytest.mark.asyncio
async def test_blocklisted_group_add_request_is_rejected(
    mock_onebot11_bot: MagicMock,
) -> None:
    event = SimpleNamespace(
        sub_type="add",
        group_id=123456789,
        user_id=987654321,
        flag="flag-1",
    )
    mock_onebot11_bot.set_group_add_request = AsyncMock()

    with patch.object(
        block_module,
        "find_active_block",
        AsyncMock(return_value=SimpleNamespace(reason="blocked")),
    ):
        await block_module.onebot11_reject_blocklisted_group_request(
            bot=mock_onebot11_bot,
            event=event,
        )

    mock_onebot11_bot.set_group_add_request.assert_awaited_once_with(
        flag="flag-1",
        sub_type="add",
        approve=False,
        reason="blocked",
    )


@pytest.mark.asyncio
async def test_invite_request_is_ignored(mock_onebot11_bot: MagicMock) -> None:
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
        )

    find_mock.assert_not_awaited()
    mock_onebot11_bot.set_group_add_request.assert_not_awaited()


def test_block_command_triggers_are_minimal() -> None:
    assert COMMAND_TRIGGERS["block_member"].english_aliases == {"block-member"}
    assert COMMAND_TRIGGERS["global_block_member"].chinese_aliases == {"全局拉黑用户"}
    assert COMMAND_TRIGGERS["clear_blocklist"].english_aliases == set()
