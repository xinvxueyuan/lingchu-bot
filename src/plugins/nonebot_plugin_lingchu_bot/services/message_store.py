"""Message storage service business APIs."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

from nonebot import require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import get_session

from ..core.config import plugin_config
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
ELLIPSIS_LENGTH = 3

# API audit pipeline: a bounded queue drained by a single worker so concurrent
# API calls cannot fan out into parallel DB writes (SQLite lock contention).
_API_AUDIT_QUEUE_MAX = 1000
_API_AUDIT_DROP_WARN_INTERVAL = 100

if TYPE_CHECKING:
    # (platform_context, exception, api, data, result) captured at call time;
    # payload stringification is deferred to the worker.
    _ApiAuditItem = tuple[PlatformContext, Exception | None, str, dict[str, Any], Any]


class _ApiAuditPipeline:
    """Bounded queue + single worker for serialized audit persistence."""

    def __init__(self) -> None:
        self.queue: asyncio.Queue[_ApiAuditItem] = asyncio.Queue(
            maxsize=_API_AUDIT_QUEUE_MAX
        )
        self.worker: asyncio.Task[None] | None = None
        self.dropped = 0

    def ensure_worker(self) -> None:
        """Start the audit worker task if it is not currently running."""
        if self.worker is not None and not self.worker.done():
            return
        self.worker = asyncio.create_task(
            self._worker_loop(), name="message_store:api_audit_worker"
        )
        self.worker.add_done_callback(self._on_worker_done)

    @staticmethod
    def _on_worker_done(task: asyncio.Task[None]) -> None:
        """Log unexpected worker death; the next enqueue restarts it lazily."""
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error("API audit worker stopped unexpectedly: %r", exc)

    def enqueue(
        self,
        platform_context: PlatformContext,
        exception: Exception | None,
        api: str,
        data: dict[str, Any],
        result: Any,
    ) -> None:
        """Add one audit item, counting and warning when the queue is full."""
        try:
            self.queue.put_nowait((platform_context, exception, api, data, result))
        except asyncio.QueueFull:
            self.dropped += 1
            if self.dropped % _API_AUDIT_DROP_WARN_INTERVAL == 1:
                logger.warning(
                    "API audit queue full; dropped %d event(s) so far", self.dropped
                )

    async def _worker_loop(self) -> None:
        """Drain queued audit items in batches, one transaction per batch."""
        while True:
            item = await self.queue.get()
            batch: list[_ApiAuditItem] = [item]
            while not self.queue.empty():
                batch.append(self.queue.get_nowait())
            await write_api_audit_batch(batch)

    async def stop(self) -> None:
        """Cancel the worker and flush whatever is still queued."""
        worker, self.worker = self.worker, None
        if worker is not None and not worker.done():
            worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await worker
        await self.flush()

    async def flush(self) -> int:
        """Drain pending items and write them in one batch; return the count."""
        batch: list[_ApiAuditItem] = []
        while not self.queue.empty():
            batch.append(self.queue.get_nowait())
        await write_api_audit_batch(batch)
        return len(batch)


_api_audit = _ApiAuditPipeline()


def _truncate(value: str | None, limit: int | None = None) -> str | None:
    if value is None:
        return None
    size = limit if limit is not None else plugin_config.message_store_summary_limit
    if size <= 0 or len(value) <= size:
        return value
    if size <= ELLIPSIS_LENGTH:
        return value[:size]
    return f"{value[: size - ELLIPSIS_LENGTH]}..."


def _stringify(value: Any, *, limit: int = SUMMARY_LIMIT) -> str | None:
    if value is None:
        return None
    return _truncate(str(value), limit)


async def initialize_message_store() -> None:
    """Initialize message storage runtime resources."""
    if not plugin_config.message_store_enabled:
        logger.info("Message store is disabled")
        return
    logger.info("Message store initialized")


async def shutdown_message_store() -> None:
    """Run lightweight shutdown maintenance for message storage."""
    if not plugin_config.message_store_enabled:
        return
    # Stop the audit worker first so queued events are flushed before the
    # cleanup job takes the DB write lock.
    await _stop_api_audit_worker()
    await cleanup_expired_messages()


async def cleanup_expired_messages() -> tuple[int, bool]:
    """Delete expired message records according to configuration."""
    if (
        not plugin_config.message_store_enabled
        or not plugin_config.message_store_cleanup_enabled
    ):
        return (0, True)
    try:
        async with get_session() as session:
            result = await repository.cleanup_expired_messages(
                session,
                retention_days=plugin_config.message_store_retention_days,
            )
            await session.commit()
            return result
    except DatabaseError:
        logger.exception("Failed to cleanup expired message records")
        return (0, False)


async def record_bot_lifecycle(bot: Bot, event_type: str) -> bool:
    """Record bot connect/disconnect lifecycle as an auxiliary store event."""
    if not plugin_config.message_store_enabled:
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
        async with get_session() as session:
            await repository.record_api_call(
                session,
                repository.AuditEvent(
                    platform_id=profile.platform_id,
                    adapter_id=adapter_id,
                    protocol_id="unknown",
                    bot_id=_stringify(getattr(bot, "self_id", None), limit=128)
                    or "unknown",
                    api_name=event_type,
                    data_summary=None,
                    result_summary=None,
                    exception_summary=None,
                    audit_type="lifecycle",
                ),
            )
            await session.commit()
    except DatabaseError:
        logger.exception("Failed to record bot lifecycle event: %s", event_type)
        return False
    return True


async def handle_event_received(normalized: NormalizedMessageEvent) -> None:
    """Persist an incoming normalized message event."""
    if not plugin_config.message_store_enabled:
        return
    identity = normalized.identity
    try:
        async with get_session() as session:
            await repository.record_event_received(
                session,
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
            await session.commit()
    except DatabaseError:
        logger.exception("Failed to record incoming message event")


async def handle_matcher_result(
    identity: MessageIdentity,
    matcher: Matcher,
    exception: Exception | None,
) -> bool:
    """Update processing status for a stored message record."""
    if not plugin_config.message_store_enabled:
        return False
    status = "handled" if exception is None else "failed"
    if getattr(matcher, "block", False):
        status = f"{status}:blocked"
    try:
        async with get_session() as session:
            result = await repository.record_matcher_result(
                session,
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
            await session.commit()
            return result
    except DatabaseError:
        logger.exception("Failed to update message processing status")
        return False


def handle_api_called(
    platform_context: PlatformContext,
    exception: Exception | None,
    api: str,
    data: dict[str, Any],
    result: Any,
) -> None:
    """Queue a platform API call audit event for serialized persistence.

    Synchronous by design: enqueueing must stay cheap so the adapter API call
    path is never blocked; the actual DB write happens in the audit worker.
    """
    if (
        not plugin_config.message_store_enabled
        or not plugin_config.message_store_record_api_calls
    ):
        return
    _api_audit.ensure_worker()
    _api_audit.enqueue(platform_context, exception, api, data, result)


async def write_api_audit_batch(batch: list[_ApiAuditItem]) -> None:
    """Persist a batch of audit items in a single transaction."""
    if not batch:
        return
    try:
        async with get_session() as session:
            for platform_context, exception, api, data, result in batch:
                await repository.record_api_call(
                    session,
                    repository.AuditEvent(
                        platform_id=platform_context.platform_id,
                        adapter_id=platform_context.adapter_id,
                        protocol_id=platform_context.protocol_id,
                        bot_id=platform_context.bot_id,
                        api_name=api,
                        data_summary=_stringify(data),
                        result_summary=_stringify(result),
                        exception_summary=_stringify(exception),
                    ),
                )
            await session.commit()
    except DatabaseError:
        logger.exception("Failed to record %d platform API audit event(s)", len(batch))


async def flush_api_audit_queue() -> int:
    """Drain pending audit items and write them in one batch.

    Returns the number of items written. Intended for shutdown and tests; the
    background worker owns the queue during normal operation.
    """
    return await _api_audit.flush()


async def _stop_api_audit_worker() -> None:
    """Stop the audit worker and flush whatever is still queued."""
    await _api_audit.stop()
