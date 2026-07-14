from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import MappingProxyType
from typing import Any, cast, override

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import (
    LLMEvent,
    LLMProfile,
    LLMResponse,
    LLMUsage,
)


class HostileRepr:
    @override
    def __repr__(self) -> str:
        raise AssertionError


class HostileLength:
    def __len__(self) -> int:
        raise AssertionError


def _raise_hostile_name(_cls: object) -> str:
    raise AssertionError


HostileNameMeta = cast(
    "type",
    type("HostileNameMeta", (type,), {"__name__": property(_raise_hostile_name)}),
)
HostileType = HostileNameMeta("HostileType", (), {})


def test_profile_is_frozen_slotted_and_deeply_freezes_mappings() -> None:
    headers = {"X-Trace": "enabled"}
    query = {"filters": [{"kind": "safe"}]}
    options = {"nested": {"items": [1, 2]}}

    profile = LLMProfile(
        name="primary",
        backend="litellm",
        model="provider/model",
        default_headers=headers,
        default_query=query,
        provider_options=options,
    )
    headers["X-Trace"] = "changed"
    query["filters"][0]["kind"] = "changed"
    options["nested"]["items"].append(3)

    assert not hasattr(profile, "__dict__")
    assert isinstance(profile.default_headers, MappingProxyType)
    assert profile.default_headers["X-Trace"] == "enabled"
    assert profile.default_query["filters"] == (MappingProxyType({"kind": "safe"}),)
    assert profile.provider_options["nested"]["items"] == (1, 2)
    attribute = "model"
    with pytest.raises(FrozenInstanceError):
        setattr(profile, attribute, "other")


def test_profile_repr_does_not_expose_api_keys_or_nested_secrets() -> None:
    profile = LLMProfile(
        name="primary",
        backend="openai",
        model="gpt-test",
        base_url="https://synthetic-host.invalid/path",
        api_key="sk-profile-secret",
        organization="synthetic-organization",
        project="synthetic-project",
        default_headers={"Authorization": "Bearer header-secret"},
        default_query={"safe": "synthetic-query-value"},
        provider_options={"nested": {"password": "provider-secret"}},
    )

    rendered = repr(profile)

    assert "api_key" not in rendered
    assert "sk-profile-secret" not in rendered
    assert "header-secret" not in rendered
    assert "provider-secret" not in rendered
    assert "synthetic-host" not in rendered
    assert "synthetic-organization" not in rendered
    assert "synthetic-project" not in rendered
    assert "synthetic-query-value" not in rendered


def test_profile_rejects_values_that_cannot_be_deeply_frozen() -> None:
    unsupported_values: tuple[object, ...] = (
        bytearray(b"synthetic"),
        {"unsupported"},
        type("MutableListSubclass", (list,), {})(["synthetic"]),
    )

    for value in unsupported_values:
        with pytest.raises(TypeError, match=r"^unsupported LLM configuration value$"):
            LLMProfile(
                name="invalid",
                backend="openai",
                model="gpt-test",
                provider_options=cast("Any", {"value": value}),
            )


def test_usage_response_and_event_are_frozen_slotted_value_objects() -> None:
    usage = LLMUsage(input_tokens=3, output_tokens=5, total_tokens=8, cost=0.25)
    response = LLMResponse(
        text="done",
        output=({"type": "message"},),
        usage=usage,
        request_id="req-1",
        model="gpt-test",
        backend="openai",
        raw={"native": True},
    )
    event = LLMEvent(type="completed", data=response, raw={"event": "done"})

    assert not hasattr(usage, "__dict__")
    assert not hasattr(response, "__dict__")
    assert not hasattr(event, "__dict__")
    assert response.output == ({"type": "message"},)
    assert event.data is response
    attribute = "cost"
    with pytest.raises(FrozenInstanceError):
        setattr(usage, attribute, 1.0)


def test_response_and_event_repr_do_not_call_provider_repr() -> None:
    response = LLMResponse(
        text="done",
        output=(HostileRepr(),),
        usage=None,
        request_id="req-1",
        model="gpt-test",
        backend="openai",
        raw=HostileRepr(),
    )
    event = LLMEvent(type="native", data=HostileRepr(), raw=HostileRepr())
    response_repr = repr(response)
    event_repr = repr(event)
    assert "HostileRepr" in response_repr
    assert "HostileRepr" in event_repr


def test_response_repr_handles_hostile_output_length() -> None:
    response = LLMResponse(
        text="done",
        output=cast("Any", HostileLength()),
        usage=None,
        request_id="req-1",
        model="gpt-test",
        backend="openai",
        raw=None,
    )

    rendered = repr(response)

    assert rendered.startswith("LLMResponse(")
    assert "output=<tuple:unavailable>" in rendered


def test_event_repr_handles_hostile_metaclass_names() -> None:
    event = LLMEvent(type="native", data=HostileType(), raw=HostileType())

    rendered = repr(event)

    assert rendered.startswith("LLMEvent(")
    assert rendered.count("<object>") == 2
