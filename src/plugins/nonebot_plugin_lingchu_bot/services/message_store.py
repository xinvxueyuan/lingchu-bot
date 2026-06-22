"""Message storage service and NoneBot runtime hooks."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher  # noqa: TC002
from nonebot.message import (
    event_postprocessor,
    event_preprocessor,
    run_postprocessor,
    run_preprocessor,
)
from nonebot.typing import T_State  # noqa: TC002

from ..core.async_utils import fire_and_forget
from ..core.runtime_config import runtime_config
from ..database.orm_crud import DatabaseError
from ..platforms import get_platform_profile, resolve_adapter_id
from ..repositories import message_store as repository

logger = logging.getLogger(__name__)
STATE_KEY = "_lingchu_message_record_identity"
SUMMARY_LIMIT = 500
RAW_PAYLOAD_MAX_DEPTH = 8


@dataclass(slots=True)
class MessageIdentity:
    """Stable identity for a received message event."""

    platform_id: str
    adapter_id: str
    protocol_id: str | None
    bot_id: str
    conversation_id: str | None
    message_id: str | None


@dataclass(slots=True)
class NormalizedMessageEvent:
    """Adapter-neutral message event data used by the repository layer."""

    identity: MessageIdentity
    user_id: str | None
    event_type: str
    message_type: str | None
    text_summary: str | None
    raw_message: str | None
    raw_event: str | None


def _truncate(value: str | None, limit: int | None = None) -> str | None:
    if value is None:
        return None
    size = limit if limit is not None else runtime_config.message_store_summary_limit
    if size <= 0 or len(value) <= size:
        return value
    return f"{value[:size]}..."


def _stringify(value: Any, *, limit: int = SUMMARY_LIMIT) -> str | None:
    if value is None:
        return None
    return _truncate(str(value), limit)


def _first_attr(obj: Any, *names: str) -> Any:
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value
    return None


def _safe_call(obj: Any, method_name: str) -> Any:
    method = getattr(obj, method_name, None)
    if method is None:
        return None
    try:
        return method()
    except (AttributeError, TypeError, ValueError):
        return None


def _adapter_name(bot: Bot) -> str:
    adapter = getattr(bot, "adapter", None)
    get_name = getattr(adapter, "get_name", None)
    if get_name is None:
        return "unknown"
    try:
        return str(get_name())
    except (AttributeError, TypeError, ValueError):
        return "unknown"


def _adapter_identity(adapter_name: str) -> tuple[str, str] | None:
    adapter_id = resolve_adapter_id(adapter_name)
    if adapter_id is None:
        return None
    profile = get_platform_profile(adapter_id)
    if profile is not None:
        return (profile.platform_id, adapter_id)
    return None


def _event_data(event: Event) -> Any:
    return getattr(event, "data", None)


def _event_type(event: Event) -> str:
    return str(
        _safe_call(event, "get_event_name")
        or _safe_call(event, "get_type")
        or type(event).__name__
    )


def _event_category(event: Event) -> str | None:
    value = _safe_call(event, "get_type")
    return str(value) if value is not None else None


def _message_type(event: Event) -> str | None:
    value = _first_attr(event, "message_type", "post_type")
    if value is None:
        value = _first_attr(_event_data(event), "message_type", "post_type")
    return _stringify(value, limit=64)


def _conversation_id(event: Event) -> str | None:
    value = _safe_call(event, "get_session_id")
    if value is None:
        value = _first_attr(
            event,
            "group_id",
            "guild_id",
            "channel_id",
            "peer_id",
            "session_id",
        )
    if value is None:
        value = _first_attr(
            _event_data(event),
            "group_id",
            "guild_id",
            "channel_id",
            "peer_id",
            "session_id",
        )
    return _stringify(value, limit=128)


def _user_id(event: Event) -> str | None:
    value = _safe_call(event, "get_user_id")
    if value is None:
        value = _first_attr(event, "user_id", "sender_id")
    if value is None:
        value = _first_attr(_event_data(event), "user_id", "sender_id")
    return _stringify(value, limit=128)


def _message_id(event: Event) -> str | None:
    value = _first_attr(event, "message_id", "id")
    if value is None:
        value = _first_attr(_event_data(event), "message_id", "message_seq", "id")
    return _stringify(value, limit=128)


def _plain_text(event: Event) -> str | None:
    value = _safe_call(event, "get_plaintext")
    if value:
        return _truncate(str(value))
    message = _safe_call(event, "get_message")
    if message is None:
        message = _first_attr(event, "message")
    if message is None:
        message = _first_attr(_event_data(event), "message", "segments")
    return _truncate(str(message)) if message is not None else None


def _jsonable(value: Any, *, depth: int = 0) -> Any:  # noqa: C901, PLR0911
    if depth > RAW_PAYLOAD_MAX_DEPTH:
        return repr(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {
            str(key): _jsonable(item, depth=depth + 1) for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item, depth=depth + 1) for item in value]

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump) and type(value).__module__ != "unittest.mock":
        try:
            return _jsonable(
                model_dump(mode="json", by_alias=True, exclude_none=False),
                depth=depth + 1,
            )
        except (TypeError, ValueError, AttributeError):
            pass

    data = getattr(value, "data", None)
    if data is not None and data is not value:
        return _jsonable(data, depth=depth + 1)

    if hasattr(value, "__dict__") and type(value).__module__ != "unittest.mock":
        raw = {
            key: item for key, item in vars(value).items() if not key.startswith("_")
        }
        if raw:
            return _jsonable(raw, depth=depth + 1)

    return str(value)


def _json_summary(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return json.dumps(str(value), ensure_ascii=False)


def _raw_message(event: Event) -> str | None:
    message = _safe_call(event, "get_message")
    if message is None:
        message = _first_attr(event, "message")
    if message is None:
        message = _first_attr(_event_data(event), "message", "segments")
    return _json_summary(message)


def _raw_event(event: Event) -> str | None:
    return _json_summary(event)


def normalize_message_event(bot: Bot, event: Event) -> NormalizedMessageEvent | None:
    """Normalize an adapter event into message-store metadata."""
    if _event_category(event) != "message":
        return None
    adapter = _adapter_name(bot)
    adapter_identity = _adapter_identity(adapter)
    if adapter_identity is None:
        return None
    platform_id, adapter_id = adapter_identity
    bot_id = _stringify(getattr(bot, "self_id", None), limit=128) or "unknown"
    identity = MessageIdentity(
        platform_id=platform_id,
        adapter_id=adapter_id,
        protocol_id=None,
        bot_id=bot_id,
        conversation_id=_conversation_id(event),
        message_id=_message_id(event),
    )
    return NormalizedMessageEvent(
        identity=identity,
        user_id=_user_id(event),
        event_type=_event_type(event),
        message_type=_message_type(event),
        text_summary=_plain_text(event),
        raw_message=_raw_message(event),
        raw_event=_raw_event(event),
    )


def _state_identity(state: T_State) -> MessageIdentity | None:
    value = state.get(STATE_KEY)
    return value if isinstance(value, MessageIdentity) else None


async def initialize_message_store() -> None:
    """Initialize message storage runtime resources."""
    if not runtime_config.message_store_enabled:
        logger.info("Message store is disabled")
        return
    logger.info("Message store initialized")


async def shutdown_message_store() -> None:
    """Run lightweight shutdown maintenance for message storage."""
    if not runtime_config.message_store_enabled:
        return
    await cleanup_expired_messages()


async def cleanup_expired_messages() -> tuple[int, bool]:
    """Delete expired message records according to configuration."""
    if (
        not runtime_config.message_store_enabled
        or not runtime_config.message_store_cleanup_enabled
    ):
        return (0, True)
    try:
        return await repository.cleanup_expired_messages(
            retention_days=runtime_config.message_store_retention_days
        )
    except DatabaseError:
        logger.exception("Failed to cleanup expired message records")
        return (0, False)


async def record_bot_lifecycle(bot: Bot, event_type: str) -> bool:
    """Record bot connect/disconnect lifecycle as an auxiliary store event."""
    if not runtime_config.message_store_enabled:
        return False
    adapter = _adapter_name(bot)
    adapter_identity = _adapter_identity(adapter)
    if adapter_identity is None:
        return False
    platform_id, adapter_id = adapter_identity
    try:
        await repository.record_api_call(
            repository.AuditEvent(
                platform_id=platform_id,
                adapter_id=adapter_id,
                protocol_id=None,
                bot_id=_stringify(getattr(bot, "self_id", None), limit=128)
                or "unknown",
                api_name=event_type,
                data_summary=None,
                result_summary=None,
                exception_summary=None,
                audit_type="lifecycle",
            )
        )
    except DatabaseError:
        logger.exception("Failed to record bot lifecycle event: %s", event_type)
        return False
    return True


@event_preprocessor
async def message_store_preprocessor(
    bot: Bot,
    event: Event,
    state: T_State,
) -> None:
    """Store incoming event metadata before matcher processing."""
    if not runtime_config.message_store_enabled:
        return
    normalized = normalize_message_event(bot, event)
    if normalized is None:
        return
    state[STATE_KEY] = normalized.identity

    async def _record() -> None:
        try:
            await repository.record_event_received(
                platform_id=normalized.identity.platform_id,
                adapter_id=normalized.identity.adapter_id,
                protocol_id=normalized.identity.protocol_id,
                bot_id=normalized.identity.bot_id,
                conversation_id=normalized.identity.conversation_id,
                user_id=normalized.user_id,
                message_id=normalized.identity.message_id,
                event_type=normalized.event_type,
                message_type=normalized.message_type,
                text_summary=normalized.text_summary,
                raw_message=normalized.raw_message,
                raw_event=normalized.raw_event,
            )
        except DatabaseError:
            logger.exception("Failed to record incoming message event")

    fire_and_forget(_record(), name="record_event_received")


@event_postprocessor
async def message_store_postprocessor() -> None:
    """Reserved event postprocessor hook for future aggregate updates."""


@run_preprocessor
async def message_store_run_preprocessor() -> None:
    """Reserved run preprocessor hook for future matcher timing."""


@run_postprocessor
async def message_store_run_postprocessor(
    matcher: Matcher,
    exception: Exception | None,
    state: T_State,
) -> None:
    """Update message processing status after a matcher run."""
    if not runtime_config.message_store_enabled:
        return
    identity = _state_identity(state)
    if identity is None:
        return
    status = "handled" if exception is None else "failed"
    if getattr(matcher, "block", False):
        status = f"{status}:blocked"

    async def _record() -> None:
        try:
            await repository.record_matcher_result(
                platform_id=identity.platform_id,
                adapter_id=identity.adapter_id,
                protocol_id=identity.protocol_id,
                bot_id=identity.bot_id,
                conversation_id=identity.conversation_id,
                message_id=identity.message_id,
                process_status=status,
                exception_summary=_stringify(exception),
            )
        except DatabaseError:
            logger.exception("Failed to update message processing status")

    fire_and_forget(_record(), name="record_matcher_result")


@Bot.on_calling_api
async def message_store_on_calling_api(
    bot: Bot,
    api: str,
    data: dict[str, Any],
) -> None:
    """Reserved API pre-call hook for future correlation identifiers."""
    _ = (bot, api, data)


@Bot.on_called_api
async def message_store_on_called_api(
    bot: Bot,
    exception: Exception | None,
    api: str,
    data: dict[str, Any],
    result: Any,
) -> None:
    """Record platform API call results when configured."""
    if (
        not runtime_config.message_store_enabled
        or not runtime_config.message_store_record_api_calls
    ):
        return
    adapter = _adapter_name(bot)
    adapter_identity = _adapter_identity(adapter)
    if adapter_identity is None:
        return
    platform_id, adapter_id = adapter_identity
    bot_id = _stringify(getattr(bot, "self_id", None), limit=128) or "unknown"

    async def _record() -> None:
        try:
            await repository.record_api_call(
                repository.AuditEvent(
                    platform_id=platform_id,
                    adapter_id=adapter_id,
                    protocol_id=None,
                    bot_id=bot_id,
                    api_name=api,
                    data_summary=_stringify(data),
                    result_summary=_stringify(result),
                    exception_summary=_stringify(exception),
                )
            )
        except DatabaseError:
            logger.exception("Failed to record platform API call: %s", api)

    fire_and_forget(_record(), name="record_api_call")
