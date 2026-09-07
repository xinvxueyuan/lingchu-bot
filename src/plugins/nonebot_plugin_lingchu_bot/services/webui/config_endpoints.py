"""WebUI 配置读写端点逻辑（nonebot 侧）。

提供「基本配置」（runtime-overrides.toml）与「高级配置」（{command_key}.toml）
的读写端点，返回「当前值 + 字段 schema」结构；写回统一走既有唯一写入路径
（``save_mutable_settings`` / ``HandleConfigManager.update_config``），
底层 TOML 读写异常收敛为 500 ``config_io_error``。

复用 ``verify_webui_password`` 简易字符串密码鉴权，不实现任何 JWT/令牌功能。
本模块不依赖驱动器，可在不启动 NoneBot 的情况下导入。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from _lingchu_bot_contracts import MutableRuntimeSettings
from starlette.requests import Request
from starlette.responses import JSONResponse

from ...core.config import get_handle_config_manager
from ...core.handle_config_defaults import HANDLE_DEFAULTS_REGISTRY
from ...core.mutable_settings import (
    MutableSettingsError,
    load_mutable_settings,
    save_mutable_settings,
)
from ...database.toml_store import DatabaseError
from .info import _unauthorized, verify_webui_password

if TYPE_CHECKING:
    from ...core.handle_config_manager import HandleConfig

# 路由路径
WEBUI_CONFIG_BASIC_PATH: str = "/lingchu-bot/webui/v1/config/basic"
WEBUI_CONFIG_ADVANCED_PATH: str = "/lingchu-bot/webui/v1/config/advanced"

# 基本配置字段 schema：平铺数组（每项含 key/type），前端 schema 驱动表单按数组渲染
_BASIC_CONFIG_SCHEMA: list[dict[str, str]] = [
    {"key": "permission_platform_runtime_passthrough", "type": "boolean_or_map"},
    {"key": "command_trigger_overrides", "type": "map"},
    {"key": "menu_page_trigger_overrides", "type": "map"},
]

# 高级配置 defaults 字段的枚举取值集
_ENUM_OPTIONS: dict[str, list[str]] = {
    "audit_level": ["low", "medium", "high"],
    "whitelist_scope": ["group", "global"],
}


def _derive_defaults_schema(command_key: str) -> list[dict[str, Any]]:
    """由默认值 Python 类型推导 single-command defaults 字段 schema。

    推导规则（与 spec 一致）：bool→boolean、int→integer、None→optional_integer、
    str→string/enum；``audit_level`` / ``whitelist_scope`` 固定为枚举。
    返回平铺数组（每项含 key/type/options），与基本配置 schema 形状一致，
    前端按 ``ConfigFieldSchema[]`` 直接驱动表单渲染。
    """
    factory = HANDLE_DEFAULTS_REGISTRY[command_key]
    defaults = factory().get("defaults", {})
    schema: list[dict[str, Any]] = []
    for name, value in defaults.items():
        if name in _ENUM_OPTIONS:
            schema.append(
                {"key": name, "type": "enum", "options": list(_ENUM_OPTIONS[name])}
            )
        elif type(value) is bool:
            schema.append({"key": name, "type": "boolean"})
        elif type(value) is int:
            schema.append({"key": name, "type": "integer"})
        elif value is None:
            schema.append({"key": name, "type": "optional_integer"})
        else:
            schema.append({"key": name, "type": "string"})
    return schema


def _handle_config_to_dict(config: HandleConfig) -> dict[str, Any]:
    """将 HandleConfig 转成 JSON 可序列化字典。"""
    return {
        "enabled": config.enabled,
        "defaults": config.defaults,
        "policies": config.policies,
    }


async def webui_config_basic_endpoint(request: Request) -> JSONResponse:
    """基本配置读写端点：GET 返回当前值 + schema，PUT 校验并落盘。"""
    if not verify_webui_password(request):
        return _unauthorized()
    if request.method == "PUT":
        return await _save_basic_config(request)
    return await _load_basic_config()


async def _load_basic_config() -> JSONResponse:
    try:
        values = (await load_mutable_settings()).to_dict()
    except MutableSettingsError:
        return JSONResponse(status_code=500, content={"detail": "config_io_error"})
    return JSONResponse(content={"values": values, "schema": _BASIC_CONFIG_SCHEMA})


async def _save_basic_config(request: Request) -> JSONResponse:
    payload: object
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "invalid_json"})
    if not isinstance(payload, dict):
        return JSONResponse(
            status_code=400, content={"detail": "request body must be an object"}
        )
    settings_raw = payload.get("settings")
    if not isinstance(settings_raw, dict):
        return JSONResponse(
            status_code=400, content={"detail": "settings must be an object"}
        )
    try:
        settings = MutableRuntimeSettings.from_mapping(settings_raw)
    except (ValueError, TypeError) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    try:
        await save_mutable_settings(settings, flush=True)
    except MutableSettingsError:
        return JSONResponse(status_code=500, content={"detail": "config_io_error"})
    return JSONResponse(content={"ok": True})


async def webui_config_advanced_endpoint(request: Request) -> JSONResponse:
    """高级配置读写端点：GET 返回全部指令配置 + defaults schema，PUT 单指令更新。"""
    if not verify_webui_password(request):
        return _unauthorized()
    if request.method == "PUT":
        return await _save_advanced_config(request)
    return await _load_advanced_config()


async def _load_advanced_config() -> JSONResponse:
    manager = get_handle_config_manager()
    try:
        all_configs = await manager.get_all_configs()
    except Exception:
        return JSONResponse(status_code=500, content={"detail": "config_io_error"})
    commands: dict[str, dict[str, Any]] = {}
    schema: dict[str, list[dict[str, Any]]] = {}
    for key, config in all_configs.items():
        commands[key] = _handle_config_to_dict(config)
        schema[key] = _derive_defaults_schema(key)
    return JSONResponse(content={"commands": commands, "schema": schema})


async def _save_advanced_config(request: Request) -> JSONResponse:
    parsed = await _parse_advanced_updates(request)
    if isinstance(parsed, JSONResponse):
        return parsed
    key, updates = parsed
    manager = get_handle_config_manager()
    try:
        await manager.update_config(key, updates)
    except DatabaseError:
        return JSONResponse(status_code=500, content={"detail": "config_io_error"})
    except (ValueError, TypeError) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    config = await manager.get_config(key)
    return JSONResponse(
        content={"ok": True, "command": key, "config": _handle_config_to_dict(config)}
    )


async def _parse_advanced_updates(
    request: Request,
) -> tuple[str, dict[str, Any]] | JSONResponse:
    """解析并校验 PUT /config/advanced 请求体，返回 (key, updates) 或错误响应。"""
    payload: object
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "invalid_json"})
    if not isinstance(payload, dict):
        return JSONResponse(
            status_code=400, content={"detail": "request body must be an object"}
        )
    key = payload.get("key")
    updates = payload.get("updates")
    if not isinstance(key, str) or key not in HANDLE_DEFAULTS_REGISTRY:
        return JSONResponse(
            status_code=400,
            content={"detail": f"command_key not registered: {key}"},
        )
    if not isinstance(updates, dict):
        return JSONResponse(
            status_code=400, content={"detail": "updates must be an object"}
        )
    invalid = _validate_updates_shape(updates)
    if invalid is not None:
        return invalid
    return key, updates


def _validate_updates_shape(updates: dict[str, Any]) -> JSONResponse | None:
    """校验 updates 形状：enabled 必须布尔、defaults/policies 必须对象、无未知字段。"""
    for section, update in updates.items():
        if section in {"defaults", "policies"}:
            if not isinstance(update, dict):
                return JSONResponse(
                    status_code=400,
                    content={"detail": f"{section} must be an object"},
                )
        elif section == "enabled":
            if type(update) is not bool:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "enabled must be a boolean"},
                )
        else:
            return JSONResponse(
                status_code=400,
                content={"detail": f"unknown update field: {section}"},
            )
    return None
