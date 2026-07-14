"""Bounded immutable-data and log-redaction helpers for LLM integrations."""

from __future__ import annotations

import json
import math
import re
from types import MappingProxyType
from typing import cast

MAX_NESTING_DEPTH = 8
MAX_COLLECTION_ITEMS = 100
MAX_TEXT_LENGTH = 2048

_MAX_INTEGER_BITS = 4096
_MAX_SAFE_REPR_LENGTH = MAX_TEXT_LENGTH * 4
_CYCLE_MARKER = "<cycle>"
_DEPTH_MARKER = "<max-depth>"
_TRUNCATED_MARKER = "<truncated>"
_REDACTED_MARKER = "<redacted>"
_UNAVAILABLE_MARKER = "<unavailable>"
_UNSUPPORTED_VALUE_ERROR = "unsupported LLM configuration value"
_SECRET_KEY_PARTS = (
    "token",
    "key",
    "authorization",
    "auth",
    "secret",
    "credential",
    "cookie",
    "password",
    "header",
    "query",
)
_CONTROL_CHARACTERS = re.compile(
    r"[\x00-\x1f\x7f-\x9f\u061c\u200e\u200f\u2028\u2029\u202a-\u202e\u2066-\u2069]"
)
_AUTHORIZATION_VALUE = re.compile(r"(?i)\b(bearer|basic)\s+[^\s,;?&]+")
_ASSIGNED_SECRET_VALUE = re.compile(
    r"(?i)(\b(?:authorization|auth|api[-_]?key|x-api-key|token|secret|"
    + r"credential|cookie|password)\b\s*[:=]\s*)"
    + r"(?:\"[^\"]*\"|'[^']*'|[^\s,;?&]+)"
)
CONTROL_PLANE_KEYS = frozenset({
    "access_token",
    "api_key",
    "api_base",
    "base_url",
    "azure_ad_token",
    "azure_endpoint",
    "organization",
    "project",
    "transport",
    "http_client",
    "client",
    "callback",
    "callbacks",
    "success_callback",
    "failure_callback",
    "custom_logger",
    "logger_fn",
    "loggers",
    "headers",
    "extra_headers",
    "default_headers",
    "query",
    "extra_query",
    "default_query",
    "max_retries",
    "retry",
    "retries",
    "retry_config",
    "retry_policy",
    "retry_strategy",
    "num_retries",
    "allowed_fails",
    "fallbacks",
    "context_window_fallbacks",
    "content_policy_fallbacks",
    "router",
    "token",
})

type _ObjectMapping = dict[object, object] | MappingProxyType[object, object]
type _ObjectSequence = list[object] | tuple[object, ...]
type _ObjectCollection = _ObjectSequence | set[object] | frozenset[object]


def _clean_text(value: str) -> str:
    return _CONTROL_CHARACTERS.sub(" ", value)


def _truncate_text(value: str) -> str:
    if len(value) <= MAX_TEXT_LENGTH:
        return value
    return f"{value[: MAX_TEXT_LENGTH - len(_TRUNCATED_MARKER)]}{_TRUNCATED_MARKER}"


def sanitize_message(message: str) -> str:
    """Return bounded public exception text with credential values removed."""
    if type(message) is not str:
        return _REDACTED_MARKER
    cleaned = _clean_text(message[: MAX_TEXT_LENGTH * 2])
    cleaned = _AUTHORIZATION_VALUE.sub(r"\1 <redacted>", cleaned)
    cleaned = _ASSIGNED_SECRET_VALUE.sub(r"\1<redacted>", cleaned)
    return _truncate_text(cleaned)


def _is_secret_key(key: str) -> bool:
    normalized = "".join(
        character for character in key.casefold() if character.isalnum()
    )
    return any(part in normalized for part in _SECRET_KEY_PARTS)


def contains_control_plane_key(value: object) -> bool:
    """Return whether a safe JSON-like value contains a managed control key."""
    value_type = type(value)
    if value_type is dict or value_type is MappingProxyType:
        mapping = cast("_ObjectMapping", value)
        return any(
            type(key) is str
            and (
                key.casefold() in CONTROL_PLANE_KEYS
                or contains_control_plane_key(child)
            )
            for key, child in mapping.items()
        )
    if value_type is list or value_type is tuple:
        return any(
            contains_control_plane_key(child)
            for child in cast("_ObjectSequence", value)
        )
    return False


