"""Typed mutable permission configuration APIs."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass

from _lingchu_bot_contracts import MutableRuntimeSettings

from ..core.mutable_settings import (
    MutableSettingsError,
    load_mutable_settings,
    save_mutable_settings,
)


@dataclass(frozen=True, slots=True)
class PlatformPermissionMappingUpdate:
    platform_id: str | None
    enabled: bool


async def get_platform_runtime_passthrough_config() -> bool | dict[str, bool]:
    try:
        return (await load_mutable_settings()).permission_platform_runtime_passthrough
    except MutableSettingsError:
        return True


async def update_platform_runtime_passthrough_config(
    request: PlatformPermissionMappingUpdate,
) -> bool | dict[str, bool]:
    try:
        settings = await load_mutable_settings()
    except MutableSettingsError:
        settings = MutableRuntimeSettings()
    current = settings.permission_platform_runtime_passthrough
    if request.platform_id is None:
        updated: bool | dict[str, bool] = request.enabled
    else:
        values = dict(current) if isinstance(current, dict) else {}
        values[str(request.platform_id)] = request.enabled
        updated = values
    with contextlib.suppress(MutableSettingsError):
        await save_mutable_settings(
            settings.model_copy(
                update={"permission_platform_runtime_passthrough": updated}
            )
        )
    return updated
