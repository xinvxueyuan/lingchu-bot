"""Import-safe Pydantic contracts for Lingchu deployment and mutable settings."""

from __future__ import annotations

import json
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class DeploymentSettings(BaseModel):
    """Immutable-at-runtime settings owned by NoneBot configuration."""

    superuser_key: str = Field(
        default="123456789abcdef",
        validation_alias=AliasChoices("LINGCHU_SUPERUSER_KEY", "superuser_key"),
    )
    message_store_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "LINGCHU_MESSAGE_STORE_ENABLED", "message_store_enabled"
        ),
    )
    message_store_retention_days: int = Field(
        default=30,
        ge=0,
        validation_alias=AliasChoices(
            "LINGCHU_MESSAGE_STORE_RETENTION_DAYS",
            "message_store_retention_days",
        ),
    )
    message_store_summary_limit: int = Field(
        default=500,
        ge=0,
        validation_alias=AliasChoices(
            "LINGCHU_MESSAGE_STORE_SUMMARY_LIMIT",
            "message_store_summary_limit",
        ),
    )
    message_store_record_api_calls: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "LINGCHU_MESSAGE_STORE_RECORD_API_CALLS",
            "message_store_record_api_calls",
        ),
    )
    message_store_cleanup_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "LINGCHU_MESSAGE_STORE_CLEANUP_ENABLED",
            "message_store_cleanup_enabled",
        ),
    )
    recall_message_default_count: int = Field(
        default=10,
        ge=1,
        le=100,
        validation_alias=AliasChoices(
            "LINGCHU_RECALL_MESSAGE_DEFAULT_COUNT",
            "recall_message_default_count",
        ),
    )
    protected_subject_feature_keys: frozenset[str] = Field(
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
        }),
        validation_alias=AliasChoices(
            "LINGCHU_PROTECTED_SUBJECT_FEATURE_KEYS",
            "protected_subject_feature_keys",
        ),
    )
    lingchu_superusers: dict[str, dict[str, str | int]] | None = Field(
        default=None,
        validation_alias=AliasChoices("lingchu_superusers", "LINGCHU_SUPERUSERS"),
    )
    lingchu_adapter: str | list[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("lingchu_adapter"),
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    @field_validator("lingchu_superusers", mode="before")
    @classmethod
    def _validate_lingchu_superusers(
        cls,
        value: Any,
    ) -> dict[str, dict[str, str | int]] | None:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError as exc:
                raise ValueError("LINGCHU_SUPERUSERS must be valid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("LINGCHU_SUPERUSERS must be a mapping")
        result: dict[str, dict[str, str | int]] = {}
        for uid, accounts in value.items():
            uid_text = str(uid).strip()
            if not uid_text:
                raise ValueError("LINGCHU_SUPERUSERS UID cannot be empty")
            if not isinstance(accounts, dict):
                raise ValueError("LINGCHU_SUPERUSERS account value must be a mapping")
            result[uid_text] = {}
            for platform_id, account_id in accounts.items():
                platform_text = str(platform_id).strip()
                if not platform_text:
                    raise ValueError("LINGCHU_SUPERUSERS platform cannot be empty")
                if not isinstance(account_id, (str, int)):
                    raise ValueError("LINGCHU_SUPERUSERS account id must be str or int")
                result[uid_text][platform_text] = account_id
        return result

    @field_validator("protected_subject_feature_keys", mode="before")
    @classmethod
    def _validate_protected_subject_feature_keys(cls, value: Any) -> frozenset[str]:
        if value is None:
            return frozenset()
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                value = [value]
        if not isinstance(value, (list, tuple, set, frozenset)):
            raise TypeError("protected_subject_feature_keys must be a list")
        return frozenset(str(item).strip() for item in value if str(item).strip())


class MutableRuntimeSettings(BaseModel):
    """Online-editable settings stored in one typed localstore file."""

    permission_platform_runtime_passthrough: bool | dict[str, bool] = True
    command_trigger_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    menu_page_trigger_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


MUTABLE_RUNTIME_FIELDS = frozenset(MutableRuntimeSettings.model_fields)
