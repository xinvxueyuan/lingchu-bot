"""回归测试：alembic revision ID 必须【进程内跨插件全局唯一】。

背景：`nonebot_plugin_orm` 在启动时把**所有已加载 ORM 插件**的迁移汇成一张迁移图。
lingchu 与 nonebot-plugin-fanqie-verify 的迁移链曾共用 `a1b2c3d4e5f6` /
`b7c8d9e0f1a2` 两个 ID，同一进程加载两个插件时报：

    Revision a1b2c3d4e5f6 is present more than once

进而导致启动迁移检查失败（生产因此长期靠 `ALEMBIC_STARTUP_CHECK=false` 硬撑）。

注意：alembic 的 `revision` 是**全局**命名的，不是「本插件内唯一」——
复制别的插件的迁移模板时最容易把示例 ID 一起复制走。
"""

from __future__ import annotations

from collections import Counter
import os
from pathlib import Path
import re

#: 迁移目录布局（注意：本系列插件的迁移文件**直接放在 migrations/**，
#: 没有 alembic 默认的 versions/ 子目录）
_MIGRATIONS_SUBDIR = "migrations"

_REVISION_RE = re.compile(
    r'^\s*revision\s*(?::\s*str\s*)?=\s*["\']([^"\']+)["\']',
    re.MULTILINE,
)

#: 本仓插件根
_OWN_ROOT = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "plugins"
    / "nonebot_plugin_lingchu_bot"
)


def _candidate_roots() -> list[Path]:
    """可能同时被加载的插件根目录。

    本地开发时兄弟插件在 `C:/dev/...`；生产（qbot 项目）在
    `/root/imqq/qbot/plugins/...`，可用 `QBOT_PLUGINS_DIR` 覆盖；CI 下这些
    路径都不存在，此时只校验本仓 —— 测试不会因此失败。
    """
    roots = [_OWN_ROOT]

    if raw := os.environ.get("QBOT_PLUGINS_DIR"):
        roots.append(Path(raw) / "nonebot_plugin_fanqie_verify")

    # 本地开发常见的兄弟插件位置（存在才校验）
    roots.append(
        Path("C:/dev/ocr-fanqie-novel/src/plugins/nonebot_plugin_fanqie_verify")
    )

    return [r for r in roots if (r / _MIGRATIONS_SUBDIR).is_dir()]


def _collect(roots: list[Path]) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    for root in roots:
        for f in sorted((root / _MIGRATIONS_SUBDIR).glob("*.py")):
            m = _REVISION_RE.search(f.read_text(encoding="utf-8"))
            if m:
                found.append((m.group(1), f))
    return found


def test_alembic_revisions_are_globally_unique() -> None:
    """同一 NoneBot 进程会加载所有插件的迁移图，ID 不允许跨插件重复。"""
    roots = _candidate_roots()
    items = _collect(roots)
    assert items, f"未找到任何迁移文件，测试本身失效（扫描根：{roots}）"

    dupes = {
        rid: cnt for rid, cnt in Counter(rid for rid, _ in items).items() if cnt > 1
    }
    if dupes:
        detail = "\n".join(
            f"  {rid} x{cnt}:\n" + "\n".join(f"      {p}" for r, p in items if r == rid)
            for rid, cnt in sorted(dupes.items())
        )
        raise AssertionError(f"发现跨插件重复的 alembic revision ID：\n{detail}")

    # 顺带保证文件名前缀与 revision 一致（便于人眼排查）
    for rid, path in items:
        assert path.name.startswith(rid), (
            f"迁移文件名前缀与 revision 不一致：{path.name} 的 revision 是 {rid}"
        )
