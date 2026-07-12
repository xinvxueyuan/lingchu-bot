"""Async utilities for fire-and-forget background tasks."""

import asyncio
from collections.abc import Coroutine
from typing import Any

from nonebot import logger

_background_tasks: set[asyncio.Task[Any]] = set()


def fire_and_forget(
    coro: Coroutine[Any, Any, Any],
    *,
    name: str = "fire_and_forget",
) -> asyncio.Task[Any]:
    """Schedule a coroutine as a tracked background task.

    The task is stored in a module-level set so it is not garbage-collected
    before completion.  A done-callback removes the reference and logs any
    exception via ``logger.exception`` so failures are never silently lost.

    Args:
        coro: The coroutine to schedule.
        name: Human-readable name for the background task.

    Returns:
        The created :class:`asyncio.Task` so callers may await it if needed.

    """
    task = asyncio.create_task(coro, name=name)
    _background_tasks.add(task)
    task.add_done_callback(_on_background_task_done)
    return task


def _on_background_task_done(task: asyncio.Task[Any]) -> None:
    """Discard the finished task reference and log any exception."""
    _background_tasks.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is None:
        return
    logger.exception("Background task %s failed", task.get_name(), exc_info=exc)
