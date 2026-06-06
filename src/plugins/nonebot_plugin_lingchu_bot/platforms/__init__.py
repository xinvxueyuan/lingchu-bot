"""Platform capability registry for Lingchu Bot."""

from .registry import (
    PlatformCapability,
    PlatformProfile,
    get_platform_profile,
    get_supported_adapter_names,
    get_supported_adapters,
    iter_platform_profiles,
)

__all__ = [
    "PlatformCapability",
    "PlatformProfile",
    "get_platform_profile",
    "get_supported_adapter_names",
    "get_supported_adapters",
    "iter_platform_profiles",
]
