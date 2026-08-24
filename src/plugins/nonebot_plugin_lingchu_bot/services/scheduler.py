"""Persistent scheduler service backed by nonebot-plugin-apscheduler."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import inspect
import logging
from typing import TYPE_CHECKING, Any

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.base import SchedulerNotRunningError
from nonebot import require

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

require("nonebot_plugin_orm")
from nonebot_plugin_orm import get_session

from ..database.orm_crud import DatabaseError
from ..repositories import (
    blocklist as blocklist_repository,
    scheduler_jobs as repository,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session

logger = logging.getLogger(__name__)
SchedulerHandler = Callable[..., Awaitable[Any] | Any]
_handlers: dict[str, SchedulerHandler] = {}
_runtime_job_ids: set[str] = set()

BLOCKLIST_CLEANUP_HANDLER_KEY = "blocklist.cleanup_expired_blocks"
BLOCKLIST_CLEANUP_INTERVAL_MINUTES = 5


def register_scheduler_handler(key: str, handler: SchedulerHandler) -> None:
    """Register a handler key used by persisted scheduler jobs."""
    _handlers[key] = handler


def clear_scheduler_handlers() -> None:
    """Clear registered scheduler handlers."""
    _handlers.clear()


async def _maybe_await(value: Awaitable[Any] | Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _cleanup_expired_blocks_job() -> tuple[int, bool]:
    """Run blocklist and subject-policy expiration cleanup for APScheduler."""
    try:
        async with get_session() as session, session.begin():
            return await blocklist_repository.cleanup_expired_blocks(session)
    except DatabaseError:
        logger.exception("Failed to cleanup expired blocklist and subject policies")
        return (0, False)


def _register_builtin_handlers() -> None:
    register_scheduler_handler(
        BLOCKLIST_CLEANUP_HANDLER_KEY,
        _cleanup_expired_blocks_job,
    )


async def _ensure_builtin_jobs(
    session: AsyncSession | async_scoped_session[AsyncSession],
) -> None:
    existing_job = await repository.get_job_spec(session, BLOCKLIST_CLEANUP_HANDLER_KEY)
    if existing_job is not None:
        return
    await repository.save_job_spec(
        session,
        job_id=BLOCKLIST_CLEANUP_HANDLER_KEY,
        handler_key=BLOCKLIST_CLEANUP_HANDLER_KEY,
        trigger_type="interval",
        trigger_kwargs={"minutes": BLOCKLIST_CLEANUP_INTERVAL_MINUTES},
    )


def _schedule_runtime_job(
    *,
    job_id: str,
    trigger_type: str,
    trigger_kwargs: dict[str, Any],
    coalesce: bool,
    max_instances: int,
    misfire_grace_time: int | None,
) -> None:
    scheduler.add_job(
        execute_persistent_job,
        trigger_type,
        id=job_id,
        args=[job_id],
        replace_existing=True,
        coalesce=coalesce,
        max_instances=max_instances,
        misfire_grace_time=misfire_grace_time,
        **trigger_kwargs,
    )
    _runtime_job_ids.add(job_id)


async def execute_persistent_job(job_id: str) -> None:
    """Load a persisted scheduler job and dispatch its registered handler."""
    try:
        async with get_session() as session:
            job = await repository.get_job_spec(session, job_id)
            if job is None or not job.enabled:
                return
            handler_key = job.handler_key
            handler = _handlers.get(handler_key)
            if handler is None:
                logger.warning(
                    "Scheduled job %s has no registered handler %s",
                    job_id,
                    handler_key,
                )
                return
            _, args, kwargs = repository.decode_job_payload(job)
    except DatabaseError:
        # Transient DB failures must surface as a logged, skipped run instead of
        # propagating into APScheduler as an unhandled job error.
        logger.exception("Failed to load scheduled job %s; skipping run", job_id)
        return
    except (TypeError, ValueError):
        logger.exception("Failed to decode payload for scheduled job %s", job_id)
        return

    await _maybe_await(handler(*args, **kwargs))


async def register_persistent_job(
    *,
    job_id: str,
    handler_key: str,
    trigger_type: str,
    trigger_kwargs: dict[str, Any],
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    enabled: bool = True,
    coalesce: bool = True,
    max_instances: int = 1,
    misfire_grace_time: int | None = None,
) -> None:
    """Persist a scheduler job spec and schedule it when enabled."""
    if handler_key not in _handlers:
        raise ValueError(f"unknown scheduler handler: {handler_key}")

    async with get_session() as session, session.begin():
        await repository.save_job_spec(
            session,
            job_id=job_id,
            handler_key=handler_key,
            trigger_type=trigger_type,
            trigger_kwargs=trigger_kwargs,
            args=args,
            kwargs=kwargs,
            enabled=enabled,
            coalesce=coalesce,
            max_instances=max_instances,
            misfire_grace_time=misfire_grace_time,
        )
    if not enabled:
        return

    _schedule_runtime_job(
        job_id=job_id,
        trigger_type=trigger_type,
        trigger_kwargs=trigger_kwargs,
        coalesce=coalesce,
        max_instances=max_instances,
        misfire_grace_time=misfire_grace_time,
    )


async def initialize_scheduler_service() -> None:
    """Rehydrate enabled persisted jobs into the runtime scheduler."""
    _register_builtin_handlers()
    try:
        async with get_session() as session, session.begin():
            await _ensure_builtin_jobs(session)
            jobs = await repository.list_enabled_job_specs(session)
            # 在 session 内解码 payload 并提取标量字段,避免 ORM 对象
            # 在 session 关闭(commit)后访问属性触发 DetachedInstanceError。
            job_specs: list[dict[str, Any]] = []
            for job in jobs:
                if job.handler_key not in _handlers:
                    logger.warning(
                        "Skipping scheduled job %s without handler %s",
                        job.job_id,
                        job.handler_key,
                    )
                    continue
                try:
                    trigger_kwargs, _, _ = repository.decode_job_payload(job)
                except (TypeError, ValueError):
                    logger.exception(
                        "Failed to schedule persisted job %s",
                        job.job_id,
                    )
                    continue
                job_specs.append({
                    "job_id": job.job_id,
                    "trigger_type": job.trigger_type,
                    "trigger_kwargs": trigger_kwargs,
                    "coalesce": job.coalesce,
                    "max_instances": job.max_instances,
                    "misfire_grace_time": job.misfire_grace_time,
                })
    except DatabaseError:
        logger.exception("Failed to load persisted scheduler jobs")
        return

    for spec in job_specs:
        _schedule_runtime_job(
            job_id=spec["job_id"],
            trigger_type=spec["trigger_type"],
            trigger_kwargs=spec["trigger_kwargs"],
            coalesce=spec["coalesce"],
            max_instances=spec["max_instances"],
            misfire_grace_time=spec["misfire_grace_time"],
        )


async def remove_persistent_job(job_id: str) -> tuple[int, bool]:
    """Remove a persisted scheduler job and its runtime scheduler entry."""
    try:
        scheduler.remove_job(job_id)
    except JobLookupError:
        logger.debug("Runtime scheduler job %s was not present", job_id)
        _runtime_job_ids.discard(job_id)
    except SchedulerNotRunningError:
        logger.debug("Scheduler already stopped; job %s not removed", job_id)
        _runtime_job_ids.discard(job_id)
    else:
        _runtime_job_ids.discard(job_id)
    async with get_session() as session, session.begin():
        return await repository.delete_job_spec(session, job_id)


async def shutdown_scheduler_service() -> None:
    """Remove Lingchu-owned runtime jobs before the scheduler shuts down."""
    first_error: Exception | None = None
    for job_id in tuple(_runtime_job_ids):
        try:
            scheduler.remove_job(job_id)
        except JobLookupError:
            logger.debug("Runtime scheduler job %s was not present at shutdown", job_id)
        except Exception as exc:
            logger.exception("Failed to remove runtime scheduler job %s", job_id)
            if first_error is None:
                first_error = exc
        finally:
            _runtime_job_ids.discard(job_id)
    _handlers.clear()
    if first_error is not None:
        raise first_error
