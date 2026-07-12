"""Enforce the subplugin import boundary.

Nested subplugins under core/subplugins/llm_chat/ and core/subplugins/novelai_image/
must NOT reach into parent internals (3+ dot relative imports) or import adapter
packages (nonebot.adapters.*). They may only touch the ..contracts seam, same-package
"." imports, framework packages, the standard library, and third-party packages.
"""

from __future__ import annotations

import ast
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SUBPLUGIN_DIRS = [
    _PROJECT_ROOT
    / "src"
    / "plugins"
    / "nonebot_plugin_lingchu_bot"
    / "core"
    / "subplugins"
    / "llm_chat",
    _PROJECT_ROOT
    / "src"
    / "plugins"
    / "nonebot_plugin_lingchu_bot"
    / "core"
    / "subplugins"
    / "novelai_image",
]


def _collect_subplugin_python_files() -> list[Path]:
    """Collect every .py file from both subplugin packages, skipping __pycache__."""
    files: list[Path] = []
    for subplugin_dir in _SUBPLUGIN_DIRS:
        for path in sorted(subplugin_dir.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            files.append(path)
    return files


def _find_import_violations(source: str) -> list[str]:
    """AST-parse source and return import boundary violation descriptions.

    Flags:
      - ast.ImportFrom with level >= 3 (reaches parent internals via ... or ....)
      - ast.ImportFrom with level == 0 targeting nonebot.adapters.*
      - ast.Import whose alias name starts with nonebot.adapters
    """
    tree = ast.parse(source)
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level >= 3:
                module = node.module or ""
                names = ", ".join(alias.name for alias in node.names)
                violations.append(
                    f"line {node.lineno}: 3+ dot relative import "
                    f"from {'.' * node.level}{module} import {names}"
                )
            elif (
                node.level == 0
                and node.module is not None
                and node.module.startswith("nonebot.adapters")
            ):
                names = ", ".join(alias.name for alias in node.names)
                violations.append(
                    f"line {node.lineno}: adapter import "
                    f"from {node.module} import {names}"
                )
            elif (
                node.level == 0
                and node.module is not None
                and node.module.endswith("services.llm")
            ):
                violations.append(
                    f"line {node.lineno}: direct LLM service import from {node.module}"
                )
        elif isinstance(node, ast.Import):
            violations.extend(
                f"line {node.lineno}: adapter import {alias.name}"
                for alias in node.names
                if alias.name.startswith("nonebot.adapters")
            )
            violations.extend(
                f"line {node.lineno}: direct LLM service import {alias.name}"
                for alias in node.names
                if alias.name.endswith("services.llm")
            )
    return violations


def test_no_subplugin_imports_from_parent_internals_or_adapters() -> None:
    """No subplugin .py file reaches parent internals or adapter packages."""
    violations: list[str] = []
    for path in _collect_subplugin_python_files():
        source = path.read_text(encoding="utf-8")
        violations.extend(
            f"{path}: {violation}" for violation in _find_import_violations(source)
        )
    assert not violations, "subplugin import boundary violations:\n" + "\n".join(
        violations
    )


def test_violation_detection_on_synthetic_source() -> None:
    """The scanner flags 3+ dot relative imports and adapter imports."""
    source = (
        "from ....services.llm import complete_chat\n"
        "from nonebot.adapters.onebot.v11 import Bot\n"
        "import nonebot.adapters.onebot.v11\n"
        "from src.plugins.nonebot_plugin_lingchu_bot.services.llm import complete_chat\n"
        "import src.plugins.nonebot_plugin_lingchu_bot.services.llm\n"
    )
    violations = _find_import_violations(source)
    assert len(violations) == 5
    assert any("3+ dot relative import" in v for v in violations)
    assert any(
        "adapter import" in v and "from nonebot.adapters" in v for v in violations
    )
    assert any(
        "adapter import" in v and "import nonebot.adapters" in v for v in violations
    )
    assert sum("direct LLM service import" in v for v in violations) == 2
