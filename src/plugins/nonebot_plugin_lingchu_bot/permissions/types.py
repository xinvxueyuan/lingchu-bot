"""Permission system value objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PermissionReason = Literal[
    "superuser",
    "granted",
    "anonymous",
    "missing_grant",
    "unknown_command",
]


@dataclass(frozen=True, slots=True)
class PlatformIdentityGroupSeed:
    group_id: str
    platform_id: str
    display_name: str
    parent_group_id: str | None = None


@dataclass(frozen=True, slots=True)
class PermissionContext:
    platform_id: str
    adapter_id: str | None
    account_id: str | None
    scope_type: str = "global"
    scope_id: str | None = None
    uid: str | None = None
    runtime_group_ids: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    allowed: bool
    reason: PermissionReason
    uid: str | None = None
    matched_groups: frozenset[str] = frozenset()
