"""Adapter-to-platform registry.

The bot should make business decisions against platform capabilities instead
of concrete NoneBot adapters. Adapter modules stay at the edge of the system.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class PlatformCapability(StrEnum):
    """Cross-platform management features Lingchu can reason about."""

    GROUP_MANAGEMENT = "group_management"
    MEMBER_MODERATION = "member_moderation"
    MEMBER_PROFILE = "member_profile"
    GROUP_PROFILE = "group_profile"
    ANNOUNCEMENT = "announcement"
    MESSAGE_STORE = "message_store"
    API_AUDIT = "api_audit"


@dataclass(frozen=True, slots=True)
class PlatformProfile:
    """Runtime profile shared by one or more concrete adapters."""

    platform_id: str
    display_name: str
    adapter_names: frozenset[str]
    nonebot_adapters: frozenset[str]
    capabilities: frozenset[PlatformCapability]
    implemented: bool = True


QQ_CAPABILITIES: Final[frozenset[PlatformCapability]] = frozenset(
    {
        PlatformCapability.GROUP_MANAGEMENT,
        PlatformCapability.MEMBER_MODERATION,
        PlatformCapability.MEMBER_PROFILE,
        PlatformCapability.GROUP_PROFILE,
        PlatformCapability.ANNOUNCEMENT,
        PlatformCapability.MESSAGE_STORE,
        PlatformCapability.API_AUDIT,
    }
)

PLATFORM_PROFILES: Final[tuple[PlatformProfile, ...]] = (
    PlatformProfile(
        platform_id="qq",
        display_name="QQ",
        adapter_names=frozenset(
            {
                "milky",
                "onebot v11",
                "onebot v12",
                "onebot11",
                "onebot12",
                "qq",
            }
        ),
        nonebot_adapters=frozenset({"~milky", "~onebot.v11"}),
        capabilities=QQ_CAPABILITIES,
    ),
)

_ADAPTER_PROFILE_INDEX: Final[dict[str, PlatformProfile]] = {
    adapter_name.casefold(): profile
    for profile in PLATFORM_PROFILES
    for adapter_name in profile.adapter_names
}


def iter_platform_profiles(
    *,
    implemented_only: bool = True,
) -> tuple[PlatformProfile, ...]:
    """Return known platform profiles."""
    if implemented_only:
        return tuple(profile for profile in PLATFORM_PROFILES if profile.implemented)
    return PLATFORM_PROFILES


def get_platform_profile(adapter_name: str) -> PlatformProfile | None:
    """Resolve a concrete adapter name to its cross-platform profile."""
    return _ADAPTER_PROFILE_INDEX.get(adapter_name.casefold())


def get_supported_adapters() -> set[str]:
    """Return NoneBot adapter identifiers implemented by this plugin."""
    return {
        adapter
        for profile in iter_platform_profiles()
        for adapter in profile.nonebot_adapters
    }


def get_supported_adapter_names() -> tuple[str, ...]:
    """Return display names for startup logs and diagnostics."""
    names = {
        adapter_name
        for profile in iter_platform_profiles()
        for adapter_name in profile.adapter_names
    }
    return tuple(sorted(names))
