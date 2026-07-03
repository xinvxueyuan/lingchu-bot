"""Message storage service business APIs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..core.runtime_config import runtime_config
from ..database.orm_crud import DatabaseError
from ..platforms import get_platform_profile, resolve_adapter_id
from ..repositories import message_store as repository

if TYPE_CHECKING:
    from nonebot.adapters import Bot
    from nonebot.matcher import Matcher

    from ..hooks.adapters import (
        MessageIdentity,
        NormalizedMessageEvent,
        PlatformContext,
    )

logger = logging.getLogger(__name__)
SCHEDULER_CLEANUP_HANDLER_KEY = "message_store.cleanup_expired_messages"
STATE_KEY = "_lingchu_message_record_identity"
SUMMARY_LIMIT = 500


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
    adapter_obj = getattr(bot, "adapter", None)
    get_name = getattr(adapter_obj, "get_name", None)
    adapter = "unknown"
    if callable(get_name):
        try:
            adapter = str(get_name())
        except (AttributeError, TypeError, ValueError):
            adapter = "unknown"
    adapter_id = resolve_adapter_id(adapter)
    if adapter_id is None:
        return False
    profile = get_platform_profile(adapter_id)
    if profile is None:
        return False
    try:
        await repository.record_api_call(
            repository.AuditEvent(
                platform_id=profile.platform_id,
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


async def handle_event_received(normalized: NormalizedMessageEvent) -> None:
    """Persist an incoming normalized message event."""
    if not runtime_config.message_store_enabled:
        return
    identity = normalized.identity
    try:
        await repository.record_event_received(
            platform_id=identity.platform_id,
            adapter_id=identity.adapter_id,
            protocol_id=identity.protocol_id,
            framework_id=identity.framework_id,
            bot_id=identity.bot_id,
            conversation_id=identity.conversation_id,
            user_id=normalized.user_id,
            message_id=identity.message_id,
            event_type=normalized.event_type,
            event_category=normalized.event_category,
            message_type=normalized.message_type,
            text_summary=normalized.text_summary,
            raw_message=normalized.raw_message,
            raw_event=normalized.raw_event,
        )
    except DatabaseError:
        logger.exception("Failed to record incoming message event")


async def handle_matcher_result(
    identity: MessageIdentity,
    matcher: Matcher,
    exception: Exception | None,
) -> bool:
    """Update processing status for a stored message record."""
    if not runtime_config.message_store_enabled:
        return False
    status = "handled" if exception is None else "failed"
    if getattr(matcher, "block", False):
        status = f"{status}:blocked"
    try:
        return await repository.record_matcher_result(
            platform_id=identity.platform_id,
            adapter_id=identity.adapter_id,
            protocol_id=identity.protocol_id,
            framework_id=identity.framework_id,
            bot_id=identity.bot_id,
            conversation_id=identity.conversation_id,
            message_id=identity.message_id,
            process_status=status,
            exception_summary=_stringify(exception),
        )
    except DatabaseError:
        logger.exception("Failed to update message processing status")
        return False


async def handle_api_called(
    platform_context: PlatformContext,
    exception: Exception | None,
    api: str,
    data: dict[str, Any],
    result: Any,
) -> None:
    """Record a platform API call result."""
    if (
        not runtime_config.message_store_enabled
        or not runtime_config.message_store_record_api_calls
    ):
        return
    try:
        await repository.record_api_call(
            repository.AuditEvent(
                platform_id=platform_context.platform_id,
                adapter_id=platform_context.adapter_id,
                protocol_id=platform_context.protocol_id,
                bot_id=platform_context.bot_id,
                api_name=api,
                data_summary=_stringify(data),
                result_summary=_stringify(result),
                exception_summary=_stringify(exception),
            )
        )
    except DatabaseError:
        logger.exception("Failed to record platform API call: %s", api)
