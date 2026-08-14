"""Async utilities for fire-and-forget background tasks."""

import asyncio
from collections.abc import Coroutine
from typing import Any

from nonebot import logger

_background_tasks: set[asyncio.Task[Any]] = set()
_BACKGROUND_TASK_DRAIN_TIMEOUT_SECONDS = 10.0


def get_background_tasks() -> tuple[asyncio.Task[Any], ...]:
    """Return a stable snapshot of currently registered background tasks."""
    return tuple(sorted(_background_tasks, key=lambda task: task.get_name()))


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
    logger.debug("Registered background task {}", task.get_name())
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


async def drain_background_tasks(
    *,
    drain_timeout: float = _BACKGROUND_TASK_DRAIN_TIMEOUT_SECONDS,
) -> None:
    """Wait for background tasks with a bounded shutdown timeout.

    Tasks that do not finish before ``drain_timeout`` are cancelled and left to
    complete asynchronously; shutdown must not hang on an uncooperative
    discardable task.
    """
    if drain_timeout <= 0:
        raise ValueError

    current_task = asyncio.current_task()
    deadline = asyncio.get_running_loop().time() + drain_timeout
    while tasks := get_background_tasks():
        pending = tuple(task for task in tasks if task is not current_task)
        if not pending:
            return
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            unfinished = pending
        else:
            _, unfinished = await asyncio.wait(pending, timeout=remaining)
        if unfinished:
            for task in unfinished:
                task.cancel()
            logger.warning(
                "Timed out draining background tasks; cancelled {} task(s)",
                len(unfinished),
            )
            await asyncio.sleep(0)
            return
        await asyncio.sleep(0)
