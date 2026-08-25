"""Tests for lingc_cli.i18n."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lingc_cli import i18n

if TYPE_CHECKING:
    import pytest


def test_normalize_locale_default() -> None:
    assert i18n.normalize_locale(None) == "en"
    assert i18n.normalize_locale("") == "en"


def test_normalize_locale_dash_to_underscore() -> None:
    assert i18n.normalize_locale("zh-CN") == "zh_CN"


def test_normalize_locale_strips_encoding() -> None:
    assert i18n.normalize_locale("zh_CN.UTF-8") == "zh_CN"


def test_normalize_locale_zh_alias() -> None:
    assert i18n.normalize_locale("zh") == "zh_CN"


def test_get_locale_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINGC_LOCALE", "zh_CN")
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    monkeypatch.delenv("LANG", raising=False)
    assert i18n.get_locale() == "zh_CN"


def test_get_locale_os_declaration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LINGC_LOCALE", raising=False)
    monkeypatch.setenv("LC_ALL", "zh_CN.UTF-8")
    assert i18n.get_locale() == "zh_CN"


def test_get_locale_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINGC_LOCALE", "en")
    monkeypatch.setenv("LC_ALL", "zh_CN")
    assert i18n.get_locale() == "en"


def test_gettext_default_english() -> None:
    assert (
        i18n.gettext("Run environment diagnostics.") == "Run environment diagnostics."
    )


def test_gettext_zh_cn_translation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINGC_LOCALE", "zh_CN")
    assert i18n.gettext("Run environment diagnostics.") == "运行环境诊断。"
