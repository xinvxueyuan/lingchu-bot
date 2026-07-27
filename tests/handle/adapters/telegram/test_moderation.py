from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from nonebot.adapters.telegram.exception import ActionFailed
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.moderation import (
    telegram_block_member,
    telegram_kick_member,
    telegram_leave_group,
    telegram_set_group_name,
    telegram_set_member_admin,
    telegram_unblock_member,
    telegram_unset_member_admin,
)


@pytest.fixture
def bot() -> SimpleNamespace:
    return SimpleNamespace(
        self_id="999",
        ban_chat_member=AsyncMock(return_value=True),
        unban_chat_member=AsyncMock(return_value=True),
        promote_chat_member=AsyncMock(return_value=True),
        set_chat_title=AsyncMock(return_value=True),
        leave_chat=AsyncMock(return_value=True),
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
async def test_telegram_kick_bans_then_unbans(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.moderation.kick_member_cmd.finish",
        AsyncMock(),
    )

    await telegram_kick_member(42, bot, event, session)

    bot.ban_chat_member.assert_awaited_once_with(
        chat_id=-1001,
        user_id=42,
        revoke_messages=False,
    )
    bot.unban_chat_member.assert_awaited_once_with(
        chat_id=-1001,
        user_id=42,
        only_if_banned=True,
    )


@pytest.mark.asyncio
async def test_telegram_block_keeps_member_banned(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.moderation.block_member_cmd.finish",
        AsyncMock(),
    )

    await telegram_block_member(42, None, bot, event, session)

    assert bot.ban_chat_member.await_args.kwargs == {
        "chat_id": -1001,
        "user_id": 42,
        "until_date": None,
        "revoke_messages": True,
    }
    bot.unban_chat_member.assert_not_awaited()


@pytest.mark.asyncio
async def test_telegram_admin_uses_explicit_permissions(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.moderation.set_group_member_admin_cmd.finish",
        AsyncMock(),
    )

    await telegram_set_member_admin(42, bot, event, session)

    kwargs = bot.promote_chat_member.await_args.kwargs
    assert kwargs["chat_id"] == -1001
    assert kwargs["user_id"] == 42
    assert kwargs["can_restrict_members"] is True


@pytest.mark.asyncio
async def test_telegram_group_name_calls_native_api(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.moderation.set_group_name_cmd.finish",
        AsyncMock(),
    )

    await telegram_set_group_name("Lingchu", bot, event, session)

    bot.set_chat_title.assert_awaited_once_with(chat_id=-1001, title="Lingchu")


@pytest.mark.asyncio
async def test_telegram_kick_reports_rejected_api_call(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    bot.ban_chat_member.side_effect = ActionFailed("denied")
    finish = AsyncMock()
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.moderation.kick_member_cmd.finish",
        finish,
    )

    await telegram_kick_member(42, bot, event, session)

    finish.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_unblock_and_demote_use_native_apis(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    unblock_finish = AsyncMock()
    demote_finish = AsyncMock()
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.moderation.unblock_member_cmd.finish",
        unblock_finish,
    )
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.moderation.unset_group_member_admin_cmd.finish",
        demote_finish,
    )

    await telegram_unblock_member(42, bot, event, session)
    await telegram_unset_member_admin(42, bot, event, session)

    bot.unban_chat_member.assert_awaited_once_with(
        chat_id=-1001,
        user_id=42,
        only_if_banned=True,
    )
    assert bot.promote_chat_member.await_args.kwargs["can_manage_chat"] is False


@pytest.mark.asyncio
async def test_telegram_leave_group_calls_native_api(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.moderation.quit_group_cmd.finish",
        AsyncMock(),
    )

    await telegram_leave_group(bot, event, session)

    bot.leave_chat.assert_awaited_once_with(chat_id=-1001)
