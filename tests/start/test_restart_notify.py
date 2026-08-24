from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.start import startup as startup_module


@pytest.mark.asyncio
async def test_notify_restart_success_with_retry_skips_when_env_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(startup_module.RESTART_BY_ENV, raising=False)
    notify = AsyncMock()
    monkeypatch.setattr(startup_module, "notify_restart_success", notify)

    await startup_module._notify_restart_success_with_retry()

    notify.assert_not_awaited()


@pytest.mark.asyncio
async def test_notify_restart_success_with_retry_sends_once_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(startup_module.RESTART_BY_ENV, "qq:12345")
    notify = AsyncMock(return_value=True)
    monkeypatch.setattr(startup_module, "notify_restart_success", notify)

    await startup_module._notify_restart_success_with_retry()

    notify.assert_awaited_once_with("qq", "12345")


@pytest.mark.asyncio
async def test_notify_restart_success_with_retry_retries_until_giving_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(startup_module.RESTART_BY_ENV, "qq:12345")
    notify = AsyncMock(return_value=False)
    monkeypatch.setattr(startup_module, "notify_restart_success", notify)
    sleep = AsyncMock()
    monkeypatch.setattr(startup_module.asyncio, "sleep", sleep)

    await startup_module._notify_restart_success_with_retry()

    assert notify.await_count == 10
    assert sleep.await_count >= 9
