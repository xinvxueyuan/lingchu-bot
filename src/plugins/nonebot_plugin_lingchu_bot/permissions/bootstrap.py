"""Startup validation and seeding for permissions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ..core.config import get_runtime_config
from ..handle.menu import MENU_FEATURES
from ..platforms import iter_platform_profiles
from ..repositories import permissions as repo
from .platforms import iter_default_identity_groups

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session


class PermissionConfigError(RuntimeError):
    """Permission configuration is invalid and startup must stop."""


async def validate_and_seed_permission_system(
    session: AsyncSession | async_scoped_session[AsyncSession],
) -> None:
    superusers = _resolve_superusers_config()
    _validate_superusers(superusers)

    await repo.seed_identity_groups(session, iter_default_identity_groups())
    await _sync_superusers(session, superusers)


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


async def _sync_superusers(
    session: AsyncSession | async_scoped_session[AsyncSession],
    superusers: Mapping[str, Mapping[str, str]],
) -> None:
    configured_accounts: set[tuple[str, str]] = set()
    for uid, accounts in superusers.items():
        await repo.upsert_identity_user(session, uid, uid)
        await repo.upsert_membership(
            session,
            uid=uid,
            group_id=repo.SUPERUSERS_GROUP_ID,
            source=repo.SUPERUSER_SOURCE,
        )
        for platform_id, account_id in accounts.items():
            normalized_account_id = _validate_platform_account_id(
                platform_id,
                account_id,
            )
            configured_accounts.add((platform_id, normalized_account_id))
            await repo.bind_platform_account(
                session,
                uid=uid,
                platform_id=platform_id,
                account_id=normalized_account_id,
                display_name=uid,
                source=repo.SUPERUSER_SOURCE,
            )

    await repo.delete_stale_superuser_accounts(
        session,
        configured_accounts=configured_accounts,
    )
    await repo.delete_stale_superuser_memberships(
        session,
        configured_uids=superusers.keys(),
    )
    configured_command_keys = [feature.command_key for feature in MENU_FEATURES]
    await repo.delete_stale_superuser_grants(
        session,
        configured_command_keys=configured_command_keys,
    )
    for feature in MENU_FEATURES:
        await repo.grant_command(
            session,
            group_id=repo.SUPERUSERS_GROUP_ID,
            command_key=feature.command_key,
        )
