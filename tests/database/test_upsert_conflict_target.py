"""upsert 冲突目标校验的测试。

背景：SQLite 的 ``ON CONFLICT (cols)`` 必须与某个唯一索引**逐列精确匹配**，多一列就
会报 ``ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE constraint``，在业务
层表现为 ``DatabaseError('Upsert failed')``。因此 ``upsert`` 在构造语句前就校验冲突目标。
"""

from __future__ import annotations

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.models import (
    BlocklistEntry,
    Platform,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud._base import (
    _get_column_map,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud._bulk import (
    _validate_upsert_conflict_target,
)

BLOCKLIST_IDENTITY = (
    "platform_id",
    "adapter_id",
    "bot_id",
    "scope",
    "scope_key",
    "user_id",
)


def _validate(model: type, fields: list[str]) -> list[str]:
    return _validate_upsert_conflict_target(model, _get_column_map(model), fields, None)


def test_accepts_target_matching_declared_unique_constraint() -> None:
    assert _validate(BlocklistEntry, list(BLOCKLIST_IDENTITY)) == list(
        BLOCKLIST_IDENTITY
    )


def test_accepts_primary_key_target() -> None:
    assert _validate(BlocklistEntry, ["id"]) == ["id"]


def test_rejects_extra_column_absent_from_unique_constraint() -> None:
    """本仓 2026-10 的真实故障：conflict_fields 多了 protocol_id（7 列 vs 6 列）。"""
    with pytest.raises(ValueError, match="does not match any unique constraint"):
        _validate(
            BlocklistEntry,
            [
                "platform_id",
                "adapter_id",
                "protocol_id",
                "bot_id",
                "scope",
                "scope_key",
                "user_id",
            ],
        )


def test_rejects_subset_of_unique_constraint() -> None:
    with pytest.raises(ValueError, match="does not match any unique constraint"):
        _validate(BlocklistEntry, ["platform_id", "adapter_id"])


def test_rejects_unknown_column() -> None:
    with pytest.raises(ValueError, match="Unknown column 'nope'"):
        _validate(BlocklistEntry, ["nope"])


def test_requires_a_conflict_target() -> None:
    with pytest.raises(ValueError, match="conflict target is required"):
        _validate(BlocklistEntry, [])


def test_skips_validation_when_model_declares_no_unique_target() -> None:
    """模型没有声明非主键唯一约束时不应误报（Platform 仅有主键以外的普通列）。"""
    assert _validate(Platform, ["platform_id"]) == ["platform_id"]
