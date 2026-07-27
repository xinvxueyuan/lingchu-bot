from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default import (
    menu as telegram_menu_module,
)


@pytest.mark.asyncio
async def test_telegram_menu_filters_by_allowed_command_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        telegram_menu_module,
        "allowed_command_keys",
        AsyncMock(return_value=frozenset({"kick_member"})),
    )
    finish = AsyncMock()
    monkeypatch.setattr(telegram_menu_module.menu_cmd, "finish", finish)

    await telegram_menu_module.telegram_menu(
        SimpleNamespace(),
        AsyncMock(),
        SimpleNamespace(),
    )

    assert finish.await_args is not None
    rendered = finish.await_args.kwargs["message"]
    assert "成员管理" in rendered
    assert "远程管理" not in rendered


@pytest.mark.asyncio
async def test_telegram_menu_without_event_keeps_context_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    finish = AsyncMock()
    monkeypatch.setattr(telegram_menu_module.menu_cmd, "finish", finish)

    await telegram_menu_module.telegram_menu(SimpleNamespace(), AsyncMock())

    assert finish.await_args is not None
    assert "灵初功能菜单" in finish.await_args.kwargs["message"]
