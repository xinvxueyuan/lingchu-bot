"""JSON5-backed permission configuration APIs."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.runtime_config import get_runtime_config_file, runtime_config_defaults
from ..database.json5_store import RobustAsyncJSON5DB

PASSTHROUGH_KEY = "permission_platform_runtime_passthrough"


@dataclass(frozen=True, slots=True)
class PlatformPermissionMappingUpdate:
    platform_id: str | None
    enabled: bool


async def get_platform_runtime_passthrough_config() -> bool | dict[str, bool]:
    async with RobustAsyncJSON5DB(
        get_runtime_config_file(),
        default=runtime_config_defaults(),
    ) as db:
        value = await db.read(PASSTHROUGH_KEY, default=True)
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        return {str(key): bool(item) for key, item in value.items()}
    return True


async def update_platform_runtime_passthrough_config(
    request: PlatformPermissionMappingUpdate,
) -> bool | dict[str, bool]:
    async with RobustAsyncJSON5DB(
        get_runtime_config_file(),
        default=runtime_config_defaults(),
    ) as db:
        if request.platform_id is None:
            await db.set(PASSTHROUGH_KEY, request.enabled)
            return request.enabled
        current = await db.read(PASSTHROUGH_KEY, {})
        values = current if isinstance(current, dict) else {}
        values[str(request.platform_id)] = request.enabled
        await db.set(PASSTHROUGH_KEY, values)
        return {str(key): bool(item) for key, item in values.items()}
