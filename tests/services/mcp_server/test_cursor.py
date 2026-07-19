from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.contracts import (
    BotAddress,
    ContractError,
    ConversationAddress,
    ErrorCode,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.cursor import (
    CursorBinding,
    CursorCodec,
    CursorPosition,
)

NOW = datetime(2026, 7, 18, 8, tzinfo=UTC)
BOT = BotAddress("qq", "~onebot.v11", "napcat", "bot-1")
CONVERSATION = ConversationAddress("group", "group-1")
BINDING = CursorBinding("principal-1", "grant-1", 3, BOT, CONVERSATION)
POSITION = CursorPosition(datetime(2026, 7, 18, 7, tzinfo=UTC), "42")
WINDOW_END = CursorPosition(datetime(2026, 7, 18, 8, tzinfo=UTC), "99")
STRONG_SECRET = b"0123456789abcdef0123456789abcdef"


def _codec() -> CursorCodec:
    return CursorCodec(secret=STRONG_SECRET, clock=lambda: NOW)


@pytest.mark.parametrize("secret", [b"", b"A" * 31, "A" * 32])
def test_cursor_codec_rejects_non_bytes_and_weak_secrets(secret: object) -> None:
    with pytest.raises(ValueError) as caught:
        CursorCodec(secret=cast("bytes", secret), clock=lambda: NOW)

    assert str(caught.value) == ""


def test_cursor_round_trip_is_opaque_and_bound() -> None:
    token = _codec().encode(BINDING, position=POSITION, window_end=WINDOW_END)

    state = _codec().decode(token, expected=BINDING)

    assert state.position == POSITION
    assert state.window_end == WINDOW_END
    assert "principal-1" not in token.value
    assert len(token.value) < 2048


@pytest.mark.parametrize("mutation", ["signature", "payload", "oversized"])
def test_cursor_rejects_tampering_and_bounded_input(mutation: str) -> None:
    token = _codec().encode(BINDING, position=POSITION, window_end=WINDOW_END).value
    if mutation == "signature":
        token = f"{token[:-1]}{'A' if token[-1] != 'A' else 'B'}"
    elif mutation == "payload":
        token = f"A{token[1:]}"
    else:
        token = "A" * 4097

    with pytest.raises(ContractError) as caught:
        _codec().decode(token, expected=BINDING)

    assert caught.value.code is ErrorCode.INVALID_CURSOR


@pytest.mark.parametrize(
    "expected",
    [
        CursorBinding("principal-2", "grant-1", 3, BOT, CONVERSATION),
        CursorBinding("principal-1", "grant-2", 3, BOT, CONVERSATION),
        CursorBinding(
            "principal-1", "grant-1", 3, BOT, ConversationAddress("group", "group-2")
        ),
        CursorBinding("principal-1", "grant-1", 3, BOT, CONVERSATION, "other-query"),
    ],
)
def test_cursor_rejects_principal_query_and_resource_mismatch(
    expected: CursorBinding,
) -> None:
    token = _codec().encode(BINDING, position=POSITION, window_end=WINDOW_END)

    with pytest.raises(ContractError) as caught:
        _codec().decode(token, expected=expected)

    assert caught.value.code is ErrorCode.INVALID_CURSOR


def test_cursor_reports_grant_revision_change_as_expired() -> None:
    token = _codec().encode(BINDING, position=POSITION, window_end=WINDOW_END)
    revised = CursorBinding("principal-1", "grant-1", 4, BOT, CONVERSATION)

    with pytest.raises(ContractError) as caught:
        _codec().decode(token, expected=revised)

    assert caught.value.code is ErrorCode.CURSOR_EXPIRED


def test_cursor_reports_time_expiry() -> None:
    codec = CursorCodec(
        secret=STRONG_SECRET,
        ttl_seconds=60,
        clock=lambda: NOW,
    )
    token = codec.encode(BINDING, position=POSITION, window_end=WINDOW_END)
    expired_codec = CursorCodec(
        secret=STRONG_SECRET,
        ttl_seconds=60,
        clock=lambda: datetime(2026, 7, 18, 8, 1, 1, tzinfo=UTC),
    )

    with pytest.raises(ContractError) as caught:
        expired_codec.decode(token, expected=BINDING)

    assert caught.value.code is ErrorCode.CURSOR_EXPIRED
