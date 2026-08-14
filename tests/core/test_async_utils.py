from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import async_utils
from src.plugins.nonebot_plugin_lingchu_bot.core.async_utils import (
    drain_background_tasks,
    fire_and_forget,
    get_background_tasks,
)


async def _drain_until_done(task: asyncio.Task[Any]) -> None:
    """Yield control until the task and its done-callback have run."""
    for _ in range(100):
        if task.done() and task not in async_utils._background_tasks:
            return
        await asyncio.sleep(0)


@pytest.fixture(autouse=True)
def _isolate_background_tasks():
    async_utils._background_tasks.clear()
    yield
    async_utils._background_tasks.clear()


@pytest.mark.asyncio
async def test_fire_and_forget_schedules_task_that_runs_to_completion() -> None:
    marker = asyncio.Event()

    async def worker() -> None:
        marker.set()

    task = fire_and_forget(worker())
    await task
    await _drain_until_done(task)

    assert marker.is_set()
    assert task.done()


@pytest.mark.asyncio
async def test_fire_and_forget_logs_exception_without_propagating() -> None:
    async def failing() -> None:
        raise ValueError("boom")

    with patch.object(async_utils, "logger") as logger_mock:
        task = fire_and_forget(failing())
        await _drain_until_done(task)

    logger_mock.exception.assert_called_once()
    assert task.done()
    assert task not in async_utils._background_tasks


@pytest.mark.asyncio
async def test_fire_and_forget_releases_task_reference_after_completion() -> None:
    async def worker() -> str:
        return "done"

    task = fire_and_forget(worker(), name="release-check")

    assert task in async_utils._background_tasks

    await task
    await _drain_until_done(task)

    assert task.done()
    assert task not in async_utils._background_tasks


@pytest.mark.asyncio
async def test_fire_and_forget_exposes_registered_task_by_name() -> None:
    release = asyncio.Event()

    async def worker() -> None:
        await release.wait()

    task = fire_and_forget(worker(), name="observable-task")

    assert get_background_tasks() == (task,)
    assert task.get_name() == "observable-task"

    release.set()
    await task
    await _drain_until_done(task)


@pytest.mark.asyncio
async def test_drain_background_tasks_waits_for_registered_tasks() -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    async def worker() -> None:
        started.set()
        await release.wait()

    task = fire_and_forget(worker(), name="drain-task")
    await started.wait()

    drain_task = asyncio.create_task(drain_background_tasks())
    await asyncio.sleep(0)
    assert drain_task.done() is False

    release.set()
    await drain_task

    assert task.done()
    assert get_background_tasks() == ()


@pytest.mark.asyncio
async def test_drain_background_tasks_logs_failures_without_raising() -> None:
    async def failing() -> None:
        raise ValueError("drain failure")

    with patch.object(async_utils, "logger") as logger_mock:
        task = fire_and_forget(failing(), name="drain-failure")
        await drain_background_tasks()

    assert task.done()
    assert get_background_tasks() == ()
    logger_mock.exception.assert_called_once()


@pytest.mark.asyncio
async def test_drain_background_tasks_cancels_tasks_after_timeout() -> None:
    started = asyncio.Event()

    async def worker() -> None:
        started.set()
        await asyncio.Event().wait()

    task = fire_and_forget(worker(), name="timeout-task")
    await started.wait()

    with patch.object(async_utils.logger, "warning") as warning_mock:
        await drain_background_tasks(drain_timeout=0.001)

    assert task.cancelled()
    await _drain_until_done(task)
    warning_mock.assert_called_once()
