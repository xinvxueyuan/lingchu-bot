"""SQLite 并发调优：WAL + busy_timeout + synchronous=NORMAL。

背景（2026-08-14 实测）：nonebot_plugin_orm 默认 SQLite 处于
rollback-journal（delete）模式，busy_timeout 仅 5 秒——消息存储/审计等
并发写入时会触发 ``sqlite3.OperationalError: database is locked`` 锁风暴，
严重时拖住插件导致命令无响应。

``PRAGMA journal_mode=WAL`` 与 ``synchronous=NORMAL`` 是数据库级持久设置，
执行一次后对所有后续进程/连接生效；``busy_timeout`` 由 ORM 引擎配置
（``SQLALCHEMY_ENGINE_OPTIONS={"connect_args": {"timeout": 30}}``）覆盖。
"""

from __future__ import annotations

from pathlib import Path
import sqlite3

from nonebot import logger

_BUSY_TIMEOUT_MS = 30_000
"""busy_timeout 毫秒数（对当前连接；ORM 连接的 busy timeout 由引擎配置决定）。"""


async def _resolve_sqlite_db_path() -> Path | None:
    """通过 ORM 默认绑定解析 SQLite 数据库文件路径。

    返回 ``None`` 表示非 SQLite 数据库或路径不可解析（调用方跳过调优）。
    """
    from nonebot_plugin_orm import get_session
    from sqlalchemy.ext.asyncio import AsyncEngine

    try:
        async with get_session() as session:
            bind = session.bind
            if not isinstance(bind, AsyncEngine):
                return None
            url = bind.url
            if not str(url.drivername).startswith("sqlite"):
                return None
            database = url.database
            return Path(database) if database else None
    except Exception:  # 路径解析失败时跳过调优（fail-soft，不阻断插件启动）
        logger.exception("解析 SQLite 数据库路径失败，跳过并发调优")
        return None


async def tune_sqlite_connection() -> None:
    """应用 SQLite 并发调优 PRAGMA（WAL / synchronous / busy_timeout）。"""
    path = await _resolve_sqlite_db_path()
    if path is None:
        logger.debug("跳过 SQLite 并发调优：非 SQLite 数据库或路径不可解析")
        return
    try:
        conn = sqlite3.connect(str(path), timeout=30)
        try:
            journal = conn.execute("PRAGMA journal_mode=WAL").fetchone()
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
            conn.commit()
        finally:
            conn.close()
        logger.info(
            "SQLite 并发调优完成 (path={}, journal_mode={}, busy_timeout={}ms)",
            path,
            journal[0] if journal else "?",
            _BUSY_TIMEOUT_MS,
        )
    except Exception:  # 调优失败仅记录（fail-soft，不阻断插件启动）
        logger.exception("SQLite 并发调优失败 (path={})", path)
