"""Platform capability registry for Lingchu Bot."""

from .registry import (
    PlatformAdapterConflictError,
    PlatformCapability,
    PlatformProfile,
    get_platform_profile,
    get_supported_adapter_names,
    get_supported_adapters,
    is_adapter_enabled,
    is_known_adapter,
    iter_platform_profiles,
    parse_configured_adapters,
    resolve_enabled_adapters,
    validate_platform_adapter_selection,
)

__all__ = [
    "PlatformAdapterConflictError",
    "PlatformCapability",
    "PlatformProfile",
    "get_platform_profile",
    "get_supported_adapter_names",
    "get_supported_adapters",
    "is_adapter_enabled",
    "is_known_adapter",
    "iter_platform_profiles",
    "parse_configured_adapters",
    "resolve_enabled_adapters",
    "validate_platform_adapter_selection",
]
