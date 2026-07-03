from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from src.plugins.nonebot_plugin_lingchu_bot.hooks.interfaces import (
    EventContext,
    HookContext,
    HookHandler,
    HookType,
    PlatformContext,
)


def test_platform_context_defaults() -> None:
    ctx = PlatformContext(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="bot-1",
    )
    assert ctx.platform_id == "qq"
    assert ctx.adapter_id == "~onebot.v11"
    assert ctx.bot_id == "bot-1"
    assert ctx.protocol_id is None


def test_event_context_inherits_platform() -> None:
    platform = PlatformContext(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="bot-1",
    )
    event = MagicMock()
    ctx = EventContext(
        platform_context=platform,
        event=event,
        normalized_event=None,
    )
    assert ctx.platform_context == platform
    assert ctx.event is event
    assert ctx.normalized_event is None
    assert ctx.state is None


def test_hook_type_values() -> None:
    assert HookType.LIFECYCLE == "lifecycle"
    assert HookType.BOT_CONNECTION == "bot_connection"
    assert HookType.MESSAGE_STORE == "message_store"
    assert HookType.API_AUDIT == "api_audit"


async def _sample_handler(context: HookContext) -> None:
    _ = context


def test_hook_handler_protocol() -> None:
    handler: HookHandler[HookContext] = _sample_handler
    assert callable(handler)


def test_event_context_with_state() -> None:
    state: dict[str, Any] = {"key": "value"}
    ctx = EventContext(state=state)
    assert ctx.platform_context is None
    assert ctx.state is state
