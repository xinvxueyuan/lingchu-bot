from __future__ import annotations

from dataclasses import FrozenInstanceError
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


def test_profile_is_frozen_slotted() -> None:
    profile = LLMProfile(
        name="primary",
        backend="pydantic_ai",
        model="provider/model",
    )

    assert not hasattr(profile, "__dict__")
    attribute = "model"
    with pytest.raises(FrozenInstanceError):
        setattr(profile, attribute, "other")


def test_profile_repr_does_not_expose_api_keys_or_nested_secrets() -> None:
    profile = LLMProfile(
        name="primary",
        backend="pydantic_ai",
        model="gpt-test",
        base_url="https://synthetic-host.invalid/path",
        api_key="sk-profile-secret",
    )

    rendered = repr(profile)

    assert "api_key" not in rendered
    assert "sk-profile-secret" not in rendered
    assert "synthetic-host" not in rendered


def test_usage_response_and_event_are_frozen_slotted_value_objects() -> None:
    usage = LLMUsage(input_tokens=3, output_tokens=5, total_tokens=8, cost=0.25)
    response = LLMResponse(
        text="done",
        output=({"type": "message"},),
        usage=usage,
        request_id="req-1",
        model="gpt-test",
        backend="pydantic_ai",
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
        backend="pydantic_ai",
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
        backend="pydantic_ai",
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


def test_profile_defaults_use_documented_optional_values() -> None:
    profile = LLMProfile(name="minimal", backend="pydantic_ai", model="gpt-test")

    assert profile.base_url is None
    assert profile.api_key is None
    assert profile.timeout == 60.0
    assert profile.max_retries == 2


def test_response_repr_reports_usage_present_and_tuple_length() -> None:
    usage = LLMUsage(input_tokens=1, output_tokens=2, total_tokens=3)
    response = LLMResponse(
        text="done",
        output=(1, 2, 3),
        usage=usage,
        request_id="req-1",
        model="gpt-test",
        backend="pydantic_ai",
        raw={"native": True},
    )

    rendered = repr(response)

    assert "usage=present" in rendered
    assert "output=<tuple:3>" in rendered
    assert 'backend="pydantic_ai"' in rendered


def test_response_repr_reports_none_usage_and_request_id() -> None:
    response = LLMResponse(
        text=None,
        output=(),
        usage=None,
        request_id=None,
        model=None,
        backend="pydantic_ai",
        raw=None,
    )

    rendered = repr(response)

    assert "usage=none" in rendered
    assert "request_id=null" in rendered
    assert "model=null" in rendered
    assert "raw=<NoneType>" in rendered


def test_event_repr_reports_native_data_and_raw_type_names() -> None:
    event = LLMEvent(type="text_delta", data="hello", raw={"event": "done"})

    rendered = repr(event)

    assert 'type="text_delta"' in rendered
    assert "data=<str>" in rendered
    assert "raw=<dict>" in rendered


def test_profile_repr_redacts_all_sensitive_configured_fields() -> None:
    profile = LLMProfile(
        name="primary",
        backend="pydantic_ai",
        model="provider/model",
        base_url="https://synthetic-host.invalid/path",
        api_key="sk-profile-secret",
        timeout=120.0,
        max_retries=5,
    )

    rendered = repr(profile)

    assert "LLMProfile(" in rendered
    assert '"timeout":120.0' in rendered
    assert '"max_retries":5' in rendered
    assert '"backend":"pydantic_ai"' in rendered
    assert "sk-profile-secret" not in rendered
    assert "synthetic-host" not in rendered


def test_safe_length_returns_none_for_non_sized_object() -> None:
    from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import (
        _safe_length,
    )

    assert _safe_length(object()) is None


def test_safe_length_returns_length_for_sized_object() -> None:
    from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import (
        _safe_length,
    )

    assert _safe_length([1, 2, 3]) == 3
    assert _safe_length("hello") == 5
    assert _safe_length(()) == 0
