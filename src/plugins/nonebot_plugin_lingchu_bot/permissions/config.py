"""TOML-backed permission configuration APIs."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass

from ..core.config import get_runtime_config_file, runtime_config_defaults
from ..database.toml_store import (
    DatabaseError,
    load_toml_dict_async,
    write_toml_dict_file_async,
)

PASSTHROUGH_KEY = "permission_platform_runtime_passthrough"


@dataclass(frozen=True, slots=True)
class PlatformPermissionMappingUpdate:
    platform_id: str | None
    enabled: bool


async def get_platform_runtime_passthrough_config() -> bool | dict[str, bool]:
    path = get_runtime_config_file()
    try:
        data = await load_toml_dict_async(
            path, default=runtime_config_defaults(), merge_default=True
        )
    except DatabaseError:
        return True
    value = data.get(PASSTHROUGH_KEY, True)
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        return {str(key): bool(item) for key, item in value.items()}
    return True


async def update_platform_runtime_passthrough_config(
    request: PlatformPermissionMappingUpdate,
) -> bool | dict[str, bool]:
    path = get_runtime_config_file()
    try:
        data = await load_toml_dict_async(
            path, default=runtime_config_defaults(), merge_default=True
        )
    except DatabaseError:
        data = runtime_config_defaults()
    if request.platform_id is None:
        data[PASSTHROUGH_KEY] = request.enabled
    else:
        current = data.get(PASSTHROUGH_KEY, {})
        values = current if isinstance(current, dict) else {}
        values[str(request.platform_id)] = request.enabled
        data[PASSTHROUGH_KEY] = values
    with contextlib.suppress(DatabaseError):
        await write_toml_dict_file_async(path, data)
    if request.platform_id is None:
        return request.enabled
    final = data.get(PASSTHROUGH_KEY, {})
    if isinstance(final, dict):
        return {str(key): bool(item) for key, item in final.items()}
    return request.enabled
