"""Safe startup and supervision for the ``lc run`` command."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import json
import os
from pathlib import Path
import sys
import tempfile
import tomllib
from typing import Any, NoReturn

from lingc_cli.consts import DEFAULT_STARTUP_TIMEOUT, STARTUP_MARKER
from lingc_cli.core import config, meta
from lingc_cli.exceptions import EnvironmentNotReadyError
from lingc_cli.handlers.process import await_process, create_process
from lingc_cli.handlers.reloader import Reloader, ReloaderError
from lingc_cli.handlers.signal import register_signal_forwarder, terminate_process
from lingc_cli.i18n import _
from lingc_cli.log import get_logger

# 宿主心跳监听间隔(秒)
HEARTBEAT_INTERVAL = 5.0

# lc 宿主运行时标识: 注入被监督子进程(worker)环境, 使其可识别宿主会话。
_LC_HOSTED_ENV = "LINGCHU_LC_HOSTED"
# 重启标志文件路径: worker 写入 JSON 即请求宿主重启自身应用。
_RESTART_FLAG_ENV = "LINGCHU_RESTART_FLAG_PATH"
# 重启原因: 宿主重拉起 worker 时注入, 标明由哪个平台/账号触发。
_RESTART_BY_ENV = "LINGCHU_RESTART_BY"

logger = get_logger("run")


def _color_env() -> dict[str, str] | None:
    """Return child env overrides that force color output on a TTY parent.

    The child's stdout is a pipe (not a TTY), so loguru/rich disable colors.
    When the parent terminal supports color, force them back on so the
    forwarded output keeps its styling. Returns ``None`` when the parent
    stdout is not a terminal (e.g. redirected), leaving colors disabled.
    """
    if sys.stdout is None or not sys.stdout.isatty():
        return None
    env = dict(os.environ)
    env.setdefault("LOGURU_COLORIZE", "true")
    env.setdefault("FORCE_COLOR", "1")
    return env


def _resolve_restart_flag_path() -> Path:
    """Return the absolute path of the shared restart flag file.

    The worker writes a JSON flag here to ask the host to restart the app;
    the host's restart probe consumes it so a single request fires once.
    """
    return Path(tempfile.gettempdir()) / "lingchu_restart.flag"


def _build_host_env(restart_flag_path: Path) -> dict[str, str]:
    """Build the child environment carrying lc-host runtime identifiers.

    Starts from the parent environment (with forced color overrides on a
    TTY) and marks the child as lc-hosted, telling it where to leave a
    restart flag.
    """
    env = _color_env() or dict(os.environ)
    env[_LC_HOSTED_ENV] = "1"
    env[_RESTART_FLAG_ENV] = str(restart_flag_path)
    return env


def _read_restart_flag(path: Path) -> str | None:
    """Read and consume the worker's restart flag, if present.

    The flag is a JSON file ``{"platform": ..., "account_id": ...}``.
    Returns ``"platform:account_id"`` when a valid flag was consumed; the
    file is deleted in every case so a single request cannot trigger
    repeated restarts. Returns ``None`` when no flag exists or it cannot
    be parsed (a stuck flag is removed rather than left to loop forever).
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        logger.warning(
            _("Failed to read restart flag {path}: {exc}").format(path=path, exc=exc)
        )
        path.unlink(missing_ok=True)
        return None
    try:
        data = json.loads(raw)
        platform = data["platform"]
        account_id = data["account_id"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning(
            _("Invalid restart flag {path}: {exc}").format(path=path, exc=exc)
        )
        path.unlink(missing_ok=True)
        return None
    path.unlink(missing_ok=True)
    return f"{platform}:{account_id}"


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
    try:
        async for raw in stream:
            text = raw.decode(errors="replace")
            if STARTUP_MARKER in text:
                marker_found.set()
            if sys.stdout is not None:
                sys.stdout.write(text)
                sys.stdout.flush()
    finally:
        # Close the underlying pipe transport so the Windows proactor event
        # loop does not warn about an unclosed transport at GC time (the
        # child already exited, so the pipe is at EOF).
        transport = getattr(stream, "_transport", None)
        if transport is not None and not transport.is_closing():
            transport.close()


async def _start_and_confirm(
    entry: list[str],
    cwd: Path,
    timeout: float,
    *,
    env: Mapping[str, str] | None = None,
) -> asyncio.subprocess.Process:
    """Spawn *entry*, forward output, and wait for a clean startup.

    *env* is the child environment (including lc-host runtime identifiers)
    to launch with. Raises :class:`ReloaderError` with the exit code when
    the child exits before the startup marker (a crash) or when startup
    times out (``124``).
    """
    marker_found = asyncio.Event()
    proc = await create_process(
        entry,
        cwd=cwd,
        env=env if env is not None else _color_env(),
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


async def _supervise(  # noqa: PLR0913 - 签名由宿主监督协议固定
    proc: asyncio.subprocess.Process,
    *,
    entry: list[str],
    cwd: Path,
    timeout: float,
    restart_flag_path: Path,
    base_env: dict[str, str] | None,
    interval: float = HEARTBEAT_INTERVAL,
) -> int:
    """Host the worker, polling its liveness every *interval* seconds.

    Each tick, after confirming the worker is still alive, the shared
    restart flag is probed. When the worker left a flag, the current
    worker is terminated and replaced by a fresh instance launched with
    ``LINGCHU_RESTART_BY`` set to the flag's ``platform:account_id``;
    supervision then continues with the new worker. Returns the final
    worker exit code.
    """
    while True:
        await asyncio.sleep(interval)
        if proc.returncode is not None:
            return proc.returncode
        restart_by = _read_restart_flag(restart_flag_path)
        if restart_by is None:
            continue
        logger.info(
            _("Restart requested by {restart_by}; restarting process.").format(
                restart_by=restart_by
            )
        )
        await terminate_process(proc)
        env = dict(base_env or os.environ)
        env[_RESTART_BY_ENV] = restart_by
        try:
            proc = await _start_and_confirm(entry, cwd, timeout, env=env)
        except ReloaderError as exc:
            return exc.exit_code


async def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout: float = DEFAULT_STARTUP_TIMEOUT,
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
    restart_flag_path = _resolve_restart_flag_path()
    host_env = _build_host_env(restart_flag_path)

    if reload:
        reloader = Reloader(
            startup_func=lambda: _start_and_confirm(entry, cwd, timeout, env=host_env),
            shutdown_func=terminate_process,
            cwd=cwd,
        )
        return await reloader.run()

    try:
        proc = await _start_and_confirm(entry, cwd, timeout, env=host_env)
    except ReloaderError as exc:
        return exc.exit_code

    return await _supervise(
        proc,
        entry=entry,
        cwd=cwd,
        timeout=timeout,
        restart_flag_path=restart_flag_path,
        base_env=host_env,
    )
