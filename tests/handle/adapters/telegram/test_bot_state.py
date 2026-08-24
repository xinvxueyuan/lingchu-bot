from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default import (
    bot_state,
    import_handle,
)


@pytest.mark.asyncio
async def test_telegram_handler_entry_point_imports_all_modules() -> None:
    await import_handle()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("handler_name", "setter_name", "expected"),
    [
        ("telegram_bot_silence", "set_global_silent_mode", {"silent": True}),
        ("telegram_bot_speak", "set_global_silent_mode", {"silent": False}),
        ("telegram_bot_boot", "set_global_handle_active", {"active": True}),
        ("telegram_bot_shutdown", "set_global_handle_active", {"active": False}),
    ],
)
async def test_telegram_bot_state_handlers_update_global_state(
    monkeypatch: pytest.MonkeyPatch,
    handler_name: str,
    setter_name: str,
    expected: dict[str, bool],
) -> None:
    setter = AsyncMock()
    monkeypatch.setattr(bot_state, setter_name, setter)
    command = getattr(bot_state, f"{handler_name.removeprefix('telegram_')}_cmd")
    monkeypatch.setattr(command, "finish", AsyncMock())
    bot = SimpleNamespace()
    event = SimpleNamespace()
    session = AsyncMock()

    await getattr(bot_state, handler_name)(bot, event, session)

    setter.assert_called_once_with(**expected)
