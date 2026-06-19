"""Compatibility repository for UID/platform account mapping APIs."""

from __future__ import annotations

from ..database.models import IdentityUser, PlatformAccount
from .permissions import (
    bind_platform_account,
    get_platform_account,
    get_user_by_platform_account,
    upsert_identity_user,
)

__all__ = [
    "IdentityUser",
    "PlatformAccount",
    "bind_platform_account",
    "get_platform_account",
    "get_user_by_platform_account",
    "upsert_identity_user",
]
