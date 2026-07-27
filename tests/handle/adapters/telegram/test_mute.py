from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from nonebot.adapters.telegram.exception import ActionFailed
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.mute import (
    telegram_mute,
    telegram_unmute,
    telegram_whole_mute,
    telegram_whole_unmute,
)


@pytest.fixture
def bot() -> SimpleNamespace:
    return SimpleNamespace(
        self_id="999",
        restrict_chat_member=AsyncMock(return_value=True),
        set_chat_permissions=AsyncMock(return_value=True),
    )


@pytest.fixture
def event() -> SimpleNamespace:
    return SimpleNamespace(
        chat=SimpleNamespace(id=-1001, type="supergroup"),
        from_=SimpleNamespace(id=10),
    )


@pytest.fixture
def session() -> AsyncMock:
    value = AsyncMock()
    value.add = MagicMock()
    return value


@pytest.mark.asyncio
async def test_telegram_mute_restricts_target(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.mute.get_handle_config_manager",
        lambda: SimpleNamespace(
            get_config=AsyncMock(
                return_value=SimpleNamespace(
                    enabled=True,
                    defaults={"mute_duration": 300},
                )
            )
        ),
    )
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.mute.member_mute_cmd.finish",
        AsyncMock(),
    )

    await telegram_mute(42, 60, bot, event, session)

    kwargs = bot.restrict_chat_member.await_args.kwargs
    assert kwargs["chat_id"] == -1001
    assert kwargs["user_id"] == 42
    assert kwargs["permissions"].can_send_messages is False
    assert isinstance(kwargs["until_date"], int)


@pytest.mark.asyncio
async def test_telegram_unmute_restores_send_permissions(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.mute.get_handle_config_manager",
        lambda: SimpleNamespace(
            get_config=AsyncMock(
                return_value=SimpleNamespace(enabled=True, defaults={})
            )
        ),
    )
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.mute.member_unmute_cmd.finish",
        AsyncMock(),
    )

    await telegram_unmute(42, bot, event, session)

    permissions = bot.restrict_chat_member.await_args.kwargs["permissions"]
    assert permissions.can_send_messages is True


@pytest.mark.asyncio
async def test_telegram_mute_reports_rejected_api_call(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    bot.restrict_chat_member.side_effect = ActionFailed("denied")
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.mute.get_handle_config_manager",
        lambda: SimpleNamespace(
            get_config=AsyncMock(
                return_value=SimpleNamespace(
                    enabled=True, defaults={"mute_duration": 300}
                )
            )
        ),
    )
    finish = AsyncMock()
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.mute.member_mute_cmd.finish",
        finish,
    )

    await telegram_mute(42, 60, bot, event, session)

    finish.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_mute_rejects_disabled_handle(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.mute.get_handle_config_manager",
        lambda: SimpleNamespace(
            get_config=AsyncMock(
                return_value=SimpleNamespace(enabled=False, defaults={})
            )
        ),
    )
    finish = AsyncMock()
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.mute.member_mute_cmd.finish",
        finish,
    )

    await telegram_mute(42, 60, bot, event, session)

    bot.restrict_chat_member.assert_not_awaited()
    finish.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("handler", "expected"),
    [(telegram_whole_mute, False), (telegram_whole_unmute, True)],
)
async def test_telegram_whole_mute_changes_chat_permissions(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
    handler: Callable[[Any, Any, Any], Awaitable[Any]],
    expected: object,
) -> None:
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.mute.get_handle_config_manager",
        lambda: SimpleNamespace(
            get_config=AsyncMock(
                return_value=SimpleNamespace(enabled=True, defaults={})
            )
        ),
    )
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.mute.whole_mute_cmd.finish",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.mute.whole_unmute_cmd.finish",
        AsyncMock(),
    )

    await handler(bot, event, session)

    permissions = bot.set_chat_permissions.await_args.kwargs["permissions"]
    assert permissions.can_send_messages is expected
