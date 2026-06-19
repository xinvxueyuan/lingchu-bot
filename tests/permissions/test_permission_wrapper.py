from collections.abc import Awaitable, Callable
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands import common
from src.plugins.nonebot_plugin_lingchu_bot.permissions import PermissionDecision


class FakeCommand:
    def __init__(self) -> None:
        self.registered: Callable[..., Awaitable[Any]] | None = None
        self.finished = AsyncMock()

    def handle(
        self,
    ) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
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
    monkeypatch.setattr(common, "is_adapter_enabled", lambda _adapter_id: True)
    monkeypatch.setattr(
        common,
        "check_permission",
        AsyncMock(return_value=PermissionDecision(allowed=False, reason="anonymous")),
    )

    returned = common.selected_adapter_handle(
        cast("Any", command), "~onebot.v11", "member_mute"
    )(handler)

    assert returned is handler
    assert command.registered is not None
    await command.registered(bot=FakeBot(), event=FakeEvent())

    handler.assert_not_awaited()
    command.finished.assert_awaited_once_with("权限不足")


@pytest.mark.asyncio
async def test_selected_adapter_handle_allows_business_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = FakeCommand()
    handler = AsyncMock(return_value="ok")
    monkeypatch.setattr(common, "is_adapter_enabled", lambda _adapter_id: True)
    monkeypatch.setattr(
        common,
        "check_permission",
        AsyncMock(return_value=PermissionDecision(allowed=True, reason="granted")),
    )

    common.selected_adapter_handle(cast("Any", command), "~onebot.v11", "member_mute")(
        handler
    )

    assert command.registered is not None
    result = await command.registered(bot=FakeBot(), event=FakeEvent(), value=1)

    assert result == "ok"
    handler.assert_awaited_once()
    command.finished.assert_not_awaited()
