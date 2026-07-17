from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.mcp_confirmation import (
    CriticalConfirmationManager,
    CriticalConfirmationReply,
    CriticalConfirmationRequest,
)


def _now() -> datetime:
    return datetime(2026, 7, 17, tzinfo=UTC)


def test_same_actor_session_and_exact_call_consumes_confirmation_once() -> None:
    manager = CriticalConfirmationManager(clock=_now)
    state = manager.create(
        CriticalConfirmationRequest(
            actor_uid="user-1",
            session_id="group_1_user_1",
            server_name="ops",
            tool_name="restart",
            arguments={"service": "bot", "force": False},
            ttl=timedelta(seconds=30),
        )
    )
    reply = CriticalConfirmationReply(
        actor_uid="user-1",
        session_id="group_1_user_1",
        text="confirm",
    )

    assert manager.consume(
        state,
        reply,
        server_name="ops",
        tool_name="restart",
        arguments={"force": False, "service": "bot"},
    )
    assert not manager.consume(
        state,
        reply,
        server_name="ops",
        tool_name="restart",
        arguments={"force": False, "service": "bot"},
    )


def test_reply_mismatch_expiry_cancellation_and_new_manager_deny() -> None:
    current = _now()
    manager = CriticalConfirmationManager(clock=lambda: current)
    state = manager.create(
        CriticalConfirmationRequest(
            actor_uid="user-1",
            session_id="session-1",
            server_name="ops",
            tool_name="restart",
            arguments={"force": False},
            ttl=timedelta(seconds=1),
        )
    )

    for reply in (
        CriticalConfirmationReply("user-1", "session-1", "yes"),
        CriticalConfirmationReply("user-2", "session-1", "confirm"),
        CriticalConfirmationReply("user-1", "session-2", "confirm"),
    ):
        assert not manager.consume(
            state,
            reply,
            server_name="ops",
            tool_name="restart",
            arguments={"force": False},
        )

    assert not manager.consume(
        state,
        CriticalConfirmationReply("user-1", "session-1", "confirm"),
        server_name="ops",
        tool_name="restart",
        arguments={"force": True},
    )

    manager.cancel(state.confirmation_id)
    assert not manager.consume(
        state,
        CriticalConfirmationReply("user-1", "session-1", "confirm"),
        server_name="ops",
        tool_name="restart",
        arguments={"force": False},
    )

    fresh = manager.create(
        CriticalConfirmationRequest(
            actor_uid="user-1",
            session_id="session-1",
            server_name="ops",
            tool_name="restart",
            arguments={},
            ttl=timedelta(seconds=1),
        )
    )
    current += timedelta(seconds=2)
    assert not manager.consume(
        fresh,
        CriticalConfirmationReply("user-1", "session-1", "confirm"),
        server_name="ops",
        tool_name="restart",
        arguments={},
    )
    assert not CriticalConfirmationManager(clock=lambda: current).consume(
        fresh,
        CriticalConfirmationReply("user-1", "session-1", "confirm"),
        server_name="ops",
        tool_name="restart",
        arguments={},
    )


def test_matcher_state_is_immutable_scalar_confirmation_data() -> None:
    state = CriticalConfirmationManager(clock=_now).create(
        CriticalConfirmationRequest(
            actor_uid="user-1",
            session_id="session-1",
            server_name="ops",
            tool_name="restart",
            arguments={"nested": [1, 2]},
            ttl=timedelta(seconds=30),
        )
    )

    assert set(state.matcher_state()) == {
        "confirmation_id",
        "arguments_hash",
        "expires_at",
        "actor_uid",
        "session_id",
    }
    assert all(isinstance(value, str) for value in state.matcher_state().values())
