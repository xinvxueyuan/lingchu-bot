"""Repository helpers for persistent scheduler job specs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ..database.models import ScheduledJob
from ..database.orm_crud import delete, get_one, list_items, upsert


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _json_load(value: str) -> Any:
    return json.loads(value)


async def save_job_spec(  # noqa: PLR0913
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
) -> ScheduledJob:
    now = datetime.now(UTC)
    update_values = {
        "handler_key": handler_key,
        "trigger_type": trigger_type,
        "trigger_kwargs": _json_dump(trigger_kwargs),
        "args": _json_dump(args or []),
        "kwargs": _json_dump(kwargs or {}),
        "enabled": enabled,
        "coalesce": coalesce,
        "max_instances": max_instances,
        "misfire_grace_time": misfire_grace_time,
        "updated_at": now,
    }
    return await upsert(
        ScheduledJob,
        {
            "job_id": job_id,
            **update_values,
            "created_at": now,
        },
        conflict_fields=["job_id"],
        update_values=update_values,
    )


async def get_job_spec(job_id: str) -> ScheduledJob | None:
    return await get_one(ScheduledJob, {"job_id": job_id})


async def list_enabled_job_specs() -> list[ScheduledJob]:
    return await list_items(
        ScheduledJob,
        filters={"enabled": True},
        limit=1000,
        order_by=["job_id"],
    )


async def delete_job_spec(job_id: str) -> tuple[int, bool]:
    return await delete(ScheduledJob, {"job_id": job_id})


def decode_job_payload(
    job: ScheduledJob,
) -> tuple[dict[str, Any], list[Any], dict[str, Any]]:
    trigger_kwargs = _json_load(job.trigger_kwargs)
    args = _json_load(job.args)
    kwargs = _json_load(job.kwargs)
    if not isinstance(trigger_kwargs, dict):
        raise ValueError(  # noqa: TRY003, TRY004
            "scheduled job trigger_kwargs must be a JSON object",
        )
    if not isinstance(args, list):
        raise ValueError(  # noqa: TRY003, TRY004
            "scheduled job args must be a JSON array",
        )
    if not isinstance(kwargs, dict):
        raise ValueError(  # noqa: TRY003, TRY004
            "scheduled job kwargs must be a JSON object",
        )
    return trigger_kwargs, args, kwargs