def contains_sensitive_mapping_entry(value: object) -> bool:
    """Detect credential-like keys or authorization values in a safe mapping."""
    value_type = type(value)
    if value_type is dict or value_type is MappingProxyType:
        mapping = cast("_ObjectMapping", value)
        return any(
            type(key) is str
            and (
                _is_secret_key(key)
                or (
                    type(child) is str
                    and _AUTHORIZATION_VALUE.search(child) is not None
                )
                or contains_sensitive_mapping_entry(child)
            )
            for key, child in mapping.items()
        )
    if value_type is list or value_type is tuple:
        return any(
            contains_sensitive_mapping_entry(child)
            for child in cast("_ObjectSequence", value)
        )
    return False


def safe_type_name(value: object) -> str:
    try:
        name = type(value).__name__
    except BaseException:
        return "object"
    return _truncate_text(_clean_text(name)) if type(name) is str else "object"


def _unsupported_value() -> TypeError:
    return TypeError(_UNSUPPORTED_VALUE_ERROR)


def freeze_value(value: object) -> object:
    """Deep-copy the supported JSON-like domain into immutable containers."""
    try:
        return _freeze(value, depth=0, active=set())
    except TypeError as error:
        if str(error) == _UNSUPPORTED_VALUE_ERROR:
            raise
        raise _unsupported_value() from None
    except BaseException:
        raise _unsupported_value() from None


def _freeze(value: object, *, depth: int, active: set[int]) -> object:
    value_type = type(value)
    if value is None or value_type in {bool, int, float, str, bytes}:
        return value
    if depth >= MAX_NESTING_DEPTH:
        raise _unsupported_value()
    if value_type is dict or value_type is MappingProxyType:
        return _freeze_mapping(
            cast("_ObjectMapping", value), depth=depth, active=active
        )
    if value_type is list or value_type is tuple:
        return _freeze_sequence(
            cast("_ObjectSequence", value), depth=depth, active=active
        )
    raise _unsupported_value()


def _freeze_mapping(
    value: _ObjectMapping,
    *,
    depth: int,
    active: set[int],
) -> MappingProxyType[str, object]:
    identity = id(value)
    if identity in active or len(value) > MAX_COLLECTION_ITEMS:
        raise _unsupported_value()
    active.add(identity)
    try:
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise _unsupported_value()
            frozen[key] = _freeze(item, depth=depth + 1, active=active)
        return MappingProxyType(frozen)
    finally:
        active.remove(identity)


def _freeze_sequence(
    value: list[object] | tuple[object, ...],
    *,
    depth: int,
    active: set[int],
) -> tuple[object, ...]:
    identity = id(value)
    if identity in active or len(value) > MAX_COLLECTION_ITEMS:
        raise _unsupported_value()
    active.add(identity)
    try:
        return tuple(_freeze(item, depth=depth + 1, active=active) for item in value)
    finally:
        active.remove(identity)


def thaw_value(value: object) -> object:
    """Copy a valid frozen value into mutable SDK-friendly containers."""
    try:
        return _thaw(value, depth=0, active=set())
    except TypeError as error:
        if str(error) == _UNSUPPORTED_VALUE_ERROR:
            raise
        raise _unsupported_value() from None
    except BaseException:
        raise _unsupported_value() from None


def _thaw(value: object, *, depth: int, active: set[int]) -> object:
    value_type = type(value)
    if value is None or value_type in {bool, int, float, str, bytes}:
        return value
    if depth >= MAX_NESTING_DEPTH:
        raise _unsupported_value()
    if value_type is dict or value_type is MappingProxyType:
        return _thaw_mapping(cast("_ObjectMapping", value), depth=depth, active=active)
    if value_type is list or value_type is tuple:
        return _thaw_sequence(
            cast("_ObjectSequence", value), depth=depth, active=active
        )
    raise _unsupported_value()


def _thaw_mapping(
    value: _ObjectMapping,
    *,
    depth: int,
    active: set[int],
) -> dict[str, object]:
    identity = id(value)
    if identity in active or len(value) > MAX_COLLECTION_ITEMS:
        raise _unsupported_value()
    active.add(identity)
    try:
        mutable: dict[str, object] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise _unsupported_value()
            mutable[key] = _thaw(item, depth=depth + 1, active=active)
        return mutable
    finally:
        active.remove(identity)


