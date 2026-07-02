from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from apscheduler.jobstores.base import JobLookupError

from src.plugins.nonebot_plugin_lingchu_bot.services import (
    scheduler as scheduler_service,
)


class FakeScheduler:
    def __init__(self) -> None:
        self.added: list[dict[str, Any]] = []
        self.removed: list[str] = []
        self.missing_jobs: set[str] = set()
        self.remove_errors: dict[str, Exception] = {}

    def add_job(self, func: Any, trigger: str, **kwargs: Any) -> None:
        self.added.append({"func": func, "trigger": trigger, **kwargs})

    def remove_job(self, job_id: str) -> None:
        if job_id in self.remove_errors:
            raise self.remove_errors[job_id]
        if job_id in self.missing_jobs:
            raise JobLookupError(job_id)
        self.removed.append(job_id)


def make_job(**overrides: Any) -> SimpleNamespace:
    values: dict[str, Any] = {
        "job_id": "cleanup",
        "handler_key": "cleanup",
        "trigger_type": "interval",
        "enabled": True,
        "coalesce": True,
        "max_instances": 1,
        "misfire_grace_time": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture(autouse=True)
def clear_registry() -> None:
    scheduler_service.clear_scheduler_handlers()


async def test_register_persistent_job_saves_and_schedules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_scheduler = FakeScheduler()
    save_job_spec = AsyncMock()
    monkeypatch.setattr(scheduler_service, "scheduler", fake_scheduler)
    monkeypatch.setattr(scheduler_service.repository, "save_job_spec", save_job_spec)

    async def handler() -> None:
        return None

    scheduler_service.register_scheduler_handler("cleanup", handler)
    await scheduler_service.register_persistent_job(
        job_id="cleanup",
        handler_key="cleanup",
        trigger_type="cron",
        trigger_kwargs={"hour": "3"},
        args=["old"],
        kwargs={"limit": 100},
        coalesce=False,
        max_instances=2,
        misfire_grace_time=30,
    )

    save_job_spec.assert_awaited_once_with(
        job_id="cleanup",
        handler_key="cleanup",
        trigger_type="cron",
        trigger_kwargs={"hour": "3"},
        args=["old"],
        kwargs={"limit": 100},
        enabled=True,
        coalesce=False,
        max_instances=2,
        misfire_grace_time=30,
    )
    assert fake_scheduler.added == [
        {
            "func": scheduler_service.execute_persistent_job,
            "trigger": "cron",
            "id": "cleanup",
            "args": ["cleanup"],
            "replace_existing": True,
            "coalesce": False,
            "max_instances": 2,
            "misfire_grace_time": 30,
            "hour": "3",
        },
    ]


async def test_register_persistent_job_requires_known_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save_job_spec = AsyncMock()
    monkeypatch.setattr(scheduler_service.repository, "save_job_spec", save_job_spec)

    with pytest.raises(ValueError, match="unknown scheduler handler: missing"):
        await scheduler_service.register_persistent_job(
            job_id="cleanup",
            handler_key="missing",
            trigger_type="cron",
            trigger_kwargs={},
        )

    save_job_spec.assert_not_awaited()


async def test_register_persistent_job_does_not_schedule_disabled_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_scheduler = FakeScheduler()
    monkeypatch.setattr(scheduler_service, "scheduler", fake_scheduler)
    monkeypatch.setattr(
        scheduler_service.repository,
        "save_job_spec",
        AsyncMock(return_value=make_job(enabled=False)),
    )

    scheduler_service.register_scheduler_handler("cleanup", lambda: None)
    await scheduler_service.register_persistent_job(
        job_id="cleanup",
        handler_key="cleanup",
        trigger_type="cron",
        trigger_kwargs={},
        enabled=False,
    )

    assert fake_scheduler.added == []


async def test_initialize_scheduler_service_rehydrates_enabled_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_scheduler = FakeScheduler()
    monkeypatch.setattr(scheduler_service, "scheduler", fake_scheduler)
    monkeypatch.setattr(
        scheduler_service.repository,
        "list_enabled_job_specs",
        AsyncMock(return_value=[make_job()]),
    )
    monkeypatch.setattr(
        scheduler_service.repository,
        "decode_job_payload",
        lambda _job: ({"minutes": 5}, [], {}),
    )

    async def handler() -> None:
        return None

    scheduler_service.register_scheduler_handler("cleanup", handler)
    await scheduler_service.initialize_scheduler_service()

    assert fake_scheduler.added[0]["id"] == "cleanup"
    assert fake_scheduler.added[0]["trigger"] == "interval"
    assert fake_scheduler.added[0]["minutes"] == 5


async def test_initialize_scheduler_service_logs_and_returns_on_database_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake_scheduler = FakeScheduler()
    monkeypatch.setattr(scheduler_service, "scheduler", fake_scheduler)
    monkeypatch.setattr(
        scheduler_service.repository,
        "list_enabled_job_specs",
        AsyncMock(side_effect=scheduler_service.DatabaseError("boom")),
    )

    await scheduler_service.initialize_scheduler_service()

    assert fake_scheduler.added == []
    assert "Failed to load persisted scheduler jobs" in caplog.text


async def test_initialize_scheduler_service_skips_missing_handler(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake_scheduler = FakeScheduler()
    monkeypatch.setattr(scheduler_service, "scheduler", fake_scheduler)
    monkeypatch.setattr(
        scheduler_service.repository,
        "list_enabled_job_specs",
        AsyncMock(return_value=[make_job(handler_key="missing")]),
    )
    decode_job_payload = MagicMock(return_value=({}, [], {}))
    monkeypatch.setattr(
        scheduler_service.repository,
        "decode_job_payload",
        decode_job_payload,
    )

    await scheduler_service.initialize_scheduler_service()

    assert fake_scheduler.added == []
    decode_job_payload.assert_not_called()
    assert "Skipping scheduled job cleanup without handler missing" in caplog.text


async def test_initialize_scheduler_service_skips_invalid_payload(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake_scheduler = FakeScheduler()
    monkeypatch.setattr(scheduler_service, "scheduler", fake_scheduler)
    monkeypatch.setattr(
        scheduler_service.repository,
        "list_enabled_job_specs",
        AsyncMock(return_value=[make_job()]),
    )
    monkeypatch.setattr(
        scheduler_service.repository,
        "decode_job_payload",
        MagicMock(side_effect=ValueError("bad payload")),
    )
    scheduler_service.register_scheduler_handler("cleanup", lambda: None)

    await scheduler_service.initialize_scheduler_service()

    assert fake_scheduler.added == []
    assert "Failed to schedule persisted job cleanup" in caplog.text


async def test_execute_persistent_job_dispatches_async_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler = AsyncMock()
    scheduler_service.register_scheduler_handler("cleanup", handler)
    monkeypatch.setattr(
        scheduler_service.repository,
        "get_job_spec",
        AsyncMock(return_value=make_job()),
    )
    monkeypatch.setattr(
        scheduler_service.repository,
        "decode_job_payload",
        lambda _job: ({}, ["a"], {"enabled": True}),
    )

    await scheduler_service.execute_persistent_job("cleanup")

    handler.assert_awaited_once_with("a", enabled=True)


async def test_execute_persistent_job_dispatches_sync_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler = MagicMock(return_value="done")
    scheduler_service.register_scheduler_handler("cleanup", handler)
    monkeypatch.setattr(
        scheduler_service.repository,
        "get_job_spec",
        AsyncMock(return_value=make_job()),
    )
    monkeypatch.setattr(
        scheduler_service.repository,
        "decode_job_payload",
        lambda _job: ({}, ["a"], {"enabled": True}),
    )

    await scheduler_service.execute_persistent_job("cleanup")

    handler.assert_called_once_with("a", enabled=True)


async def test_execute_persistent_job_returns_for_missing_or_disabled_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler = AsyncMock()
    decode_job_payload = MagicMock(return_value=({}, [], {}))
    scheduler_service.register_scheduler_handler("cleanup", handler)
    get_job_spec = AsyncMock(side_effect=[None, make_job(enabled=False)])
    monkeypatch.setattr(scheduler_service.repository, "get_job_spec", get_job_spec)
    monkeypatch.setattr(
        scheduler_service.repository,
        "decode_job_payload",
        decode_job_payload,
    )

    await scheduler_service.execute_persistent_job("missing")
    await scheduler_service.execute_persistent_job("disabled")

    handler.assert_not_awaited()
    decode_job_payload.assert_not_called()


async def test_execute_persistent_job_logs_missing_handler(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        scheduler_service.repository,
        "get_job_spec",
        AsyncMock(return_value=make_job(handler_key="missing")),
    )
    decode_job_payload = MagicMock(return_value=({}, [], {}))
    monkeypatch.setattr(
        scheduler_service.repository,
        "decode_job_payload",
        decode_job_payload,
    )

    await scheduler_service.execute_persistent_job("cleanup")

    decode_job_payload.assert_not_called()
    assert "Scheduled job cleanup has no registered handler missing" in caplog.text


async def test_remove_persistent_job_removes_runtime_and_persisted_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_scheduler = FakeScheduler()
    delete_job_spec = AsyncMock(return_value=(1, True))
    monkeypatch.setattr(scheduler_service, "scheduler", fake_scheduler)
    monkeypatch.setattr(
        scheduler_service.repository, "delete_job_spec", delete_job_spec
    )

    result = await scheduler_service.remove_persistent_job("cleanup")

    assert result == (1, True)
    assert fake_scheduler.removed == ["cleanup"]
    delete_job_spec.assert_awaited_once_with("cleanup")


async def test_remove_persistent_job_ignores_missing_runtime_job(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake_scheduler = FakeScheduler()
    fake_scheduler.missing_jobs.add("cleanup")
    delete_job_spec = AsyncMock(return_value=(0, False))
    monkeypatch.setattr(scheduler_service, "scheduler", fake_scheduler)
    monkeypatch.setattr(
        scheduler_service.repository, "delete_job_spec", delete_job_spec
    )
    caplog.set_level(logging.DEBUG, logger=scheduler_service.logger.name)

    result = await scheduler_service.remove_persistent_job("cleanup")

    assert result == (0, False)
    delete_job_spec.assert_awaited_once_with("cleanup")
    assert "Runtime scheduler job cleanup was not present" in caplog.text


async def test_remove_persistent_job_propagates_scheduler_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_scheduler = FakeScheduler()
    fake_scheduler.remove_errors["cleanup"] = RuntimeError("scheduler unavailable")
    delete_job_spec = AsyncMock()
    monkeypatch.setattr(scheduler_service, "scheduler", fake_scheduler)
    monkeypatch.setattr(
        scheduler_service.repository, "delete_job_spec", delete_job_spec
    )

    with pytest.raises(RuntimeError, match="scheduler unavailable"):
        await scheduler_service.remove_persistent_job("cleanup")

    delete_job_spec.assert_not_awaited()
