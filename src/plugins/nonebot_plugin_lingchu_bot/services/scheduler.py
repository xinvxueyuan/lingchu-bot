"""Persistent scheduler service backed by nonebot-plugin-apscheduler."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import inspect
import logging
from typing import Any

from apscheduler.jobstores.base import JobLookupError
from nonebot import require

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

require("nonebot_plugin_orm")
from nonebot_plugin_orm import get_session

from ..database.orm_crud import DatabaseError
from ..repositories import scheduler_jobs as repository

logger = logging.getLogger(__name__)
SchedulerHandler = Callable[..., Awaitable[Any] | Any]
_handlers: dict[str, SchedulerHandler] = {}


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


async def execute_persistent_job(job_id: str) -> None:
    """Load a persisted scheduler job and dispatch its registered handler."""
    async with get_session() as session:
        job = await repository.get_job_spec(session, job_id)

    if job is None or not job.enabled:
        return

    handler = _handlers.get(job.handler_key)
    if handler is None:
        logger.warning(
            "Scheduled job %s has no registered handler %s",
            job_id,
            job.handler_key,
        )
        return

    _, args, kwargs = repository.decode_job_payload(job)
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

    async with get_session() as session:
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
    try:
        async with get_session() as session:
            jobs = await repository.list_enabled_job_specs(session)
    except DatabaseError:
        logger.exception("Failed to load persisted scheduler jobs")
        return

    for job in jobs:
        try:
            if job.handler_key not in _handlers:
                logger.warning(
                    "Skipping scheduled job %s without handler %s",
                    job.job_id,
                    job.handler_key,
                )
                continue
            trigger_kwargs, _, _ = repository.decode_job_payload(job)
            _schedule_runtime_job(
                job_id=job.job_id,
                trigger_type=job.trigger_type,
                trigger_kwargs=trigger_kwargs,
                coalesce=job.coalesce,
                max_instances=job.max_instances,
                misfire_grace_time=job.misfire_grace_time,
            )
        except (TypeError, ValueError):
            logger.exception("Failed to schedule persisted job %s", job.job_id)


async def remove_persistent_job(job_id: str) -> tuple[int, bool]:
    """Remove a persisted scheduler job and its runtime scheduler entry."""
    try:
        scheduler.remove_job(job_id)
    except JobLookupError:
        logger.debug("Runtime scheduler job %s was not present", job_id)
    async with get_session() as session:
        return await repository.delete_job_spec(session, job_id)


async def shutdown_scheduler_service() -> None:
    """Reserved shutdown hook for future scheduler service cleanup."""
