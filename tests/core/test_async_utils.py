from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import async_utils
from src.plugins.nonebot_plugin_lingchu_bot.core.async_utils import fire_and_forget


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
