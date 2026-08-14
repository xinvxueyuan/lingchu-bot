"""Tests for DeploymentSettings OS environment variable fallback."""

from __future__ import annotations

import pytest

from src.plugins._lingchu_bot_contracts.runtime_settings import (
    DeploymentSettings,
    SettingsValidationError,
)


@pytest.fixture(autouse=True)
def _clear_lingchu_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure tests are isolated from any ambient LINGCHU_* environment."""

    def _unset(name: str) -> None:
        monkeypatch.delenv(name, raising=False)

    for name in (
        "LINGCHU_SUPERUSERS",
        "LINGCHU_ADAPTER",
        "LINGCHU_SUPERUSER_KEY",
        "LINGCHU_MESSAGE_STORE_ENABLED",
        "LINGCHU_MESSAGE_STORE_RETENTION_DAYS",
        "LINGCHU_MESSAGE_STORE_SUMMARY_LIMIT",
        "LINGCHU_MESSAGE_STORE_RECORD_API_CALLS",
        "LINGCHU_MESSAGE_STORE_CLEANUP_ENABLED",
        "LINGCHU_RECALL_MESSAGE_DEFAULT_COUNT",
        "LINGCHU_PROTECTED_SUBJECT_FEATURE_KEYS",
    ):
        _unset(name)


def test_env_fallback_loads_superusers_from_os_environ(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINGCHU_SUPERUSERS", '{"smoke_user":{"qq":"42"}}')

    settings = DeploymentSettings.from_mapping({})

    assert settings.lingchu_superusers == {"smoke_user": {"qq": "42"}}


def test_env_fallback_parses_boolean_values_case_insensitively(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINGCHU_MESSAGE_STORE_ENABLED", "false")
    monkeypatch.setenv("LINGCHU_MESSAGE_STORE_RECORD_API_CALLS", "False")
    monkeypatch.setenv("LINGCHU_MESSAGE_STORE_CLEANUP_ENABLED", "0")

    settings = DeploymentSettings.from_mapping({})

    assert settings.message_store_enabled is False
    assert settings.message_store_record_api_calls is False
    assert settings.message_store_cleanup_enabled is False


def test_env_fallback_parses_integer_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINGCHU_MESSAGE_STORE_RETENTION_DAYS", "45")
    monkeypatch.setenv("LINGCHU_MESSAGE_STORE_SUMMARY_LIMIT", "800")
    monkeypatch.setenv("LINGCHU_RECALL_MESSAGE_DEFAULT_COUNT", "20")

    settings = DeploymentSettings.from_mapping({})

    assert settings.message_store_retention_days == 45
    assert settings.message_store_summary_limit == 800
    assert settings.recall_message_default_count == 20


def test_env_fallback_parses_adapter_and_superuser_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINGCHU_ADAPTER", "~onebot.v11")
    monkeypatch.setenv("LINGCHU_SUPERUSER_KEY", "abc123")

    settings = DeploymentSettings.from_mapping({})

    assert settings.lingchu_adapter == "~onebot.v11"
    assert settings.superuser_key == "abc123"


def test_env_fallback_rejects_invalid_boolean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINGCHU_MESSAGE_STORE_ENABLED", "not-a-bool")

    with pytest.raises(SettingsValidationError, match="message_store_enabled"):
        DeploymentSettings.from_mapping({})


def test_env_fallback_rejects_invalid_integer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINGCHU_MESSAGE_STORE_RETENTION_DAYS", "many")

    with pytest.raises(SettingsValidationError, match="message_store_retention_days"):
        DeploymentSettings.from_mapping({})


def test_mapping_values_still_take_precedence_over_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINGCHU_SUPERUSERS", '{"env_user":{"qq":"1"}}')

    settings = DeploymentSettings.from_mapping({
        "LINGCHU_SUPERUSERS": {"mapping_user": {"qq": "2"}}
    })

    assert settings.lingchu_superusers == {"mapping_user": {"qq": "2"}}
