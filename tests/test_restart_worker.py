from __future__ import annotations

from pathlib import Path
import sys

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.restart_worker import (
    _build_entry,
    _build_generated_entry,
    _InvalidProjectConfigError,
    _load_project_runtime_config,
)


def _write_pyproject(
    tmp_path: Path,
    *,
    adapters_toml: str | None = None,
    builtin_plugins: list[str] | None = None,
    include_nonebot: bool = True,
) -> Path:
    """Write a pyproject.toml fixture and return its path."""
    lines: list[str] = []
    if include_nonebot:
        lines.append("[tool.nonebot]")
        if builtin_plugins is not None:
            plugins = ", ".join(f'"{plugin}"' for plugin in builtin_plugins)
            lines.append(f"builtin_plugins = [{plugins}]")
        if adapters_toml is not None:
            lines.append(adapters_toml)
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config_path


_DICT_ADAPTERS = """\
[tool.nonebot.adapters]
nonebot-adapter-onebot = [
    { name = "OneBot V11", module_name = "nonebot.adapters.onebot.v11" },
]
"""

_LIST_ADAPTERS = """\
adapters = [
    { name = "OneBot V11", module_name = "nonebot.adapters.onebot.v11" },
]
"""


def test_build_entry_uses_bot_py_when_present(tmp_path: Path) -> None:
    (tmp_path / "bot.py").write_text("import nonebot\n", encoding="utf-8")

    entry = _build_entry(tmp_path)

    assert entry == [sys.executable, "bot.py"]


def test_build_entry_generates_inline_entry_without_bot_py(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, adapters_toml=_DICT_ADAPTERS)

    entry = _build_entry(tmp_path)

    assert entry[0] == sys.executable
    assert entry[1] == "-c"
    assert "nonebot.init()" in entry[2]
    assert "nonebot.run()" in entry[2]


def test_load_project_runtime_config_parses_dict_adapters(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, adapters_toml=_DICT_ADAPTERS)

    adapter_modules, builtin_plugins = _load_project_runtime_config(tmp_path)

    assert adapter_modules == ["nonebot.adapters.onebot.v11"]
    assert builtin_plugins == []


def test_load_project_runtime_config_parses_list_adapters(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, adapters_toml=_LIST_ADAPTERS)

    adapter_modules, builtin_plugins = _load_project_runtime_config(tmp_path)

    assert adapter_modules == ["nonebot.adapters.onebot.v11"]
    assert builtin_plugins == []


def test_load_project_runtime_config_parses_builtin_plugins(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        adapters_toml=_DICT_ADAPTERS,
        builtin_plugins=["echo", "single_session"],
    )

    adapter_modules, builtin_plugins = _load_project_runtime_config(tmp_path)

    assert adapter_modules == ["nonebot.adapters.onebot.v11"]
    assert builtin_plugins == ["echo", "single_session"]


def test_load_project_runtime_config_missing_nonebot_section(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, include_nonebot=False)

    with pytest.raises(_InvalidProjectConfigError, match=r"missing \[tool.nonebot\]"):
        _load_project_runtime_config(tmp_path)


def test_load_project_runtime_config_invalid_adapters_type(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, adapters_toml='adapters = "not-a-table"')

    with pytest.raises(
        _InvalidProjectConfigError, match="adapters must be a list or a table"
    ):
        _load_project_runtime_config(tmp_path)


def test_load_project_runtime_config_invalid_adapter_group(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        adapters_toml='[tool.nonebot.adapters]\nnonebot-adapter-onebot = "oops"',
    )

    with pytest.raises(
        _InvalidProjectConfigError, match="adapter groups must be lists"
    ):
        _load_project_runtime_config(tmp_path)


def test_load_project_runtime_config_invalid_adapter_entry(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, adapters_toml='adapters = ["not-a-table"]')

    with pytest.raises(
        _InvalidProjectConfigError, match="adapter entries must be tables"
    ):
        _load_project_runtime_config(tmp_path)


def test_load_project_runtime_config_missing_module_name(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        adapters_toml='adapters = [{ name = "OneBot V11" }]',
    )

    with pytest.raises(
        _InvalidProjectConfigError, match="adapter entries require a module_name"
    ):
        _load_project_runtime_config(tmp_path)


def test_load_project_runtime_config_invalid_builtin_plugins(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        adapters_toml=_DICT_ADAPTERS,
        builtin_plugins=["echo"],
    )
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'builtin_plugins = ["echo"]', 'builtin_plugins = "echo"'
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        _InvalidProjectConfigError, match="builtin_plugins must be a list of strings"
    ):
        _load_project_runtime_config(tmp_path)


def test_build_generated_entry_contains_startup_lines() -> None:
    script = _build_generated_entry(
        ["nonebot.adapters.onebot.v11"], ["echo", "single_session"]
    )

    assert "import importlib" in script
    assert "import nonebot" in script
    assert "nonebot.init()" in script
    assert (
        'driver.register_adapter(importlib.import_module("nonebot.adapters.onebot.v11").Adapter)'
        in script
    )
    assert 'nonebot.load_builtin_plugins("echo", "single_session")' in script
    assert 'nonebot.load_from_toml("pyproject.toml")' in script
    assert "nonebot.run()" in script


def test_build_generated_entry_without_builtin_plugins() -> None:
    script = _build_generated_entry(["nonebot.adapters.onebot.v11"], [])

    assert "load_builtin_plugins" not in script
    assert 'nonebot.load_from_toml("pyproject.toml")' in script
    assert "nonebot.run()" in script
