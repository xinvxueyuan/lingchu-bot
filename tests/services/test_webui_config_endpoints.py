"""Tests for WebUI config read/write endpoints.

覆盖 ``services/webui/config_endpoints.py``：读取成功、保存成功落盘、
非法输入 400 且不落盘、未注册 key 400、底层 TOML 异常收敛为 500。
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from _lingchu_bot_contracts import MutableRuntimeSettings
import pytest
from starlette.requests import Request

from src.plugins.nonebot_plugin_lingchu_bot.core.handle_config_manager import (
    HandleConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.mutable_settings import (
    MutableSettingsError,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.toml_store import DatabaseError
from src.plugins.nonebot_plugin_lingchu_bot.services.webui import (
    config_endpoints as endpoints,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.webui.config_endpoints import (
    WEBUI_CONFIG_ADVANCED_PATH,
    WEBUI_CONFIG_BASIC_PATH,
    webui_config_advanced_endpoint,
    webui_config_basic_endpoint,
)


def _request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    raw_body: bytes | None = None,
) -> Request:
    """构造一个携带可选 JSON body 的 Starlette 请求。"""
    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    if raw_body is not None:
        body_bytes = raw_body
    elif body is not None:
        body_bytes = json.dumps(body).encode("utf-8")
    else:
        body_bytes = b""

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body_bytes, "more_body": False}

    return Request(scope, receive)


@pytest.fixture(autouse=True)
def _bypass_webui_password(monkeypatch: pytest.MonkeyPatch) -> None:
    """默认模拟已登录状态；鉴权 401 链路由 test_config_endpoints_require_password 单独验证。

    测试环境会加载仓库根目录 .env 中的 LINGCHU_WEBUI_PASSWORD，若直接透传真实
    密码到 verify_webui_password 会耦合本地 .env 内容；端点测试聚焦「已登录转发」
    场景，鉴权函数本身的行为不属于本模块范围。
    """
    monkeypatch.setattr(endpoints, "verify_webui_password", lambda _request: True)


def _fake_manager(
    configs: dict[str, HandleConfig],
    *,
    update_side_effect: Any = None,
    get_all_side_effect: Any = None,
    get_config_side_effect: Any = None,
) -> MagicMock:
    """构造一个可注入的 HandleConfigManager 替身。"""
    manager = MagicMock()
    manager.get_all_configs = AsyncMock(
        return_value=dict(configs), side_effect=get_all_side_effect
    )
    manager.get_config = AsyncMock(
        side_effect=(
            get_config_side_effect
            if get_config_side_effect is not None
            else (lambda key: configs[key])
        )
    )
    manager.update_config = AsyncMock(side_effect=update_side_effect)
    return manager


# --- 基本配置（GET /config/basic） ---


@pytest.mark.asyncio
async def test_get_basic_config_returns_values_and_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = MutableRuntimeSettings(
        permission_platform_runtime_passthrough={"qq": False},
        command_trigger_overrides={"menu": {"english": "help"}},
    )
    monkeypatch.setattr(endpoints, "load_mutable_settings", AsyncMock(return_value=expected))

    response = await webui_config_basic_endpoint(
        _request("GET", WEBUI_CONFIG_BASIC_PATH)
    )

    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["values"] == expected.to_dict()
    assert body["schema"] == [
        {"key": "permission_platform_runtime_passthrough", "type": "boolean_or_map"},
        {"key": "command_trigger_overrides", "type": "map"},
        {"key": "menu_page_trigger_overrides", "type": "map"},
    ]


@pytest.mark.asyncio
async def test_get_basic_config_maps_read_errors_to_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        endpoints,
        "load_mutable_settings",
        AsyncMock(side_effect=MutableSettingsError("read broken")),
    )

    response = await webui_config_basic_endpoint(
        _request("GET", WEBUI_CONFIG_BASIC_PATH)
    )

    assert response.status_code == 500
    assert json.loads(response.body) == {"detail": "config_io_error"}


# --- 基本配置（PUT /config/basic） ---


@pytest.mark.asyncio
async def test_put_basic_config_saves_and_flushes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save = AsyncMock()
    monkeypatch.setattr(endpoints, "save_mutable_settings", save)

    response = await webui_config_basic_endpoint(
        _request(
            "PUT",
            WEBUI_CONFIG_BASIC_PATH,
            {"settings": {"permission_platform_runtime_passthrough": {"qq": True}}},
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body) == {"ok": True}
    save.assert_awaited_once()
    saved = save.await_args.args[0]
    assert saved.permission_platform_runtime_passthrough == {"qq": True}
    assert save.await_args.kwargs == {"flush": True}


@pytest.mark.asyncio
async def test_put_basic_config_rejects_unknown_field_without_saving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save = AsyncMock()
    monkeypatch.setattr(endpoints, "save_mutable_settings", save)

    response = await webui_config_basic_endpoint(
        _request("PUT", WEBUI_CONFIG_BASIC_PATH, {"settings": {"bogus": 1}})
    )

    assert response.status_code == 400
    assert "unknown configuration fields" in json.loads(response.body)["detail"]
    save.assert_not_awaited()


@pytest.mark.asyncio
async def test_put_basic_config_rejects_bad_type_without_saving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save = AsyncMock()
    monkeypatch.setattr(endpoints, "save_mutable_settings", save)

    response = await webui_config_basic_endpoint(
        _request(
            "PUT",
            WEBUI_CONFIG_BASIC_PATH,
            {"settings": {"permission_platform_runtime_passthrough": "yes"}},
        )
    )

    assert response.status_code == 400
    assert "must be bool or mapping" in json.loads(response.body)["detail"]
    save.assert_not_awaited()


@pytest.mark.asyncio
async def test_put_basic_config_rejects_non_object_body_without_saving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save = AsyncMock()
    monkeypatch.setattr(endpoints, "save_mutable_settings", save)

    response = await webui_config_basic_endpoint(
        _request("PUT", WEBUI_CONFIG_BASIC_PATH, {"settings": "nope"})
    )

    assert response.status_code == 400
    assert json.loads(response.body)["detail"] == "settings must be an object"
    save.assert_not_awaited()


@pytest.mark.asyncio
async def test_put_basic_config_rejects_invalid_json_without_saving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    save = AsyncMock()
    monkeypatch.setattr(endpoints, "save_mutable_settings", save)

    request = _request(
        "PUT", WEBUI_CONFIG_BASIC_PATH, raw_body=b"{not json"
    )

    response = await webui_config_basic_endpoint(request)

    assert response.status_code == 400
    assert json.loads(response.body)["detail"] == "invalid_json"
    save.assert_not_awaited()


@pytest.mark.asyncio
async def test_put_basic_config_maps_write_errors_to_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        endpoints,
        "save_mutable_settings",
        AsyncMock(side_effect=MutableSettingsError("write broken")),
    )

    response = await webui_config_basic_endpoint(
        _request("PUT", WEBUI_CONFIG_BASIC_PATH, {"settings": {}})
    )

    assert response.status_code == 500
    assert json.loads(response.body) == {"detail": "config_io_error"}


# --- 高级配置（GET /config/advanced） ---


@pytest.mark.asyncio
async def test_get_advanced_config_returns_commands_and_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configs = {
        "kick_member": HandleConfig(
            enabled=True,
            defaults={
                "require_reason": False,
                "default_reason": "管理员操作",
                "audit_level": "medium",
            },
            policies={},
        ),
        "protect_member": HandleConfig(
            enabled=True,
            defaults={"whitelist_scope": "group", "default_reason": "管理员操作"},
            policies={},
        ),
        "block_member": HandleConfig(
            enabled=False,
            defaults={"block_duration": None, "default_reason": "违反群规"},
            policies={"role": "admin"},
        ),
        "member_mute": HandleConfig(
            enabled=True,
            defaults={"mute_duration": 300, "default_reason": "管理员操作"},
            policies={},
        ),
    }
    manager = _fake_manager(configs)
    monkeypatch.setattr(endpoints, "get_handle_config_manager", lambda: manager)

    response = await webui_config_advanced_endpoint(
        _request("GET", WEBUI_CONFIG_ADVANCED_PATH)
    )

    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["commands"]["kick_member"] == {
        "enabled": True,
        "defaults": {
            "require_reason": False,
            "default_reason": "管理员操作",
            "audit_level": "medium",
        },
        "policies": {},
    }
    assert body["commands"]["block_member"]["enabled"] is False
    assert body["commands"]["block_member"]["policies"] == {"role": "admin"}
    defaults_schema = body["schema"]
    assert defaults_schema["kick_member"] == [
        {"key": "require_reason", "type": "boolean"},
        {"key": "default_reason", "type": "string"},
        {"key": "audit_level", "type": "enum", "options": ["low", "medium", "high"]},
    ]
    assert defaults_schema["protect_member"] == [
        {"key": "whitelist_scope", "type": "enum", "options": ["group", "global"]},
        {"key": "default_reason", "type": "string"},
    ]
    assert defaults_schema["block_member"] == [
        {"key": "block_duration", "type": "optional_integer"},
        {"key": "default_reason", "type": "string"},
    ]
    assert defaults_schema["member_mute"] == [
        {"key": "mute_duration", "type": "integer"},
        {"key": "default_reason", "type": "string"},
    ]


@pytest.mark.asyncio
async def test_get_advanced_config_maps_errors_to_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _fake_manager({}, get_all_side_effect=DatabaseError("read broken"))
    monkeypatch.setattr(endpoints, "get_handle_config_manager", lambda: manager)

    response = await webui_config_advanced_endpoint(
        _request("GET", WEBUI_CONFIG_ADVANCED_PATH)
    )

    assert response.status_code == 500
    assert json.loads(response.body) == {"detail": "config_io_error"}


# --- 高级配置（PUT /config/advanced） ---


@pytest.mark.asyncio
async def test_put_advanced_config_updates_and_returns_updated_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configs = {
        "kick_member": HandleConfig(
            enabled=True,
            defaults={
                "require_reason": False,
                "default_reason": "管理员操作",
                "audit_level": "low",
            },
            policies={},
        )
    }

    def fake_update(key: str, updates: dict[str, Any]) -> None:
        current = configs[key]
        defaults = dict(current.defaults)
        defaults.update(updates.get("defaults", {}))
        configs[key] = HandleConfig(
            enabled=updates.get("enabled", current.enabled),
            defaults=defaults,
            policies=updates.get("policies", current.policies),
        )

    manager = _fake_manager(configs, update_side_effect=fake_update)
    monkeypatch.setattr(endpoints, "get_handle_config_manager", lambda: manager)

    response = await webui_config_advanced_endpoint(
        _request(
            "PUT",
            WEBUI_CONFIG_ADVANCED_PATH,
            {
                "key": "kick_member",
                "updates": {"enabled": False, "defaults": {"audit_level": "high"}},
            },
        )
    )

    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["ok"] is True
    assert body["command"] == "kick_member"
    assert body["config"] == {
        "enabled": False,
        "defaults": {
            "require_reason": False,
            "default_reason": "管理员操作",
            "audit_level": "high",
        },
        "policies": {},
    }
    manager.update_config.assert_awaited_once_with(
        "kick_member", {"enabled": False, "defaults": {"audit_level": "high"}}
    )


@pytest.mark.asyncio
async def test_put_advanced_config_rejects_unregistered_key_without_saving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _fake_manager({})
    monkeypatch.setattr(endpoints, "get_handle_config_manager", lambda: manager)

    response = await webui_config_advanced_endpoint(
        _request(
            "PUT",
            WEBUI_CONFIG_ADVANCED_PATH,
            {"key": "not_a_command", "updates": {"enabled": True}},
        )
    )

    assert response.status_code == 400
    assert "command_key not registered: not_a_command" in json.loads(
        response.body
    )["detail"]
    manager.update_config.assert_not_awaited()


@pytest.mark.asyncio
async def test_put_advanced_config_rejects_bad_updates_shape_without_saving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _fake_manager({})
    monkeypatch.setattr(endpoints, "get_handle_config_manager", lambda: manager)

    cases = [
        {"key": "kick_member", "updates": "nope"},
        {"key": "kick_member", "updates": {"enabled": "yes"}},
        {"key": "kick_member", "updates": {"defaults": "nope"}},
    ]
    for payload in cases:
        response = await webui_config_advanced_endpoint(
            _request("PUT", WEBUI_CONFIG_ADVANCED_PATH, payload)
        )
        assert response.status_code == 400
    manager.update_config.assert_not_awaited()


@pytest.mark.asyncio
async def test_put_advanced_config_rejects_unknown_update_field_without_saving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _fake_manager({})
    monkeypatch.setattr(endpoints, "get_handle_config_manager", lambda: manager)

    response = await webui_config_advanced_endpoint(
        _request(
            "PUT",
            WEBUI_CONFIG_ADVANCED_PATH,
            {"key": "kick_member", "updates": {"bogus": 1}},
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body)["detail"] == "unknown update field: bogus"
    manager.update_config.assert_not_awaited()


@pytest.mark.asyncio
async def test_put_advanced_config_maps_io_errors_to_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _fake_manager({}, update_side_effect=DatabaseError("disk broken"))
    monkeypatch.setattr(endpoints, "get_handle_config_manager", lambda: manager)

    response = await webui_config_advanced_endpoint(
        _request(
            "PUT",
            WEBUI_CONFIG_ADVANCED_PATH,
            {"key": "kick_member", "updates": {"enabled": False}},
        )
    )

    assert response.status_code == 500
    assert json.loads(response.body) == {"detail": "config_io_error"}


@pytest.mark.asyncio
async def test_put_advanced_config_maps_validation_errors_to_400(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _fake_manager(
        {}, update_side_effect=ValueError("enabled must be a boolean")
    )
    monkeypatch.setattr(endpoints, "get_handle_config_manager", lambda: manager)

    response = await webui_config_advanced_endpoint(
        _request(
            "PUT",
            WEBUI_CONFIG_ADVANCED_PATH,
            {"key": "kick_member", "updates": {"enabled": False}},
        )
    )

    assert response.status_code == 400
    assert json.loads(response.body)["detail"] == "enabled must be a boolean"


# --- 鉴权 ---


@pytest.mark.asyncio
async def test_config_endpoints_require_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(endpoints, "verify_webui_password", lambda _request: False)

    basic = await webui_config_basic_endpoint(
        _request("GET", WEBUI_CONFIG_BASIC_PATH)
    )
    advanced = await webui_config_advanced_endpoint(
        _request("GET", WEBUI_CONFIG_ADVANCED_PATH)
    )

    assert basic.status_code == 401
    assert json.loads(basic.body) == {"detail": "unauthorized"}
    assert advanced.status_code == 401
    assert json.loads(advanced.body) == {"detail": "unauthorized"}
