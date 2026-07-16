from __future__ import annotations

from collections.abc import Iterator
from types import MappingProxyType
from typing import Any, cast, override
from unittest.mock import Mock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm import (
    security as security_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.security import (
    MAX_COLLECTION_ITEMS,
    MAX_NESTING_DEPTH,
    MAX_TEXT_LENGTH,
    contains_control_plane_key,
    contains_sensitive_mapping_entry,
    freeze_value,
    redact_value,
    safe_repr,
    safe_type_name,
    sanitize_message,
    thaw_value,
)


class HostileReprCalledError(AssertionError):
    pass


class HostileRepr:
    @override
    def __repr__(self) -> str:
        raise HostileReprCalledError


class HostileMapping(dict[str, object]):
    @override
    def items(self) -> Any:
        raise AssertionError


class HostileLenMapping(dict[str, object]):
    @override
    def __len__(self) -> int:
        raise RuntimeError from None


class HostileList(list[object]):
    @override
    def __iter__(self) -> Iterator[object]:
        raise AssertionError


def test_freeze_and_thaw_recursively_copy_supported_containers() -> None:
    items: list[object] = [1, {"enabled": True}]
    original: dict[str, object] = {
        "mapping": {"items": items},
        "tuple": ("a", "b"),
    }

    frozen = freeze_value(original)
    items.append(3)

    assert isinstance(frozen, MappingProxyType)
    typed_frozen = cast("MappingProxyType[str, object]", frozen)
    frozen_mapping = cast("MappingProxyType[str, object]", typed_frozen["mapping"])
    assert frozen_mapping["items"] == (1, MappingProxyType({"enabled": True}))
    assert typed_frozen["tuple"] == ("a", "b")
    assert thaw_value(typed_frozen) == {
        "mapping": {"items": [1, {"enabled": True}]},
        "tuple": ["a", "b"],
    }


def test_freeze_and_thaw_reject_values_outside_json_like_domain() -> None:
    invalid_values: tuple[object, ...] = (
        {"set"},
        frozenset({"set"}),
        bytearray(b"mutable"),
        {("tuple",): "key"},
        HostileMapping(synthetic="value"),
        MappingProxyType(HostileLenMapping(synthetic="value")),
        HostileList(["value"]),
        HostileRepr(),
    )

    for value in invalid_values:
        with pytest.raises(TypeError, match=r"^unsupported LLM configuration value$"):
            freeze_value(value)
        with pytest.raises(TypeError, match=r"^unsupported LLM configuration value$"):
            thaw_value(value)


def test_bounded_helpers_terminate_on_cycles_depth_and_collection_size() -> None:
    cyclic: dict[str, object] = {}
    cyclic["self"] = cyclic
    deep: object = "leaf"
    for _ in range(MAX_NESTING_DEPTH + 3):
        deep = [deep]
    oversized = list(range(MAX_COLLECTION_ITEMS + 5))

    cyclic_redacted = cast("dict[str, object]", redact_value(cyclic))
    deep_redacted = redact_value(deep)
    oversized_redacted = cast("list[object]", redact_value(oversized))

    assert cyclic_redacted["self"] == "<cycle>"
    assert "<max-depth>" in safe_repr(deep_redacted)
    assert len(oversized_redacted) == MAX_COLLECTION_ITEMS + 1
    assert oversized_redacted[-1] == "<truncated>"


def test_redaction_covers_secret_key_patterns_and_nested_provider_data() -> None:
    secret_keys = (
        "access_token",
        "api-key",
        "Authorization",
        "client_secret",
        "credential",
        "session_cookie",
        "password",
        "default_headers",
        "default_query",
    )
    payload = {
        "provider": {key: f"secret-{index}" for index, key in enumerate(secret_keys)},
        "safe": "visible",
    }

    redacted = cast("dict[str, object]", redact_value(payload))

    assert redacted["safe"] == "visible"
    provider = cast("dict[str, object]", redacted["provider"])
    assert set(provider.values()) == {"<redacted>"}
    rendered = safe_repr(payload)
    assert "secret-" not in rendered
    assert "visible" in rendered


def test_redaction_handles_exceptions_controls_and_malicious_repr() -> None:
    value = {
        "error": RuntimeError("provider\r\nforged", {"api_key": "exception-secret"}),
        "hostile": HostileRepr(),
        "text": "line1\nline2\x00end",
    }

    redacted = cast("dict[str, object]", redact_value(value))
    rendered = safe_repr(value)

    error = cast("dict[str, object]", redacted["error"])
    arguments = cast("list[object]", error["args"])
    secret = cast("dict[str, object]", arguments[1])
    assert error["type"] == "RuntimeError"
    assert secret["api_key"] == "<redacted>"
    assert redacted["hostile"] == "<HostileRepr>"
    text = cast("str", redacted["text"])
    assert "\n" not in text
    assert "\x00" not in text
    assert "exception-secret" not in rendered


def test_redaction_is_total_for_hostile_containers_non_string_keys_and_huge_data() -> (
    None
):
    huge_integer = 1 << (MAX_TEXT_LENGTH * 8)
    value = {
        b"api_key": "synthetic-non-string-key-secret",
        "mapping": HostileMapping(api_key="synthetic-hostile-mapping-secret"),
        "list": HostileList(["synthetic-hostile-list-secret"]),
        "huge_integer": huge_integer,
        "huge_text": "x" * (MAX_TEXT_LENGTH * 2),
    }

    rendered = safe_repr(value)

    assert "synthetic-non-string-key-secret" not in rendered
    assert "synthetic-hostile-mapping-secret" not in rendered
    assert "synthetic-hostile-list-secret" not in rendered
    assert "<large-int>" in rendered
    assert len(rendered) < MAX_TEXT_LENGTH * 2


def test_sanitize_message_redacts_assignments_urls_and_unicode_controls() -> None:
    message = (
        "authorization: synthetic-auth; auth=synthetic-short-auth "
        "api-key=synthetic-key x-api-key: synthetic-x-key "
        "token=synthetic-token secret=synthetic-secret "
        "credential=synthetic-credential cookie=synthetic-cookie "
        "password=synthetic-password Basic synthetic-basic "
        + "https://example.invalid/path?safe=yes&api_key=synthetic-query"
        + "\u2028forged\u2029\u202econtrol"
        + "z" * (MAX_TEXT_LENGTH * 2)
    )

    sanitized = sanitize_message(message)

    for secret in (
        "synthetic-auth",
        "synthetic-short-auth",
        "synthetic-key",
        "synthetic-x-key",
        "synthetic-token",
        "synthetic-secret",
        "synthetic-credential",
        "synthetic-cookie",
        "synthetic-password",
        "synthetic-basic",
        "synthetic-query",
    ):
        assert secret not in sanitized
    assert "\u2028" not in sanitized
    assert "\u2029" not in sanitized
    assert "\u202e" not in sanitized
    assert len(sanitized) <= MAX_TEXT_LENGTH


class _TypeErrorLenMapping(dict[str, object]):
    @override
    def __len__(self) -> int:
        raise TypeError("len access hostile")


class _HostileArgsException(BaseException):
    def __init__(self) -> None:
        pass

    @override
    def __getattribute__(self, name: str) -> object:
        if name == "args":
            raise AssertionError("args access hostile")
        return super().__getattribute__(name)


def _raise_hostile_type_name(_cls: object) -> str:
    raise AssertionError


HostileTypeNameMeta = cast(
    "type",
    type(
        "HostileTypeNameMeta",
        (type,),
        {"__name__": property(_raise_hostile_type_name)},
    ),
)
HostileTypeNameValue = HostileTypeNameMeta("HostileTypeNameValue", (), {})


def test_sanitize_message_returns_redacted_for_non_str_input() -> None:
    assert sanitize_message(cast("Any", 123)) == "<redacted>"
    assert sanitize_message(cast("Any", None)) == "<redacted>"
    assert sanitize_message(cast("Any", 3.14)) == "<redacted>"


def test_contains_control_plane_key_detects_dict_and_nested_entries() -> None:
    assert contains_control_plane_key({"api_key": "secret"}) is True
    assert contains_control_plane_key({"nested": {"token": "value"}}) is True
    assert contains_control_plane_key(MappingProxyType({"base_url": "x"})) is True
    assert contains_control_plane_key({"visible": "value"}) is False
    assert contains_control_plane_key({123: "non-string-key"}) is False


def test_contains_control_plane_key_detects_list_and_tuple_entries() -> None:
    assert contains_control_plane_key([{"api_key": "secret"}]) is True
    assert contains_control_plane_key(({"token": "x"}, "safe")) is True
    assert contains_control_plane_key(["api_key", "visible"]) is False
    assert contains_control_plane_key(("safe", "value")) is False


def test_contains_control_plane_key_returns_false_for_scalars() -> None:
    assert contains_control_plane_key(123) is False
    assert contains_control_plane_key("string") is False
    assert contains_control_plane_key(None) is False
    assert contains_control_plane_key(3.14) is False
    scalar_true: bool = True
    assert contains_control_plane_key(scalar_true) is False


def test_contains_sensitive_mapping_entry_detects_secret_keys_and_auth_values() -> None:
    assert contains_sensitive_mapping_entry({"api_key": "x"}) is True
    assert contains_sensitive_mapping_entry({"Authorization": "Bearer abc"}) is True
    assert contains_sensitive_mapping_entry({"auth": "Basic xyz"}) is True
    assert contains_sensitive_mapping_entry(MappingProxyType({"token": "x"})) is True
    assert contains_sensitive_mapping_entry({"visible": "value"}) is False
    assert contains_sensitive_mapping_entry({123: "non-string-key"}) is False


def test_contains_sensitive_mapping_entry_detects_nested_and_list_entries() -> None:
    assert contains_sensitive_mapping_entry([{"token": "x"}]) is True
    assert contains_sensitive_mapping_entry(({"password": "x"},)) is True
    assert contains_sensitive_mapping_entry(["safe", "value"]) is False
    assert contains_sensitive_mapping_entry({"nested": {"secret": "x"}}) is True


def test_contains_sensitive_mapping_entry_returns_false_for_scalars() -> None:
    assert contains_sensitive_mapping_entry(123) is False
    assert contains_sensitive_mapping_entry("string") is False
    assert contains_sensitive_mapping_entry(None) is False


def test_safe_type_name_returns_object_when_name_access_fails() -> None:
    assert safe_type_name(HostileTypeNameValue()) == "object"


def test_freeze_rejects_values_exceeding_max_nesting_depth() -> None:
    deep: object = "leaf"
    for _ in range(MAX_NESTING_DEPTH + 3):
        deep = [deep]
    with pytest.raises(TypeError, match=r"^unsupported LLM configuration value$"):
        freeze_value(deep)


def test_freeze_mapping_rejects_cycles_and_oversized_collections() -> None:
    cyclic: dict[str, object] = {}
    cyclic["self"] = cyclic
    with pytest.raises(TypeError, match=r"^unsupported LLM configuration value$"):
        freeze_value(cyclic)
    oversized = {f"key_{i}": i for i in range(MAX_COLLECTION_ITEMS + 5)}
    with pytest.raises(TypeError, match=r"^unsupported LLM configuration value$"):
        freeze_value(oversized)


def test_freeze_sequence_rejects_cycles_and_oversized_collections() -> None:
    cyclic: list[object] = []
    cyclic.append(cyclic)
    with pytest.raises(TypeError, match=r"^unsupported LLM configuration value$"):
        freeze_value(cyclic)
    oversized = list(range(MAX_COLLECTION_ITEMS + 5))
    with pytest.raises(TypeError, match=r"^unsupported LLM configuration value$"):
        freeze_value(oversized)


def test_freeze_wraps_non_unsupported_type_error() -> None:
    hostile = MappingProxyType(_TypeErrorLenMapping(synthetic="value"))
    with pytest.raises(TypeError, match=r"^unsupported LLM configuration value$"):
        freeze_value(hostile)


def test_thaw_rejects_values_exceeding_max_nesting_depth() -> None:
    deep: object = "leaf"
    for _ in range(MAX_NESTING_DEPTH + 3):
        deep = [deep]
    with pytest.raises(TypeError, match=r"^unsupported LLM configuration value$"):
        thaw_value(deep)


def test_thaw_mapping_rejects_cycles_and_oversized_collections() -> None:
    cyclic: dict[str, object] = {}
    cyclic["self"] = cyclic
    with pytest.raises(TypeError, match=r"^unsupported LLM configuration value$"):
        thaw_value(cyclic)
    oversized = {f"key_{i}": i for i in range(MAX_COLLECTION_ITEMS + 5)}
    with pytest.raises(TypeError, match=r"^unsupported LLM configuration value$"):
        thaw_value(oversized)


def test_thaw_sequence_rejects_cycles_and_oversized_collections() -> None:
    cyclic: list[object] = []
    cyclic.append(cyclic)
    with pytest.raises(TypeError, match=r"^unsupported LLM configuration value$"):
        thaw_value(cyclic)
    oversized = list(range(MAX_COLLECTION_ITEMS + 5))
    with pytest.raises(TypeError, match=r"^unsupported LLM configuration value$"):
        thaw_value(oversized)


def test_thaw_wraps_non_unsupported_type_error() -> None:
    hostile = MappingProxyType(_TypeErrorLenMapping(synthetic="value"))
    with pytest.raises(TypeError, match=r"^unsupported LLM configuration value$"):
        thaw_value(hostile)


def test_redact_value_returns_unavailable_for_hostile_mapping() -> None:
    hostile = MappingProxyType(HostileMapping(api_key="secret"))
    assert redact_value(hostile) == "<unavailable>"


def test_redact_value_handles_bytes_and_non_finite_floats() -> None:
    assert redact_value(b"hello") == "<bytes:5>"
    assert redact_value(float("inf")) == "<non-finite-float>"
    assert redact_value(float("-inf")) == "<non-finite-float>"
    assert redact_value(float("nan")) == "<non-finite-float>"
    assert redact_value(3.14) == 3.14


def test_redact_value_handles_cyclic_exception() -> None:
    exc = RuntimeError("cyclic")
    exc.args = (exc,)
    redacted = cast("dict[str, object]", redact_value(exc))
    assert redacted["type"] == "RuntimeError"
    args = cast("list[object]", redacted["args"])
    assert args == ["<cycle>"]


def test_redact_value_handles_exception_with_hostile_args() -> None:
    exc = _HostileArgsException()
    redacted = cast("dict[str, object]", redact_value(exc))
    assert redacted["type"] == "_HostileArgsException"
    assert redacted["args"] == "<unavailable>"


def test_redact_value_truncates_oversized_mapping() -> None:
    oversized = {f"key_{i}": i for i in range(MAX_COLLECTION_ITEMS + 5)}
    redacted = cast("dict[str, object]", redact_value(oversized))
    assert redacted["<truncated>"] == "<truncated>"
    assert len(redacted) == MAX_COLLECTION_ITEMS + 1


def test_redact_value_handles_cyclic_collection() -> None:
    cyclic: list[object] = []
    cyclic.append(cyclic)
    result = cast("list[object]", redact_value(cyclic))
    assert result == ["<cycle>"]


def test_safe_repr_returns_unavailable_when_json_serialization_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        security_module.json,
        "dumps",
        Mock(side_effect=ValueError("json hostile")),
    )
    assert safe_repr({"visible": "value"}) == '"<unavailable>"'
