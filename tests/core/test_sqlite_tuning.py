"""Tests for SQLite concurrency tuning (WAL / busy_timeout).

NOTE: 所有 lingchu 模块 import 放在函数内部——模块级 import
``nonebot_plugin_lingchu_bot.*`` 会触发包 __init__ 的副作用链
（start/startup → require(...)），在 pytest 收集期执行会污染
后续测试的插件上下文（实测导致全量测试 45 个失败）。
"""

from pathlib import Path
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()


class _FakeCtx:
    """Async context manager returning a fake session."""

    def __init__(self, session: object) -> None:
        self._session = session

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, *exc_info: object) -> bool:
        return False


class _FakeSession:
    def __init__(self, drivername: str, database: str) -> None:
        from unittest.mock import MagicMock

        from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

        if drivername == "postgresql":
            # 非 AsyncEngine 绑定：验证 isinstance 检查分支返回 None
            self.bind: AsyncEngine = MagicMock()  # type: ignore[assignment]
        else:
            url = (
                f"sqlite+aiosqlite:///{database}"
                if drivername == "sqlite"
                else f"{drivername}:///{database}"
            )
            self.bind: AsyncEngine = create_async_engine(url)  # type: ignore[assignment]


async def test_tune_sqlite_connection_applies_wal(tmp_path: Path) -> None:
    """tune_sqlite_connection 对真实 SQLite 文件应用 WAL（数据库级持久）。"""
    from nonebot_plugin_lingchu_bot.core.sqlite_tuning import tune_sqlite_connection

    db_path = tmp_path / "test.db"
    _make_db(db_path)

    with patch(
        "nonebot_plugin_lingchu_bot.core.sqlite_tuning._resolve_sqlite_db_path",
        new=AsyncMock(return_value=db_path),
    ):
        await tune_sqlite_connection()

    # journal_mode 是数据库级持久设置：新连接也应读到 wal
    conn = sqlite3.connect(str(db_path))
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        conn.close()


async def test_tune_sqlite_connection_applies_connection_pragmas(
    tmp_path: Path,
) -> None:
    """busy_timeout / synchronous 等连接级 PRAGMA 被应用到调优连接。

    （连接级设置不持久化到 DB，ORM 连接的 busy_timeout 由引擎配置
    SQLALCHEMY_ENGINE_OPTIONS 覆盖——见模块 docstring。）
    """
    from nonebot_plugin_lingchu_bot.core.sqlite_tuning import (
        _BUSY_TIMEOUT_MS,
        tune_sqlite_connection,
    )

    db_path = tmp_path / "test.db"
    _make_db(db_path)
    fake_conn = MagicMock()
    fake_conn.execute.return_value.fetchone.return_value = ("wal",)

    with (
        patch(
            "nonebot_plugin_lingchu_bot.core.sqlite_tuning._resolve_sqlite_db_path",
            new=AsyncMock(return_value=db_path),
        ),
        patch("sqlite3.connect", return_value=fake_conn) as mock_connect,
    ):
        await tune_sqlite_connection()

    mock_connect.assert_called_once_with(str(db_path), timeout=30)
    executed = [call.args[0] for call in fake_conn.execute.call_args_list]
    assert "PRAGMA journal_mode=WAL" in executed
    assert "PRAGMA synchronous=NORMAL" in executed
    assert f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}" in executed


async def test_tune_sqlite_connection_skips_non_sqlite() -> None:
    """路径解析为 None 时跳过调优（不触碰 sqlite3.connect）。"""
    from nonebot_plugin_lingchu_bot.core.sqlite_tuning import tune_sqlite_connection

    with (
        patch(
            "nonebot_plugin_lingchu_bot.core.sqlite_tuning._resolve_sqlite_db_path",
            new=AsyncMock(return_value=None),
        ),
        patch("sqlite3.connect") as mock_connect,
    ):
        await tune_sqlite_connection()

    mock_connect.assert_not_called()


async def test_tune_sqlite_connection_swallows_db_errors() -> None:
    """DB 异常被捕获并记录，不向外抛出（启动流程不因调优失败中断）。"""
    from nonebot_plugin_lingchu_bot.core.sqlite_tuning import tune_sqlite_connection

    with (
        patch(
            "nonebot_plugin_lingchu_bot.core.sqlite_tuning._resolve_sqlite_db_path",
            new=AsyncMock(return_value=Path("/nonexistent/dir/db.sqlite3")),
        ),
        patch("nonebot_plugin_lingchu_bot.core.sqlite_tuning.logger") as mock_logger,
    ):
        await tune_sqlite_connection()

    mock_logger.exception.assert_called_once()


@pytest.mark.parametrize(
    ("drivername", "database", "expected"),
    [
        ("sqlite", "/data/db.sqlite3", Path("/data/db.sqlite3")),
        ("sqlite+aiosqlite", "relative/db.sqlite3", Path("relative/db.sqlite3")),
        ("postgresql", "mydb", None),
    ],
)
async def test_resolve_sqlite_db_path(
    drivername: str, database: str, expected: Path | None
) -> None:
    """_resolve_sqlite_db_path 从 ORM 绑定解析 sqlite 路径；非 sqlite 返回 None。"""
    from nonebot_plugin_lingchu_bot.core.sqlite_tuning import _resolve_sqlite_db_path

    fake_session = _FakeSession(drivername, database)
    fake_ctx = _FakeCtx(fake_session)
    with patch(
        "nonebot_plugin_orm.get_session",
        new=MagicMock(return_value=fake_ctx),
    ):
        result = await _resolve_sqlite_db_path()
    assert result == expected
