from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import sys
from types import ModuleType
from unittest.mock import Mock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.backends import LiteLLMBackend
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    LiteLLMRouterConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import LLMProfile


def profile() -> LLMProfile:
    return LLMProfile(
        name="default",
        backend="litellm",
        model="openai/gpt-4o-mini",
    )


def test_disabled_router_does_not_import_sdk_or_construct_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constructor = Mock()
    module = ModuleType("litellm")
    module.__dict__["Router"] = constructor
    monkeypatch.setitem(sys.modules, "litellm", module)
    backend = LiteLLMBackend(profile(), LiteLLMRouterConfig({"enabled": False}))

    assert backend.router is None
    assert backend._sdk is None
    constructor.assert_not_called()


def test_enabled_router_receives_mutable_deep_copy_and_is_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    native_router = object()

    def construct(**config: object) -> object:
        captured.update(config)
        model_list = config["model_list"]
        assert isinstance(model_list, list)
        deployment = model_list[0]
        assert isinstance(deployment, dict)
        deployment["model_name"] = "sdk-mutated"
        return native_router

    module = ModuleType("litellm")
    module.__dict__["Router"] = construct
    monkeypatch.setitem(sys.modules, "litellm", module)
    source: dict[str, object] = {
        "enabled": True,
        "strategy": "least-busy",
        "num_retries": 2,
        "extensions": {
            "allowed_fails": 3,
            "model_list": [
                {
                    "model_name": "configured",
                    "litellm_params": {
                        "model": "openai/gpt-4o-mini",
                        "api_key": "",
                    },
                }
            ],
        },
    }
    config = LiteLLMRouterConfig(source)
    backend = LiteLLMBackend(profile(), config)

    assert backend.router is native_router
    assert backend.router is native_router
    assert captured["routing_strategy"] == "least-busy"
    assert captured["num_retries"] == 2
    assert captured["allowed_fails"] == 3
    assert "enabled" not in captured
    assert "strategy" not in captured
    assert "extensions" not in captured
    captured_model_list = captured["model_list"]
    assert isinstance(captured_model_list, list)
    captured_deployment = captured_model_list[0]
    assert isinstance(captured_deployment, dict)
    captured_params = captured_deployment["litellm_params"]
    assert isinstance(captured_params, dict)
    assert captured_params["api_key"] == "__lingchu_no_credential__"
    source_extensions = source["extensions"]
    assert isinstance(source_extensions, dict)
    source_model_list = source_extensions["model_list"]
    assert isinstance(source_model_list, list)
    source_deployment = source_model_list[0]
    assert isinstance(source_deployment, dict)
    assert source_deployment["model_name"] == "configured"
    frozen_extensions = config.values["extensions"]
    assert isinstance(frozen_extensions, Mapping)
    frozen_model_list = frozen_extensions["model_list"]
    assert isinstance(frozen_model_list, tuple)
    frozen_deployment = frozen_model_list[0]
    assert isinstance(frozen_deployment, Mapping)
    assert frozen_deployment["model_name"] == "configured"


@pytest.mark.parametrize(
    "forbidden",
    [
        "callbacks",
        "custom_logger",
        "failure_callback",
        "logger_fn",
        "loggers",
        "success_callback",
    ],
)
def test_router_rejects_callbacks_and_loggers_before_sdk_import(
    forbidden: str,
) -> None:
    backend = LiteLLMBackend(
        profile(),
        LiteLLMRouterConfig({"enabled": True, "extensions": {forbidden: ["unsafe"]}}),
    )

    with pytest.raises(ValueError, match="callbacks and loggers"):
        _ = backend.router
    assert backend._sdk is None


@pytest.mark.parametrize(
    "router_values",
    [
        {
            "enabled": True,
            "extensions": {
                "model_list": [
                    {
                        "litellm_params": {
                            "success_callback": ["unsafe"],
                        }
                    }
                ]
            },
        },
        {
            "enabled": True,
            "extensions": {
                "default_litellm_params": {"nested": {"failure_callback": ["unsafe"]}}
            },
        },
    ],
)
def test_router_recursively_rejects_control_plane_keys_before_sdk_import(
    router_values: dict[str, object],
) -> None:
    backend = LiteLLMBackend(profile(), LiteLLMRouterConfig(router_values))

    with pytest.raises(ValueError, match="callbacks and loggers"):
        _ = backend.router
    assert backend._sdk is None


@pytest.mark.parametrize("collision", ["num_retries", "timeout", "routing_strategy"])
def test_router_rejects_extension_collisions_deterministically(
    collision: str,
) -> None:
    backend = LiteLLMBackend(
        profile(),
        LiteLLMRouterConfig({
            "enabled": True,
            "strategy": "least-busy",
            "num_retries": 2,
            "timeout": 10,
            "extensions": {collision: "extension-value"},
        }),
    )

    with pytest.raises(ValueError, match="collides with managed option"):
        _ = backend.router
    assert backend._sdk is None


def test_router_construction_does_not_change_module_globals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    callbacks: list[object] = [{"name": "callback"}]
    success_callback: list[object] = [{"name": "success"}]
    failure_callback: list[object] = [{"name": "failure"}]
    module = ModuleType("litellm")
    module.__dict__["callbacks"] = callbacks
    module.__dict__["success_callback"] = success_callback
    module.__dict__["failure_callback"] = failure_callback
    module.__dict__["nested_runtime_state"] = {
        "callbacks": ["before"],
        "settings": {"enabled": True},
    }
    module.__dict__["Router"] = Mock(return_value=object())
    monkeypatch.setitem(sys.modules, "litellm", module)
    backend = LiteLLMBackend(
        profile(), LiteLLMRouterConfig({"enabled": True, "model_list": []})
    )

    content_snapshot = {
        name: deepcopy(module.__dict__[name])
        for name in (
            "callbacks",
            "success_callback",
            "failure_callback",
            "nested_runtime_state",
        )
    }
    identity_snapshot = {
        name: module.__dict__[name]
        for name in (
            "callbacks",
            "success_callback",
            "failure_callback",
            "nested_runtime_state",
        )
    }

    _ = backend.router

    assert module.__dict__["callbacks"] is callbacks
    assert module.__dict__["success_callback"] is success_callback
    assert module.__dict__["failure_callback"] is failure_callback
    for name, before in content_snapshot.items():
        assert module.__dict__[name] == before
        assert module.__dict__[name] is identity_snapshot[name]


@pytest.mark.asyncio
async def test_close_never_calls_router_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native_router = Mock()
    module = ModuleType("litellm")
    module.__dict__["Router"] = Mock(return_value=native_router)
    monkeypatch.setitem(sys.modules, "litellm", module)
    backend = LiteLLMBackend(
        profile(), LiteLLMRouterConfig({"enabled": True, "model_list": []})
    )
    assert backend.router is native_router

    await backend.close()
    await backend.close()

    native_router.reset.assert_not_called()
