"""Adapter-to-platform registry.

The bot should make business decisions against platform capabilities instead
of concrete NoneBot adapters. Adapter modules stay at the edge of the system.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final, cast

from ..core.runtime_config import get_runtime_config

type AdapterConfig = str | list[str] | tuple[str, ...] | None
_UNSET: Final = object()


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
    nonebot_adapters: tuple[str, ...]
    adapter_name_map: tuple[tuple[str, str], ...]
    capabilities: frozenset[PlatformCapability]
    implemented: bool = True


class PlatformAdapterConflictError(RuntimeError):
    """同一平台适配器互斥配置错误。"""

    def __init__(
        self,
        *,
        platform_id: str,
        adapters: frozenset[str],
        source: str,
    ) -> None:
        self.platform_id = platform_id
        self.adapters = adapters
        self.source = source
        adapter_list = ", ".join(sorted(adapters))
        # 找出该平台的所有已知适配器及其用户友好的名称
        profile = next(
            (p for p in PLATFORM_PROFILES if p.platform_id == platform_id), None
        )
        if profile:
            # adapter_name_map: (用户可见名, NoneBot ID)
            # -> 反转为 {NoneBot ID: 用户可见名}
            adapter_display_map = {
                nb_id: display_name for display_name, nb_id in profile.adapter_name_map
            }
            available = ", ".join(
                f"{pid} ({adapter_display_map.get(pid, 'unknown')})"
                for pid in sorted(profile.nonebot_adapters)
            )
        else:
            available = ", ".join(sorted(adapters))
        suggestion = (
            "请在 NoneBot2 配置文件(.env.dev)中通过 LINGCHUAdapter 指定要启用的适配器，"
            "只保留一个。例如：LINGCHUAdapter=~onebot.v11"
        )
        super().__init__(
            f"Lingchu 平台适配器冲突：平台 {platform_id!r} "
            f"检测到多个适配器同时运行：{adapter_list}。"
            f"每个平台只能由一个适配器提供服务。"
            f"\n该平台支持的适配器：{available}"
            f"\n{suggestion}"
        )


class PlatformAdapterNotLoadedError(RuntimeError):
    """Lingchu selected an adapter that NoneBot did not register."""

    def __init__(
        self,
        *,
        adapter_id: str,
        registered_adapters: frozenset[str],
    ) -> None:
        self.adapter_id = adapter_id
        self.registered_adapters = registered_adapters
        registered = (
            ", ".join(sorted(registered_adapters)) if registered_adapters else "none"
        )
        profile = _ADAPTER_PROFILE_INDEX.get(adapter_id.casefold())
        display_name = adapter_id
        if profile is not None:
            display_map = {
                nb_id: display for display, nb_id in profile.adapter_name_map
            }
            display_name = display_map.get(adapter_id, adapter_id)
        super().__init__(
            "Lingchu 已选择适配器 "
            f"{adapter_id} ({display_name})，但 NoneBot 未加载/注册该适配器。"
            f"\n当前 NoneBot 已注册的 Lingchu 已知适配器：{registered}"
            "\n请加载匹配的 NoneBot 适配器，或修改 LINGCHUAdapter。"
        )


class PlatformAdapterUnknownError(RuntimeError):
    """Lingchu adapter configuration contains unknown adapter ids."""

    def __init__(self, adapters: frozenset[str]) -> None:
        self.adapters = adapters
        adapter_list = ", ".join(sorted(adapters))
        known = ", ".join(
            adapter_id
            for profile in iter_platform_profiles()
            for adapter_id in profile.nonebot_adapters
        )
        super().__init__(
            "LINGCHUAdapter 声明了 Lingchu 尚未实现或无法识别的适配器："
            f"{adapter_list}。"
            f"\n当前可选择的适配器：{known}"
            "\n请改用已实现的 Lingchu 适配器，或等待对应平台 profile 实现。"
        )


UNKNOWN_PLATFORM_ID: Final[str] = "unknown"

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
        nonebot_adapters=("~onebot.v11", "~milky", "~qq", "~onebot.v12"),
        adapter_name_map=(
            ("onebot v11", "~onebot.v11"),
            ("onebot11", "~onebot.v11"),
            ("onebot v12", "~onebot.v12"),
            ("onebot12", "~onebot.v12"),
            ("milky", "~milky"),
            ("qq", "~qq"),
        ),
        capabilities=QQ_CAPABILITIES,
    ),
)

_ADAPTER_PROFILE_INDEX: Final[dict[str, PlatformProfile]] = {
    adapter_id.casefold(): profile
    for profile in PLATFORM_PROFILES
    for adapter_id in profile.nonebot_adapters
} | {
    adapter_name.casefold(): profile
    for profile in PLATFORM_PROFILES
    for adapter_name, _adapter_id in profile.adapter_name_map
}

_ADAPTER_ID_INDEX: Final[dict[str, str]] = {
    adapter_id.casefold(): adapter_id
    for profile in PLATFORM_PROFILES
    for adapter_id in profile.nonebot_adapters
} | {
    adapter_name.casefold(): adapter_id
    for profile in PLATFORM_PROFILES
    for adapter_name, adapter_id in profile.adapter_name_map
}


def iter_platform_profiles(
    *,
    implemented_only: bool = True,
) -> tuple[PlatformProfile, ...]:
    """Return known platform profiles."""
    if implemented_only:
        return tuple(profile for profile in PLATFORM_PROFILES if profile.implemented)
    return PLATFORM_PROFILES


def parse_configured_adapters(configured: AdapterConfig) -> tuple[str, ...]:
    """Parse Lingchu adapter configuration into normalized adapter ids."""
    if configured is None:
        return ()
    raw_values: tuple[Any, ...]
    if isinstance(configured, str):
        raw_values = tuple(configured.split("+"))
    elif isinstance(configured, (list, tuple)):
        raw_values = tuple(configured)
    else:
        raw_values = (configured,)

    parsed: list[str] = []
    for raw_value in raw_values:
        value = str(raw_value).strip()
        if not value:
            continue
        normalized = value.casefold()
        if not normalized.startswith("~"):
            normalized = f"~{normalized}"
        parsed.append(normalized)
    return tuple(parsed)


def _global_configured_adapters() -> str | list[str] | tuple[str, ...] | None:
    return get_runtime_config().lingchu_adapter


def _resolve_known_adapter_id(adapter_name: str) -> str | None:
    normalized = adapter_name.strip().casefold()
    if not normalized:
        return None
    if not normalized.startswith("~"):
        normalized = f"~{normalized}"
    return _ADAPTER_ID_INDEX.get(normalized) or _ADAPTER_ID_INDEX.get(
        adapter_name.strip().casefold()
    )


def resolve_adapter_id(adapter_name: str) -> str | None:
    """Resolve a display or NoneBot adapter name to Lingchu's canonical id."""
    return _resolve_known_adapter_id(adapter_name)


