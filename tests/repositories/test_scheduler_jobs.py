from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.models import ScheduledJob
from src.plugins.nonebot_plugin_lingchu_bot.repositories import scheduler_jobs


@pytest.mark.asyncio
async def test_save_job_spec_upserts_by_job_id() -> None:
    job = MagicMock(spec=ScheduledJob)
    upsert_mock = AsyncMock(return_value=job)

    with patch.object(scheduler_jobs, "upsert", upsert_mock):
        result = await scheduler_jobs.save_job_spec(
            job_id="cleanup-messages",
            handler_key="message_store.cleanup_expired_messages",
            trigger_type="cron",
            trigger_kwargs={"minute": "0", "hour": "3"},
            args=["group-1"],
            kwargs={"保留天数": 7},
            enabled=False,
            coalesce=False,
            max_instances=2,
            misfire_grace_time=30,
        )

    assert result is job
    upsert_mock.assert_awaited_once()
    assert upsert_mock.call_args.args[0] is ScheduledJob
    values = upsert_mock.call_args.args[1]
    assert values["job_id"] == "cleanup-messages"
    assert values["handler_key"] == "message_store.cleanup_expired_messages"
    assert values["trigger_type"] == "cron"
    assert values["trigger_kwargs"] == '{"hour":"3","minute":"0"}'
    assert values["args"] == '["group-1"]'
    assert values["kwargs"] == '{"保留天数":7}'
    assert values["enabled"] is False
    assert values["coalesce"] is False
    assert values["max_instances"] == 2
    assert values["misfire_grace_time"] == 30
    assert isinstance(values["created_at"], datetime)
    assert isinstance(values["updated_at"], datetime)
    assert upsert_mock.call_args.kwargs["conflict_fields"] == ["job_id"]
    update_values = upsert_mock.call_args.kwargs["update_values"]
    assert "created_at" not in update_values
    assert update_values["handler_key"] == "message_store.cleanup_expired_messages"
    assert update_values["trigger_type"] == "cron"
    assert update_values["trigger_kwargs"] == '{"hour":"3","minute":"0"}'
    assert update_values["args"] == '["group-1"]'
    assert update_values["kwargs"] == '{"保留天数":7}'
    assert update_values["enabled"] is False
    assert update_values["coalesce"] is False
    assert update_values["max_instances"] == 2
    assert update_values["misfire_grace_time"] == 30
    assert isinstance(update_values["updated_at"], datetime)


@pytest.mark.asyncio
async def test_save_job_spec_defaults_args_and_kwargs() -> None:
    upsert_mock = AsyncMock(return_value=MagicMock(spec=ScheduledJob))

    with patch.object(scheduler_jobs, "upsert", upsert_mock):
        await scheduler_jobs.save_job_spec(
            job_id="cleanup-messages",
            handler_key="message_store.cleanup_expired_messages",
            trigger_type="cron",
            trigger_kwargs={"hour": "3"},
        )

    values = upsert_mock.call_args.args[1]
    assert values["args"] == "[]"
    assert values["kwargs"] == "{}"
    assert values["enabled"] is True
    assert values["coalesce"] is True
    assert values["max_instances"] == 1
    assert values["misfire_grace_time"] is None


@pytest.mark.asyncio
async def test_get_job_spec_filters_by_job_id() -> None:
    job = MagicMock(spec=ScheduledJob)
    get_one_mock = AsyncMock(return_value=job)

    with patch.object(scheduler_jobs, "get_one", get_one_mock):
        result = await scheduler_jobs.get_job_spec("cleanup-messages")

    assert result is job
    get_one_mock.assert_awaited_once_with(
        ScheduledJob,
        {"job_id": "cleanup-messages"},
    )


@pytest.mark.asyncio
async def test_list_enabled_job_specs_filters_enabled() -> None:
    jobs = [MagicMock(spec=ScheduledJob)]
    list_items_mock = AsyncMock(return_value=jobs)

    with patch.object(scheduler_jobs, "list_items", list_items_mock):
        result = await scheduler_jobs.list_enabled_job_specs()

    assert result == jobs
    list_items_mock.assert_awaited_once_with(
        ScheduledJob,
        filters={"enabled": True},
        limit=1000,
        order_by=["job_id"],
    )


@pytest.mark.asyncio
async def test_delete_job_spec_filters_by_job_id() -> None:
    delete_mock = AsyncMock(return_value=(1, True))

    with patch.object(scheduler_jobs, "delete", delete_mock):
        result = await scheduler_jobs.delete_job_spec("cleanup-messages")

    assert result == (1, True)
    delete_mock.assert_awaited_once_with(
        ScheduledJob,
        {"job_id": "cleanup-messages"},
    )


def test_decode_job_payload_returns_typed_payloads() -> None:
    job = MagicMock(spec=ScheduledJob)
    job.trigger_kwargs = '{"hour":"3"}'
    job.args = '["group-1"]'
    job.kwargs = '{"limit":100}'

    assert scheduler_jobs.decode_job_payload(job) == (
        {"hour": "3"},
        ["group-1"],
        {"limit": 100},
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("trigger_kwargs", "[]", "trigger_kwargs must be a JSON object"),
        ("args", "{}", "args must be a JSON array"),
        ("kwargs", "[]", "kwargs must be a JSON object"),
    ],
)
def test_decode_job_payload_rejects_invalid_shapes(
    field: str,
    value: str,
    message: str,
) -> None:
    job = MagicMock(spec=ScheduledJob)
    job.trigger_kwargs = '{"hour":"3"}'
    job.args = "[]"
    job.kwargs = "{}"
    setattr(job, field, value)

    with pytest.raises(ValueError, match=message):
        scheduler_jobs.decode_job_payload(job)
