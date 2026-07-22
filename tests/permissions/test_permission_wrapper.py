from collections.abc import Awaitable, Callable
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands import common
from src.plugins.nonebot_plugin_lingchu_bot.permissions import PermissionDecision


class FakeCommand:
    def __init__(self) -> None:
        self.registered: Callable[..., Awaitable[Any]] | None = None
        self.parameterless: list[Any] = []
        self.finished = AsyncMock()

    def handle(
        self,
        *,
        parameterless: list[Any] | None = None,
    ) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
        self.parameterless = parameterless or []

        def register(
            func: Callable[..., Awaitable[Any]],
        ) -> Callable[..., Awaitable[Any]]:
            self.registered = func
            return func

        return register

    async def finish(self, message: str) -> None:
        await self.finished(message)


class FakeBot:
    adapter = object()


class FakeEvent:
    user_id = 42


@pytest.mark.asyncio
async def test_selected_adapter_handle_denies_before_business_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = FakeCommand()
    handler = AsyncMock()
    session = Mock()
    bot = FakeBot()
    event = FakeEvent()
    permission = AsyncMock(
        return_value=PermissionDecision(allowed=False, reason="anonymous")
    )
    monkeypatch.setattr(common, "is_adapter_enabled", lambda _adapter_id: True)
    monkeypatch.setattr(common, "check_permission", permission)

    returned = common.selected_adapter_handle(
        cast("Any", command),
        "~onebot.v11",
        "member_mute",
        bypass_gate=True,
        bypass_silent=True,
    )(handler)

    assert returned is handler
    assert command.registered is handler
    assert len(command.parameterless) == 1
    await command.parameterless[0].dependency(
        matcher=command,
        bot=bot,
        event=event,
        session=session,
    )

    permission.assert_awaited_once_with(session, "member_mute", bot, event)
    handler.assert_not_awaited()
    command.finished.assert_awaited_once_with("权限不足")


@pytest.mark.asyncio
async def test_selected_adapter_handle_allows_business_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = FakeCommand()
    handler = AsyncMock(return_value="ok")
    session = Mock()
    bot = FakeBot()
    event = FakeEvent()
    permission = AsyncMock(
        return_value=PermissionDecision(allowed=True, reason="granted")
    )
    monkeypatch.setattr(common, "is_adapter_enabled", lambda _adapter_id: True)
    monkeypatch.setattr(common, "check_permission", permission)

    common.selected_adapter_handle(
        cast("Any", command),
        "~onebot.v11",
        "member_mute",
        bypass_gate=True,
        bypass_silent=True,
    )(handler)

    assert command.registered is handler
    assert len(command.parameterless) == 1
    await command.parameterless[0].dependency(
        matcher=command,
        bot=bot,
        event=event,
        session=session,
    )
    assert command.registered is not None
    result = await command.registered(value=1)

    assert result == "ok"
    permission.assert_awaited_once_with(session, "member_mute", bot, event)
    handler.assert_awaited_once_with(value=1)
    command.finished.assert_not_awaited()
