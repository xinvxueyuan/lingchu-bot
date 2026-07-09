"""i18n-specific pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(params=["zh_CN", "en_US"])
def locale(request: pytest.FixtureRequest) -> str:
    """Provide locales for tests that pass locale explicitly."""
    return request.param


@pytest.fixture(params=["zh_CN", "en_US"])
def configured_locale(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    """Patch the configured project locale for gettext wrapper tests."""
    from src.plugins.nonebot_plugin_lingchu_bot import i18n

    i18n._read_configured_locale.cache_clear()
    monkeypatch.setattr(i18n, "_read_configured_locale", lambda: request.param)
    return request.param
