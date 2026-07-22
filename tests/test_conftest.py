"""Tests for pytest session configuration helpers."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from nonebug import NONEBOT_START_LIFESPAN

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

from tests.conftest import (
    _disable_nonebug_auto_lifespan,
    _serialize_startup_for_shared_database,
    _should_serialize_startup_for_shared_database,
)


def test_startup_runs_normally_for_local_database() -> None:
    assert _should_serialize_startup_for_shared_database(None, "master") is False


def test_startup_runs_normally_for_serial_external_database() -> None:
    assert (
        _should_serialize_startup_for_shared_database(
            "sqlite+aiosqlite:///test.db",
            "master",
        )
        is False
    )


def test_startup_serialized_for_xdist_external_database() -> None:
    assert (
        _should_serialize_startup_for_shared_database(
            "postgresql+psycopg://test",
            "gw0",
        )
        is True
    )


def test_nonebug_auto_lifespan_is_disabled() -> None:
    config = cast("pytest.Config", SimpleNamespace(stash={}))

    _disable_nonebug_auto_lifespan(config)

    assert config.stash[NONEBOT_START_LIFESPAN] is False


def test_serialize_startup_for_shared_database_wraps_startup_hooks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def first_startup() -> None:
        calls.append("first")

    async def second_startup() -> None:
        calls.append("second")

    async def startup() -> None:
        for func in driver._lifespan._startup_funcs:
            result = func()
            if asyncio.iscoroutine(result):
                await result

    monkeypatch.chdir(tmp_path)
    driver = SimpleNamespace(
        _lifespan=SimpleNamespace(
            _startup_funcs=[first_startup, second_startup],
            startup=startup,
        )
    )

    assert _serialize_startup_for_shared_database(driver) == 2
    assert driver._lifespan._startup_funcs == [first_startup, second_startup]

    asyncio.run(driver._lifespan.startup())

    assert calls == ["first", "second"]
