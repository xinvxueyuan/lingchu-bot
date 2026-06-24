from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    protect as protect_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.protect import (
    global_protect_member_cmd,
    global_unprotect_member_cmd,
    protect_member_cmd,
    unprotect_member_cmd,
)
from tests.handle.commands.conftest import finish_text

_TEST_USER_ID = 111222333
_MOCK_AT_TARGET = 987654321


@pytest.fixture(autouse=True)
def _mock_record_audit_fire_and_forget():
    with patch.object(protect_module, "record_audit_fire_and_forget", new=AsyncMock()):
        yield


@pytest.fixture(autouse=True)
def _mock_superuser():
    with patch.object(
        protect_module,
        "operator_is_superuser_onebot11",
        new=AsyncMock(return_value=True),
    ):
        yield


@pytest.mark.asyncio
async def test_onebot11_protect_member_upserts_group_policy(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
) -> None:
    with (
        patch.object(protect_module, "upsert_subject_policy", AsyncMock()) as upsert,
        patch.object(protect_member_cmd, "finish") as mock_finish,
    ):
        await protect_module.onebot11_protect_member(
            user=mock_at,
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    request = upsert.call_args.args[0]
    assert request.policy_type == "protected"
    assert request.scope == "group"
    assert request.group_id == mock_onebot11_event.group_id
    assert request.user_id == _MOCK_AT_TARGET
    assert request.operator_id == mock_onebot11_event.user_id
    assert request.expires_at is None
    assert "已拉白" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_global_protect_member_upserts_global_policy(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
) -> None:
    with (
        patch.object(protect_module, "upsert_subject_policy", AsyncMock()) as upsert,
        patch.object(global_protect_member_cmd, "finish"),
    ):
        await protect_module.onebot11_global_protect_member(
            user=mock_at,
            reason="vip",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    request = upsert.call_args.args[0]
    assert request.policy_type == "protected"
    assert request.scope == "global"
    assert request.reason == "vip"


@pytest.mark.asyncio
async def test_onebot11_unprotect_member_removes_group_policy(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
) -> None:
    with (
        patch.object(
            protect_module,
            "remove_subject_policy",
            AsyncMock(return_value=(1, True)),
        ) as remove,
        patch.object(unprotect_member_cmd, "finish") as mock_finish,
    ):
        await protect_module.onebot11_unprotect_member(
            user=mock_at,
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    assert remove.call_args.kwargs["policy_type"] == "protected"
    assert remove.call_args.kwargs["scope"] == "group"
    assert remove.call_args.kwargs["user_id"] == _MOCK_AT_TARGET
    assert "删除记录: 1" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_global_unprotect_member_removes_global_policy(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
    mock_at: MagicMock,
) -> None:
    with (
        patch.object(
            protect_module,
            "remove_subject_policy",
            AsyncMock(return_value=(1, True)),
        ) as remove,
        patch.object(global_unprotect_member_cmd, "finish"),
    ):
        await protect_module.onebot11_global_unprotect_member(
            user=mock_at,
            reason="reset",
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    assert remove.call_args.kwargs["policy_type"] == "protected"
    assert remove.call_args.kwargs["scope"] == "global"


@pytest.mark.asyncio
async def test_non_superuser_cannot_protect_member(
    mock_onebot11_bot: MagicMock,
    mock_onebot11_event: MagicMock,
) -> None:
    with (
        patch.object(
            protect_module,
            "operator_is_superuser_onebot11",
            AsyncMock(return_value=False),
        ),
        patch.object(protect_module, "upsert_subject_policy", AsyncMock()) as upsert,
        patch.object(protect_member_cmd, "finish") as mock_finish,
    ):
        await protect_module.onebot11_protect_member(
            user=_TEST_USER_ID,
            reason=None,
            bot=mock_onebot11_bot,
            event=mock_onebot11_event,
        )

    upsert.assert_not_awaited()
    assert "权限不足" in finish_text(mock_finish)
