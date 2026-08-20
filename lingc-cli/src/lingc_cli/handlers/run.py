"""Safe startup and supervision for the ``lc run`` command."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import json
from pathlib import Path
import sys
import tomllib
from typing import Any, NoReturn

from lingc_cli.consts import DEFAULT_STARTUP_TIMEOUT, STARTUP_MARKER
from lingc_cli.core import config, meta
from lingc_cli.exceptions import EnvironmentNotReadyError
from lingc_cli.handlers.process import await_process, create_process
from lingc_cli.handlers.reloader import Reloader, ReloaderError
from lingc_cli.handlers.signal import register_signal_forwarder, terminate_process
from lingc_cli.i18n import _


def _raise_invalid_project_config(detail: str) -> NoReturn:
    """Raise a consistent error for invalid NoneBot project metadata."""
    raise EnvironmentNotReadyError(
        _("Invalid NoneBot project configuration: {detail}").format(detail=detail)
    )


def _load_project_runtime_config(cwd: Path) -> tuple[list[str], list[str]]:
    """Load adapter modules and builtin plugins from the project TOML file."""
    project_root = meta.project_root(cwd)
    config_path = project_root / "pyproject.toml"
    try:
        with config_path.open("rb") as config_file:
            data: dict[str, Any] = tomllib.load(config_file)
    except FileNotFoundError as exc:
        raise EnvironmentNotReadyError(
            _("Cannot find pyproject.toml for the NoneBot project.")
        ) from exc
    except tomllib.TOMLDecodeError as exc:
        _raise_invalid_project_config(f"invalid TOML: {exc}")

    tool = data.get("tool")
    nonebot = tool.get("nonebot") if isinstance(tool, Mapping) else None
    if not isinstance(nonebot, Mapping):
        _raise_invalid_project_config("missing [tool.nonebot]")

    raw_adapters = nonebot.get("adapters", {})
    adapter_groups: list[Any]
    if isinstance(raw_adapters, Mapping):
        adapter_groups = list(raw_adapters.values())
    elif isinstance(raw_adapters, list):
        adapter_groups = [raw_adapters]
    else:
        _raise_invalid_project_config("adapters must be a list or a table")

    adapter_modules: list[str] = []
    for group in adapter_groups:
        if not isinstance(group, list):
            _raise_invalid_project_config("adapter groups must be lists")
        for adapter in group:
            if not isinstance(adapter, Mapping):
                _raise_invalid_project_config("adapter entries must be tables")
            module_name = adapter.get("module_name")
            if not isinstance(module_name, str) or not module_name:
                _raise_invalid_project_config("adapter entries require a module_name")
            adapter_modules.append(module_name)

    builtin_plugins = nonebot.get("builtin_plugins", [])
    if not isinstance(builtin_plugins, list) or not all(
        isinstance(plugin, str) for plugin in builtin_plugins
    ):
        _raise_invalid_project_config("builtin_plugins must be a list of strings")

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


def _build_entry(python: str, cmd: list[str], cwd: Path) -> list[str]:
    """Compose the command list for the bot process.

    An explicit ``cmd`` wins; otherwise run ``bot.py`` when present, falling
    back to an inline nb-cli-style startup script generated from the project
    configuration.
    """
    if cmd:
        return [python, *cmd]
    if (cwd / "bot.py").is_file():
        return [python, "bot.py"]
    adapter_modules, builtin_plugins = _load_project_runtime_config(cwd)
    return [
        python,
        "-c",
        _build_generated_entry(adapter_modules, builtin_plugins),
    ]


async def _check_python(python: str) -> None:
    """Verify the resolved interpreter can be spawned, else raise.

    Raises :class:`EnvironmentNotReadyError` if the interpreter cannot be
    launched or its smoke probe returns a non-zero status.
    """
    try:
        proc = await create_process(
            [python, "--version"],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        raise EnvironmentNotReadyError(
            _("Failed to spawn Python interpreter: {python}").format(
                python=python,
            )
        ) from exc
    code = await await_process(proc)
    if code != 0:
        raise EnvironmentNotReadyError(
            _("Python interpreter exited with code {code}: {python}").format(
                code=code,
                python=python,
            )
        )


async def _forward_output(
    stream: asyncio.StreamReader | None,
    marker_found: asyncio.Event,
) -> None:
    """Stream child output to stdout, flagging the startup marker."""
    if stream is None:
        return
    async for raw in stream:
        text = raw.decode(errors="replace")
        if STARTUP_MARKER in text:
            marker_found.set()
        if sys.stdout is not None:
            sys.stdout.write(text)
            sys.stdout.flush()


async def _start_and_confirm(
    entry: list[str],
    cwd: Path,
    timeout: int,
) -> asyncio.subprocess.Process:
    """Spawn *entry*, forward output, and wait for a clean startup.

    Raises :class:`ReloaderError` with the exit code when the child exits
    before the startup marker (a crash) or when startup times out (``124``).
    """
    marker_found = asyncio.Event()
    proc = await create_process(
        entry,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    register_signal_forwarder(proc)
    reader_task = asyncio.create_task(_forward_output(proc.stdout, marker_found))
    exit_task = asyncio.create_task(proc.wait())
    marker_task = asyncio.create_task(marker_found.wait())
    done, _ = await asyncio.wait(
        {marker_task, exit_task},
        timeout=timeout,
        return_when=asyncio.FIRST_COMPLETED,
    )
    if exit_task in done:
        marker_task.cancel()
        await reader_task
        raise ReloaderError(await await_process(proc))
    if marker_task in done:
        await marker_task
        return proc
    marker_task.cancel()
    await terminate_process(proc)
    await reader_task
    raise ReloaderError(124)


async def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = DEFAULT_STARTUP_TIMEOUT,
    reload: bool = False,
) -> int:
    """Safely start the bot and supervise it until it exits.

    ``cmd`` may be empty to auto-select the entry point (``bot.py`` or an
    inline nb-cli-style generated script). Returns the child exit code, or
    ``124`` if startup timed out. With ``reload`` the child is restarted on
    file changes.
    """
    if cwd is None:
        cwd = config.get_cwd() or Path.cwd()
    cwd = cwd.resolve()
    if not cmd:
        cwd = meta.project_root(cwd)
    python = meta.resolve_python(cwd)
    await _check_python(python)
    entry = _build_entry(python, cmd, cwd)

    if reload:
        reloader = Reloader(
            startup_func=lambda: _start_and_confirm(entry, cwd, timeout),
            shutdown_func=terminate_process,
            cwd=cwd,
        )
        return await reloader.run()

    try:
        proc = await _start_and_confirm(entry, cwd, timeout)
    except ReloaderError as exc:
        return exc.exit_code
    return await await_process(proc)
