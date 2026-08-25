"""Self-contained application restart worker (stdlib only).

Usage: python restart_worker.py <old_pid> <cwd>

The plugin copies this file into its cache directory and spawns it with the
current process id and working directory. The worker starts a fresh bot
process, waits for the NoneBot startup marker, then terminates the old
process and keeps the pipe open until the new worker exits.
"""

from __future__ import annotations

from collections.abc import Mapping
import contextlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import tomllib
from typing import Any

STARTUP_MARKER = "Application startup complete."
STARTUP_TIMEOUT = 30.0
_EXPECTED_ARG_COUNT = 3


class _InvalidProjectConfigError(ValueError):
    """Invalid NoneBot project configuration."""


def _load_project_runtime_config(cwd: Path) -> tuple[list[str], list[str]]:
    """Load adapter modules and builtin plugins from the project TOML file."""
    config_path = cwd / "pyproject.toml"
    with config_path.open("rb") as config_file:
        data: dict[str, Any] = tomllib.load(config_file)
    tool = data.get("tool")
    nonebot = tool.get("nonebot") if isinstance(tool, Mapping) else None
    if not isinstance(nonebot, Mapping):
        raise _InvalidProjectConfigError("missing [tool.nonebot]")

    raw_adapters = nonebot.get("adapters", {})
    adapter_groups: list[Any]
    if isinstance(raw_adapters, Mapping):
        adapter_groups = list(raw_adapters.values())
    elif isinstance(raw_adapters, list):
        adapter_groups = [raw_adapters]
    else:
        raise _InvalidProjectConfigError("adapters must be a list or a table")

    adapter_modules: list[str] = []
    for group in adapter_groups:
        if not isinstance(group, list):
            raise _InvalidProjectConfigError("adapter groups must be lists")
        for adapter in group:
            if not isinstance(adapter, Mapping):
                raise _InvalidProjectConfigError("adapter entries must be tables")
            module_name = adapter.get("module_name")
            if not isinstance(module_name, str) or not module_name:
                raise _InvalidProjectConfigError(
                    "adapter entries require a module_name"
                )
            adapter_modules.append(module_name)

    builtin_plugins = nonebot.get("builtin_plugins", [])
    if not isinstance(builtin_plugins, list) or not all(
        isinstance(plugin, str) for plugin in builtin_plugins
    ):
        raise _InvalidProjectConfigError("builtin_plugins must be a list of strings")

    return adapter_modules, builtin_plugins


def _build_generated_entry(
    adapter_modules: list[str], builtin_plugins: list[str]
) -> str:
    """Generate the same inline startup script used by modern nb-cli."""
    lines = [
        "import importlib",
        "import nonebot",
        "",
        "nonebot.init()",
        "driver = nonebot.get_driver()",
    ]
    lines.extend(
        "driver.register_adapter("
        f"importlib.import_module({json.dumps(module_name)}).Adapter)"
        for module_name in adapter_modules
    )
    if builtin_plugins:
        plugins = ", ".join(json.dumps(plugin) for plugin in builtin_plugins)
        lines.append(f"nonebot.load_builtin_plugins({plugins})")
    lines.extend([
        f"nonebot.load_from_toml({json.dumps('pyproject.toml')})",
        "nonebot.run()",
    ])
    return "\n".join(lines) + "\n"


def _build_entry(cwd: Path) -> list[str]:
    """Compose the command list for the fresh bot process."""
    if (cwd / "bot.py").is_file():
        return [sys.executable, "bot.py"]
    adapter_modules, builtin_plugins = _load_project_runtime_config(cwd)
    return [
        sys.executable,
        "-c",
        _build_generated_entry(adapter_modules, builtin_plugins),
    ]


def _read_stdout(proc: subprocess.Popen[str], marker: threading.Event) -> None:
    """Read the worker output line by line, flagging the startup marker."""
    assert proc.stdout is not None
    for line in proc.stdout:
        if STARTUP_MARKER in line:
            marker.set()


def main() -> int:
    """Run the restart handoff and return the new worker exit code."""
    if len(sys.argv) != _EXPECTED_ARG_COUNT:
        print("usage: python restart_worker.py <old_pid> <cwd>", file=sys.stderr)
        return 2
    old_pid = int(sys.argv[1])
    cwd = Path(sys.argv[2]).resolve()
    entry = _build_entry(cwd)
    env = dict(os.environ)
    proc = subprocess.Popen(
        entry,
        cwd=str(cwd),
        env=env,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    marker = threading.Event()
    reader = threading.Thread(target=_read_stdout, args=(proc, marker), daemon=True)
    reader.start()
    if not marker.wait(STARTUP_TIMEOUT):
        proc.terminate()
        print(
            "restart worker: startup timed out; new worker terminated",
            file=sys.stderr,
        )
        return 1
    with contextlib.suppress(ProcessLookupError):
        os.kill(old_pid, signal.SIGTERM)
    return proc.wait()


if __name__ == "__main__":
    sys.exit(main())
