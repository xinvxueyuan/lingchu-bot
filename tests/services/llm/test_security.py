from __future__ import annotations

from collections.abc import Iterator
from types import MappingProxyType
from typing import Any, cast, override

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.security import (
    MAX_COLLECTION_ITEMS,
    MAX_NESTING_DEPTH,
    MAX_TEXT_LENGTH,
    freeze_value,
    redact_value,
    safe_repr,
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
