from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from nonebot.adapters.telegram.exception import ActionFailed
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default import (
    moderation,
)
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
    async def get_chat_member(*, chat_id: int, user_id: int) -> SimpleNamespace:
        del chat_id
        if user_id == 999:
            return SimpleNamespace(
                status="administrator",
                can_restrict_members=True,
            )
        return SimpleNamespace(status="member")

    return SimpleNamespace(
        self_id="999",
        ban_chat_member=AsyncMock(return_value=True),
        unban_chat_member=AsyncMock(return_value=True),
        get_chat_member=AsyncMock(side_effect=get_chat_member),
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


@pytest.fixture(autouse=True)
def moderation_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(
        enabled=True,
        defaults={"block_duration": None, "default_reason": "违反群规"},
    )
    monkeypatch.setattr(
        moderation,
        "get_handle_config_manager",
        lambda: SimpleNamespace(get_config=AsyncMock(return_value=config)),
    )
    monkeypatch.setattr(
        moderation,
        "find_active_block",
        AsyncMock(return_value=SimpleNamespace()),
    )
    monkeypatch.setattr(moderation, "upsert_block", AsyncMock())
    monkeypatch.setattr(
        moderation,
        "remove_block",
        AsyncMock(return_value=(1, True)),
    )
    monkeypatch.setattr(moderation, "_record_telegram_audit", AsyncMock())


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


@pytest.mark.asyncio
async def test_telegram_block_writes_blocklist_and_audit(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    upsert = AsyncMock()
    audit = AsyncMock()
    monkeypatch.setattr(moderation, "upsert_block", upsert)
    monkeypatch.setattr(moderation, "_record_telegram_audit", audit)
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.moderation.block_member_cmd.finish",
        AsyncMock(),
    )

    await telegram_block_member(42, 60, bot, event, session, reason="spam")

    upsert_call = upsert.await_args
    assert upsert_call is not None
    request = upsert_call.args[1]
    assert request.platform_id == "telegram"
    assert request.adapter_id == "~telegram"
    assert request.bot_id == "999"
    assert request.scope == "group"
    assert request.group_id == -1001
    assert request.user_id == 42
    assert request.operator_id == 10
    assert request.reason == "spam"
    assert request.expires_at is not None
    audit_call = audit.await_args
    assert audit_call is not None
    audit_request = audit_call.args[3]
    assert audit_request.action == "block_member"
    assert audit_request.target_user_id == 42
    assert audit_request.duration == 60


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        (0, None),
        (-5, None),
        (60, 60),
        (10, 30),  # Telegram treats <30s as permanent; raise to 30s minimum
        (29, 30),
        (30, 30),
        ("60", 60),  # string values from TOML are coerced
        ("invalid", None),
        ("0", None),
        (True, None),  # booleans are not valid durations
        (3.5, None),  # non-integer numerics are rejected
    ],
)
def test_normalized_block_duration(raw: object, expected: int | None) -> None:
    assert moderation._normalized_block_duration(raw) == expected


@pytest.mark.asyncio
async def test_telegram_block_api_failure_rolls_back_and_skips_audit(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    bot.ban_chat_member.side_effect = ActionFailed("denied")
    upsert = AsyncMock()
    audit = AsyncMock()
    monkeypatch.setattr(moderation, "upsert_block", upsert)
    monkeypatch.setattr(moderation, "_record_telegram_audit", audit)
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.moderation.block_member_cmd.finish",
        AsyncMock(),
    )

    await telegram_block_member(42, None, bot, event, session)

    upsert.assert_awaited_once()
    session.rollback.assert_awaited_once()
    audit.assert_not_awaited()


@pytest.mark.asyncio
async def test_telegram_moderation_permission_failure_does_not_write_database(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    async def get_chat_member(*, chat_id: int, user_id: int) -> SimpleNamespace:
        del chat_id
        if user_id == 999:
            return SimpleNamespace(status="member")
        return SimpleNamespace(status="member")

    bot.get_chat_member = AsyncMock(side_effect=get_chat_member)
    upsert = AsyncMock()
    monkeypatch.setattr(moderation, "upsert_block", upsert)
    finish = AsyncMock()
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.moderation.block_member_cmd.finish",
        finish,
    )

    await telegram_block_member(42, None, bot, event, session)

    upsert.assert_not_awaited()
    bot.ban_chat_member.assert_not_awaited()
    finish.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_kick_requires_active_lingchu_block(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    monkeypatch.setattr(moderation, "find_active_block", AsyncMock(return_value=None))
    finish = AsyncMock()
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.moderation.kick_member_cmd.finish",
        finish,
    )

    await telegram_kick_member(42, bot, event, session)

    bot.ban_chat_member.assert_not_awaited()
    finish.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_unblock_removes_block_and_records_audit(
    monkeypatch: pytest.MonkeyPatch,
    bot: SimpleNamespace,
    event: SimpleNamespace,
    session: AsyncMock,
) -> None:
    remove = AsyncMock(return_value=(1, True))
    audit = AsyncMock()
    monkeypatch.setattr(moderation, "remove_block", remove)
    monkeypatch.setattr(moderation, "_record_telegram_audit", audit)
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.handle.telegram.adapters.default.moderation.unblock_member_cmd.finish",
        AsyncMock(),
    )

    await telegram_unblock_member(42, bot, event, session, reason="restored")

    remove.assert_awaited_once_with(
        session,
        platform_id="telegram",
        adapter_id="~telegram",
        bot_id="999",
        scope="group",
        group_id=-1001,
        user_id=42,
    )
    audit_call = audit.await_args
    assert audit_call is not None
    audit_request = audit_call.args[3]
    assert audit_request.action == "unblock_member"
    assert audit_request.target_user_id == 42
    assert audit_request.reason == "restored"
