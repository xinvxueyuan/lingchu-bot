"""Import-safe standard-library contracts for runtime settings."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

MAX_RECALL_MESSAGE_DEFAULT_COUNT = 100


class SettingsValidationError(ValueError):
    """Raised when a runtime setting has an invalid value."""


def _value(mapping: Mapping[str, Any], *names: str, default: Any) -> Any:
    for name in names:
        if name in mapping:
            return mapping[name]
    # NoneBot's pydantic Config only surfaces declared fields via model_dump(),
    # so deployment settings provided purely via OS environment variables
    # (e.g. CI job env with no .env file) must fall back to os.environ.
    for name in names:
        if name in os.environ:
            return os.environ[name]
    return default


def _non_negative_int(name: str, value: Any) -> int:
    if type(value) is not int or value < 0:
        raise SettingsValidationError(f"{name} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class DeploymentSettings:
    """Immutable-at-runtime settings owned by NoneBot configuration."""

    superuser_key: str = "123456789abcdef"
    message_store_enabled: bool = True
    message_store_retention_days: int = 30
    message_store_summary_limit: int = 500
    message_store_record_api_calls: bool = True
    message_store_cleanup_enabled: bool = True
    recall_message_default_count: int = 10
    protected_subject_feature_keys: frozenset[str] = field(
        default_factory=lambda: frozenset({
            "kick_member",
            "block_member",
            "global_block_member",
            "member_mute",
            "recall_message",
            "set_member_card",
            "set_member_title",
            "set_member_admin",
            "unset_member_admin",
            "remote_kick",
            "remote_block",
            "remote_mute",
        })
    )
    lingchu_superusers: dict[str, dict[str, str | int]] | None = None
    lingchu_adapter: str | list[str] | None = None

    @classmethod
    def from_mapping(cls, source: Mapping[str, Any]) -> DeploymentSettings:
        superusers = _value(
            source, "LINGCHU_SUPERUSERS", "lingchu_superusers", default=None
        )
        if isinstance(superusers, str):
            try:
                superusers = json.loads(superusers)
            except ValueError as exc:
                raise SettingsValidationError(
                    "LINGCHU_SUPERUSERS must be valid JSON"
                ) from exc
        if superusers is not None:
            if not isinstance(superusers, dict):
                raise SettingsValidationError("LINGCHU_SUPERUSERS must be a mapping")
            normalized: dict[str, dict[str, str | int]] = {}
            for uid, accounts in superusers.items():
                uid_text = str(uid).strip()
                if not uid_text or not isinstance(accounts, dict):
                    raise SettingsValidationError("invalid LINGCHU_SUPERUSERS mapping")
                normalized[uid_text] = {}
                for platform, account in accounts.items():
                    platform_text = str(platform).strip()
                    if not platform_text or not isinstance(account, (str, int)):
                        raise SettingsValidationError(
                            "invalid LINGCHU_SUPERUSERS account"
                        )
                    normalized[uid_text][platform_text] = account
            superusers = normalized
        protected = _value(
            source,
            "LINGCHU_PROTECTED_SUBJECT_FEATURE_KEYS",
            "protected_subject_feature_keys",
            default=cls().protected_subject_feature_keys,
        )
        if isinstance(protected, str):
            try:
                protected = json.loads(protected)
            except ValueError:
                protected = [protected]
        if not isinstance(protected, (list, tuple, set, frozenset)):
            raise SettingsValidationError(
                "protected_subject_feature_keys must be a list"
            )
        retention = _non_negative_int(
            "message_store_retention_days",
            _value(
                source,
                "LINGCHU_MESSAGE_STORE_RETENTION_DAYS",
                "message_store_retention_days",
                default=30,
            ),
        )
        summary = _non_negative_int(
            "message_store_summary_limit",
            _value(
                source,
                "LINGCHU_MESSAGE_STORE_SUMMARY_LIMIT",
                "message_store_summary_limit",
                default=500,
            ),
        )
        count = _value(
            source,
            "LINGCHU_RECALL_MESSAGE_DEFAULT_COUNT",
            "recall_message_default_count",
            default=10,
        )
        if type(count) is not int or not 1 <= count <= MAX_RECALL_MESSAGE_DEFAULT_COUNT:
            raise SettingsValidationError(
                "recall_message_default_count must be between 1 and 100"
            )
        return cls(
            superuser_key=str(
                _value(
                    source,
                    "LINGCHU_SUPERUSER_KEY",
                    "superuser_key",
                    default=cls().superuser_key,
                )
            ),
            message_store_enabled=bool(
                _value(
                    source,
                    "LINGCHU_MESSAGE_STORE_ENABLED",
                    "message_store_enabled",
                    default=True,
                )
            ),
            message_store_retention_days=retention,
            message_store_summary_limit=summary,
            message_store_record_api_calls=bool(
                _value(
                    source,
                    "LINGCHU_MESSAGE_STORE_RECORD_API_CALLS",
                    "message_store_record_api_calls",
                    default=True,
                )
            ),
            message_store_cleanup_enabled=bool(
                _value(
                    source,
                    "LINGCHU_MESSAGE_STORE_CLEANUP_ENABLED",
                    "message_store_cleanup_enabled",
                    default=True,
                )
            ),
            recall_message_default_count=count,
            protected_subject_feature_keys=frozenset(
                str(item).strip() for item in protected if str(item).strip()
            ),
            lingchu_superusers=superusers,
            lingchu_adapter=_value(
                source,
                "LINGCHU_ADAPTER",
                "LINGCHUAdapter",
                "lingchu_adapter",
                "lingchuadapter",
                default=None,
            ),
        )


@dataclass(frozen=True, slots=True)
class MutableRuntimeSettings:
    """Online-editable settings stored in one typed localstore file."""

    permission_platform_runtime_passthrough: bool | dict[str, bool] = True
    command_trigger_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    menu_page_trigger_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> MutableRuntimeSettings:
        unknown = set(raw) - MUTABLE_RUNTIME_FIELDS
        if unknown:
            raise SettingsValidationError(
                f"unknown configuration fields: {', '.join(sorted(unknown))}"
            )
        value = raw.get("permission_platform_runtime_passthrough", True)
        if not isinstance(value, (bool, dict)):
            raise SettingsValidationError(
                "permission_platform_runtime_passthrough must be bool or mapping"
            )
        for name in ("command_trigger_overrides", "menu_page_trigger_overrides"):
            if not isinstance(raw.get(name, {}), dict):
                raise SettingsValidationError(f"{name} must be a mapping")
        return cls(
            value,
            dict(raw.get("command_trigger_overrides", {})),
            dict(raw.get("menu_page_trigger_overrides", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


MUTABLE_RUNTIME_FIELDS = frozenset({
    "permission_platform_runtime_passthrough",
    "command_trigger_overrides",
    "menu_page_trigger_overrides",
})
