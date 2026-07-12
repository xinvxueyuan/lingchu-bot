"""Startup validation and seeding for permissions."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import logging
from typing import Any

from ..core.runtime_config import get_runtime_config
from ..handle.menu import MENU_FEATURES
from ..platforms import iter_platform_profiles
from ..repositories import permissions as repo
from .platforms import iter_default_identity_groups

logger = logging.getLogger(__name__)


class PermissionConfigError(RuntimeError):
    """Permission configuration is invalid and startup must stop."""


async def validate_and_seed_permission_system() -> None:
    superusers = _resolve_superusers_config()
    _validate_superusers(superusers)

    await repo.seed_identity_groups(iter_default_identity_groups())
    await _sync_superusers(superusers)


def _resolve_superusers_config() -> dict[str, dict[str, str]]:
    configured = get_runtime_config().lingchu_superusers
    if configured is None:
        raise PermissionConfigError("LINGCHU_SUPERUSERS is required")
    return _normalize_superusers_mapping(configured)


def _normalize_superusers_mapping(
    raw: Mapping[str, Mapping[str, str | int]],
) -> dict[str, dict[str, str]]:
    return {
        str(uid): {
            str(platform_id): str(account_id)
            for platform_id, account_id in accounts.items()
        }
        for uid, accounts in raw.items()
    }


def _validate_superusers(superusers: Mapping[str, Mapping[str, str]]) -> None:
    if not superusers:
        raise PermissionConfigError("LINGCHU_SUPERUSERS cannot be empty")

    known_platforms = {profile.platform_id for profile in iter_platform_profiles()}
    seen_accounts: set[tuple[str, str]] = set()
    for uid, accounts in superusers.items():
        if not uid.strip():
            raise PermissionConfigError("SUPERUSERS UID cannot be empty")
        if not accounts:
            raise PermissionConfigError(
                f"SUPERUSERS UID {uid!r} has no platform accounts"
            )
        for platform_id, account_id in accounts.items():
            if platform_id not in known_platforms:
                raise PermissionConfigError(
                    f"Unknown SUPERUSERS platform: {platform_id}"
                )
            normalized_account_id = _validate_platform_account_id(
                platform_id,
                account_id,
            )
            account_key = (platform_id, normalized_account_id)
            if account_key in seen_accounts:
                raise PermissionConfigError(
                    f"Duplicate SUPERUSERS account binding: {platform_id}/{account_id}"
                )
            seen_accounts.add(account_key)


def _validate_platform_account_id(platform_id: str, account_id: Any) -> str:
    value = str(account_id).strip()
    if not value:
        raise PermissionConfigError(f"{platform_id} SUPERUSERS account cannot be empty")
    if platform_id == "qq":
        try:
            parsed = int(value)
        except ValueError as exc:
            raise PermissionConfigError(
                "QQ SUPERUSERS account must be a positive int"
            ) from exc
        if parsed <= 0:
            raise PermissionConfigError("QQ SUPERUSERS account must be a positive int")
        return str(parsed)
    return value


async def _sync_superusers(superusers: Mapping[str, Mapping[str, str]]) -> None:
    for uid, accounts in superusers.items():
        await repo.upsert_identity_user(uid, uid)
        await repo.upsert_membership(
            uid=uid,
            group_id=repo.SUPERUSERS_GROUP_ID,
            source=repo.SUPERUSER_SOURCE,
        )
        for platform_id, account_id in accounts.items():
            normalized_account_id = _validate_platform_account_id(
                platform_id,
                account_id,
            )
            await repo.bind_platform_account(
                uid=uid,
                platform_id=platform_id,
                account_id=normalized_account_id,
                display_name=uid,
            )

    grant_results = await asyncio.gather(
        *(
            repo.grant_command(
                group_id=repo.SUPERUSERS_GROUP_ID,
                command_key=feature.command_key,
            )
            for feature in MENU_FEATURES
        ),
        return_exceptions=True,
    )
    for feature, result in zip(MENU_FEATURES, grant_results, strict=True):
        if isinstance(result, Exception):
            logger.warning(
                "Failed to grant command during superuser sync: %s",
                feature.command_key,
                exc_info=result,
            )