def _thaw_sequence(
    value: list[object] | tuple[object, ...],
    *,
    depth: int,
    active: set[int],
) -> list[object]:
    identity = id(value)
    if identity in active or len(value) > MAX_COLLECTION_ITEMS:
        raise _unsupported_value()
    active.add(identity)
    try:
        return [_thaw(item, depth=depth + 1, active=active) for item in value]
    finally:
        active.remove(identity)


def redact_value(value: object) -> object:
    """Project arbitrary data into bounded, redacted, pure built-in values."""
    try:
        return _redact(value, depth=0, active=set())
    except BaseException:
        return _UNAVAILABLE_MARKER


def _redact(value: object, *, depth: int, active: set[int]) -> object:
    value_type = type(value)
    if value is None or value_type in {bool, int, float, str, bytes}:
        return _redact_scalar(value)
    if depth >= MAX_NESTING_DEPTH:
        return _DEPTH_MARKER
    if isinstance(value, BaseException):
        return _redact_exception(value, depth=depth, active=active)
    if value_type is dict or value_type is MappingProxyType:
        return _redact_mapping(
            cast("_ObjectMapping", value), depth=depth, active=active
        )
    if value_type in {list, tuple, set, frozenset}:
        return _redact_collection(
            cast("_ObjectCollection", value), depth=depth, active=active
        )
    return f"<{safe_type_name(value)}>"


def _redact_scalar(value: object) -> object:
    value_type = type(value)
    if value_type is str:
        return sanitize_message(cast("str", value))
    if value_type is bytes:
        return f"<bytes:{len(cast('bytes', value))}>"
    if value_type is int and cast("int", value).bit_length() > _MAX_INTEGER_BITS:
        return "<large-int>"
    if value_type is float and not math.isfinite(cast("float", value)):
        return "<non-finite-float>"
    return value


def _redact_exception(
    value: BaseException,
    *,
    depth: int,
    active: set[int],
) -> object:
    identity = id(value)
    if identity in active:
        return _CYCLE_MARKER
    active.add(identity)
    try:
        try:
            arguments = value.args
        except BaseException:
            arguments = _UNAVAILABLE_MARKER
        return {
            "type": safe_type_name(value),
            "args": (
                arguments
                if arguments == _UNAVAILABLE_MARKER
                else _redact(arguments, depth=depth + 1, active=active)
            ),
        }
    finally:
        active.remove(identity)


def _redact_mapping(
    value: _ObjectMapping,
    *,
    depth: int,
    active: set[int],
) -> object:
    identity = id(value)
    if identity in active:
        return _CYCLE_MARKER
    active.add(identity)
    try:
        redacted: dict[str, object] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= MAX_COLLECTION_ITEMS:
                redacted[_TRUNCATED_MARKER] = _TRUNCATED_MARKER
                break
            if type(key) is not str:
                redacted[f"<non-string-key:{index}>"] = _REDACTED_MARKER
                continue
            safe_key = _truncate_text(_clean_text(key))
            redacted[safe_key] = (
                _REDACTED_MARKER
                if _is_secret_key(safe_key)
                else _redact(item, depth=depth + 1, active=active)
            )
        return redacted
    finally:
        active.remove(identity)


def _redact_collection(
    value: list[object] | tuple[object, ...] | set[object] | frozenset[object],
    *,
    depth: int,
    active: set[int],
) -> object:
    identity = id(value)
    if identity in active:
        return _CYCLE_MARKER
    active.add(identity)
    try:
        redacted = [
            _redact(item, depth=depth + 1, active=active)
            for index, item in enumerate(value)
            if index < MAX_COLLECTION_ITEMS
        ]
        if len(value) > MAX_COLLECTION_ITEMS:
            redacted.append(_TRUNCATED_MARKER)
        return redacted
    finally:
        active.remove(identity)


def safe_repr(value: object) -> str:
    """Render bounded redacted data without invoking untrusted repr methods."""
    try:
        rendered = json.dumps(
            redact_value(value),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    except BaseException:
        return '"<unavailable>"'
    return rendered if len(rendered) <= _MAX_SAFE_REPR_LENGTH else '"<truncated>"'


__all__ = [
    "MAX_COLLECTION_ITEMS",
    "MAX_NESTING_DEPTH",
    "MAX_TEXT_LENGTH",
    "freeze_value",
    "redact_value",
    "safe_repr",
    "sanitize_message",
    "thaw_value",
]
