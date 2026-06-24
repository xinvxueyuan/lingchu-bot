"""Subject policy repository helpers for blocked and protected users."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import or_

from ..database.models import SubjectPolicyEntry
from ..database.orm_crud import delete, get_one, upsert
from ..repositories.blocklist import GLOBAL_SCOPE_KEY, BlockScope, scope_key_for

SubjectPolicyType = Literal["blocked", "protected"]


@dataclass(frozen=True, slots=True)
class SubjectPolicyUpsert:
    policy_type: SubjectPolicyType
    platform_id: str
    adapter_id: str
    bot_id: str
    scope: BlockScope
    group_id: str | int | None
    user_id: str | int
    operator_id: str | int | None
    reason: str | None
    expires_at: datetime | None
    protocol_id: str | None = None


def expires_at_from_duration(duration: int | None) -> datetime | None:
    if duration is None or duration <= 0:
        return None
    return datetime.now(UTC) + timedelta(seconds=duration)


async def upsert_subject_policy(request: SubjectPolicyUpsert) -> SubjectPolicyEntry:
    now = datetime.now(UTC)
    scope_key = scope_key_for(request.scope, request.group_id)
    values = {
        "policy_type": request.policy_type,
        "platform_id": request.platform_id,
        "adapter_id": request.adapter_id,
        "protocol_id": request.protocol_id,
        "bot_id": request.bot_id,
        "scope": request.scope,
        "scope_key": scope_key,
        "group_id": None if request.scope == "global" else str(request.group_id),
        "user_id": str(request.user_id),
        "operator_id": None
        if request.operator_id is None
        else str(request.operator_id),
        "reason": request.reason,
        "expires_at": request.expires_at,
        "created_at": now,
        "updated_at": now,
    }
    return await upsert(
        SubjectPolicyEntry,
        values,
        conflict_fields=[
            "policy_type",
            "platform_id",
            "adapter_id",
            "protocol_id",
            "bot_id",
            "scope",
            "scope_key",
            "user_id",
        ],
        update_values={
            "operator_id": values["operator_id"],
            "reason": request.reason,
            "expires_at": request.expires_at,
            "updated_at": now,
        },
    )


async def remove_subject_policy(  # noqa: PLR0913
    *,
    policy_type: SubjectPolicyType,
    platform_id: str,
    adapter_id: str,
    protocol_id: str | None = None,
    bot_id: str,
    scope: BlockScope,
    group_id: str | int | None,
    user_id: str | int,
) -> tuple[int, bool]:
    filters = {
        "policy_type": policy_type,
        "platform_id": platform_id,
        "adapter_id": adapter_id,
        "bot_id": bot_id,
        "scope": scope,
        "scope_key": scope_key_for(scope, group_id),
        "user_id": str(user_id),
    }
    if protocol_id is not None:
        filters["protocol_id"] = protocol_id
    return await delete(SubjectPolicyEntry, filters)


async def clear_subject_policy(  # noqa: PLR0913
    *,
    policy_type: SubjectPolicyType,
    platform_id: str,
    adapter_id: str,
    protocol_id: str | None = None,
    bot_id: str,
    scope: BlockScope,
    group_id: str | int | None,
) -> tuple[int, bool]:
    filters = {
        "policy_type": policy_type,
        "platform_id": platform_id,
        "adapter_id": adapter_id,
        "bot_id": bot_id,
        "scope": scope,
        "scope_key": scope_key_for(scope, group_id),
    }
    if protocol_id is not None:
        filters["protocol_id"] = protocol_id
    return await delete(SubjectPolicyEntry, filters)


async def find_active_subject_policy(  # noqa: PLR0913
    *,
    policy_type: SubjectPolicyType,
    platform_id: str,
    adapter_id: str,
    protocol_id: str | None = None,
    bot_id: str,
    group_id: str | int,
    user_id: str | int,
) -> SubjectPolicyEntry | None:
    global_entry = await _find_active_subject_policy_for_scope(
        policy_type=policy_type,
        platform_id=platform_id,
        adapter_id=adapter_id,
        protocol_id=protocol_id,
        bot_id=bot_id,
        scope="global",
        group_id=None,
        user_id=user_id,
    )
    if global_entry is not None:
        return global_entry
    return await _find_active_subject_policy_for_scope(
        policy_type=policy_type,
        platform_id=platform_id,
        adapter_id=adapter_id,
        protocol_id=protocol_id,
        bot_id=bot_id,
        scope="group",
        group_id=group_id,
        user_id=user_id,
    )


async def _find_active_subject_policy_for_scope(  # noqa: PLR0913
    *,
    policy_type: SubjectPolicyType,
    platform_id: str,
    adapter_id: str,
    protocol_id: str | None = None,
    bot_id: str,
    scope: BlockScope,
    group_id: str | int | None,
    user_id: str | int,
) -> SubjectPolicyEntry | None:
    filters = {
        "policy_type": policy_type,
        "platform_id": platform_id,
        "adapter_id": adapter_id,
        "bot_id": bot_id,
        "scope": scope,
        "scope_key": GLOBAL_SCOPE_KEY
        if scope == "global"
        else scope_key_for(scope, group_id),
        "user_id": str(user_id),
    }
    if protocol_id is not None:
        filters["protocol_id"] = protocol_id
    entry = await get_one(SubjectPolicyEntry, filters)
    if entry is None:
        return None
    if entry.expires_at is None or entry.expires_at > datetime.now(UTC):
        return entry
    await delete(SubjectPolicyEntry, filters)
    return None


def active_subject_policy_condition() -> object:
    now = datetime.now(UTC)
    return or_(
        SubjectPolicyEntry.expires_at.is_(None),
        SubjectPolicyEntry.expires_at > now,
    )
