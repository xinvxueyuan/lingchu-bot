"""全仓静态一致性守卫：校验每个 ``upsert`` 的字面量 ``conflict_fields``。

要求：``conflict_fields`` 必须与目标模型声明的唯一目标（唯一约束 / 唯一索引 /
主键）**逐列一致**。

为什么必须有这道守卫：SQLite 的 ``ON CONFLICT`` 目标不匹配任何唯一索引时，错误只在
**运行期写库那一刻**才出现（``DatabaseError('Upsert failed')``），单元测试若都用假模型
或 mock session 就完全测不到。本仓 2026-10 就因此掉进过一次坑：模型与迁移把身份改成
6 列（去掉 ``protocol_id``），仓库层却仍传 7 列，导致所有拉黑命令失败。

扫描失败必须**报错而不是静默通过**，因此结尾断言最少检查数量。
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import pathlib

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database import models as models_module
from src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud._base import (
    declared_unique_targets,
    primary_key_columns,
)

SOURCE_ROOT = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src"
    / "plugins"
    / "nonebot_plugin_lingchu_bot"
)

#: 期望至少能静态解析出这么多个 upsert 冲突目标；低于此值说明扫描逻辑失效。
MIN_CHECKED_TARGETS = 6


@dataclass(frozen=True)
class UpsertTarget:
    """一处静态可解析的 upsert 冲突目标。"""

    location: str
    model_name: str
    columns: tuple[str, ...]


def _literal_string_list(node: ast.AST | None) -> tuple[str, ...] | None:
    """把字面量字符串列表节点转成元组；含非字面量时返回 None。"""
    if not isinstance(node, ast.List):
        return None
    values: list[str] = []
    for element in node.elts:
        if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
            return None
        values.append(element.value)
    return tuple(values)


def _model_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _iter_upsert_targets() -> list[UpsertTarget]:
    """扫描源码，收集所有 upsert 调用里静态可解析的冲突目标。"""
    targets: list[UpsertTarget] = []
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func_name = _model_name(node.func)
            if func_name != "upsert":
                continue
            conflict_node = next(
                (kw.value for kw in node.keywords if kw.arg == "conflict_fields"), None
            )
            columns = _literal_string_list(conflict_node)
            if columns is None:
                continue
            model_node = node.args[1] if len(node.args) >= 2 else None
            for keyword in node.keywords:
                if keyword.arg == "model":
                    model_node = keyword.value
            name = _model_name(model_node)
            if name is None:
                continue
            targets.append(
                UpsertTarget(
                    location=f"{path.relative_to(SOURCE_ROOT)}:{node.lineno}",
                    model_name=name,
                    columns=columns,
                )
            )
    return targets


def _declared_targets(model_name: str) -> set[frozenset[str]] | None:
    model = getattr(models_module, model_name, None)
    if not isinstance(model, type):
        return None
    targets = set(declared_unique_targets(model))
    primary_key = primary_key_columns(model)
    if primary_key:
        targets.add(primary_key)
    return targets


def test_scan_finds_enough_upsert_targets() -> None:
    """守卫自身的前提：扫描必须真的扫到东西，否则下面的断言会假通过。"""
    assert len(_iter_upsert_targets()) >= MIN_CHECKED_TARGETS


def test_conflict_fields_match_declared_unique_targets() -> None:
    mismatches: list[str] = []
    checked = 0
    for target in _iter_upsert_targets():
        declared = _declared_targets(target.model_name)
        if not declared:
            continue
        checked += 1
        if frozenset(target.columns) not in declared:
            declared_repr = "; ".join(
                ",".join(sorted(item)) for item in sorted(declared, key=sorted)
            )
            mismatches.append(
                f"{target.location}: {target.model_name} 的 conflict_fields="
                f"{target.columns} 与模型声明的唯一目标 ({declared_repr}) 不一致"
            )

    assert not mismatches, "\n".join(mismatches)
    assert checked >= MIN_CHECKED_TARGETS


def test_blocklist_identity_excludes_protocol_id() -> None:
    """回归锚点：黑名单身份是 6 列，protocol_id 只参与冲突后的更新。"""
    blocklist = [
        target
        for target in _iter_upsert_targets()
        if target.model_name == "BlocklistEntry"
    ]

    assert len(blocklist) == 1
    assert "protocol_id" not in blocklist[0].columns
    assert frozenset(blocklist[0].columns) == frozenset({
        "platform_id",
        "adapter_id",
        "bot_id",
        "scope",
        "scope_key",
        "user_id",
    })


if __name__ == "__main__":  # pragma: no cover - 便于本地快速排查
    pytest.main([__file__, "-q"])