def _profile_enabled_adapter(
    profile: PlatformProfile,
    configured_adapters: tuple[str, ...],
    *,
    source: str,
) -> str:
    configured_for_profile = _configured_profile_adapters(profile, configured_adapters)
    if len(configured_for_profile) > 1:
        raise PlatformAdapterConflictError(
            platform_id=profile.platform_id,
            adapters=configured_for_profile,
            source=source,
        )
    if configured_for_profile:
        return next(iter(configured_for_profile))
    return profile.nonebot_adapters[0]


def _configured_profile_adapters(
    profile: PlatformProfile,
    configured_adapters: tuple[str, ...],
) -> frozenset[str]:
    return frozenset(
        adapter
        for adapter in configured_adapters
        if _ADAPTER_PROFILE_INDEX.get(adapter) == profile
    )


def _unknown_configured_adapters(
    configured_adapters: tuple[str, ...],
) -> frozenset[str]:
    return frozenset(
        adapter
        for adapter in configured_adapters
        if _resolve_known_adapter_id(adapter) is None
    )


def resolve_enabled_adapters(
    configured: AdapterConfig | object = _UNSET,
) -> set[str]:
    """Return the single enabled adapter for each implemented platform."""
    raw_config = (
        _global_configured_adapters()
        if configured is _UNSET
        else cast("AdapterConfig", configured)
    )
    configured_adapters = parse_configured_adapters(raw_config)
    unknown_adapters = _unknown_configured_adapters(configured_adapters)
    if unknown_adapters:
        raise PlatformAdapterUnknownError(unknown_adapters)
    return {
        _profile_enabled_adapter(profile, configured_adapters, source="configuration")
        for profile in iter_platform_profiles()
    }


def is_adapter_enabled(
    adapter_name: str,
    configured: AdapterConfig | object = _UNSET,
) -> bool:
    """Return whether a concrete adapter is selected for its platform."""
    adapter_id = _resolve_known_adapter_id(adapter_name)
    if adapter_id is None:
        return False
    return adapter_id in resolve_enabled_adapters(configured)


def is_known_adapter(adapter_name: str) -> bool:
    """Return whether an adapter is part of a known Lingchu platform profile."""
    return _resolve_known_adapter_id(adapter_name) is not None


def validate_platform_adapter_selection(
    registered_adapter_names: tuple[str, ...],
    configured: AdapterConfig | object = _UNSET,
) -> None:
    """Validate runtime adapter registration against Lingchu platform selection."""
    validate_enabled_adapters_loaded(registered_adapter_names, configured)


def resolve_registered_adapters(
    registered_adapter_names: tuple[str, ...],
) -> set[str]:
    """Resolve NoneBot registered adapter names to Lingchu adapter ids."""
    return {
        adapter_id
        for adapter_name in registered_adapter_names
        if (adapter_id := _resolve_known_adapter_id(adapter_name)) is not None
    }


def validate_enabled_adapters_loaded(
    registered_adapter_names: tuple[str, ...],
    configured: AdapterConfig | object = _UNSET,
) -> None:
    """Validate every Lingchu-enabled adapter is registered by NoneBot."""
    raw_config = (
        _global_configured_adapters()
        if configured is _UNSET
        else cast("AdapterConfig", configured)
    )
    enabled = resolve_enabled_adapters(raw_config)
    registered = resolve_registered_adapters(registered_adapter_names)
    for adapter_id in sorted(enabled - registered):
        raise PlatformAdapterNotLoadedError(
            adapter_id=adapter_id,
            registered_adapters=frozenset(registered),
        )


def get_platform_profile(
    adapter_name: str,
    configured: AdapterConfig | object = _UNSET,
) -> PlatformProfile | None:
    """Resolve a concrete adapter name to its cross-platform profile."""
    adapter_id = _resolve_known_adapter_id(adapter_name)
    if adapter_id is None or not is_adapter_enabled(adapter_id, configured):
        return None
    return _ADAPTER_PROFILE_INDEX.get(adapter_id.casefold())


def get_supported_adapters(
    configured: AdapterConfig | object = _UNSET,
) -> set[str]:
    """Return NoneBot adapter identifiers implemented by this plugin."""
    return resolve_enabled_adapters(configured)


def get_supported_adapter_names() -> tuple[str, ...]:
    """Return display names for startup logs and diagnostics."""
    names = {
        adapter_name
        for profile in iter_platform_profiles()
        for adapter_name in profile.adapter_names
    }
    return tuple(sorted(names))
