"""Typer application shared by the console and nb-cli script entry points."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
from typing import Annotated, Never

import typer

from .config_files import (
    CONFIG_FILENAME,
    LLM_CONFIG_FILENAME,
    ConfigFileError,
    initialize_config,
    initialize_llm_config,
    install_config_schema,
    validate_config,
)

_DISTRIBUTION_NAME = "nonebot-plugin-lingchu-bot"
_LOCAL_VERSION = "0.0.0+local"
_LOCALSTORE_PLUGIN_NAME = "nonebot_plugin_lingchu_bot"
_DOCTOR_DISTRIBUTIONS = (
    "nonebot2",
    "nonebot-adapter-onebot",
    "nonebot-plugin-localstore",
    _DISTRIBUTION_NAME,
)

app = typer.Typer(
    help="Lingchu Bot operations",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)
config_app = typer.Typer(help="Inspect and manage Lingchu Bot configuration.")
schema_app = typer.Typer(help="Install Lingchu Bot configuration schemas.")
app.add_typer(config_app, name="config")
app.add_typer(schema_app, name="schema")


def _installed_version() -> str:
    try:
        return version(_DISTRIBUTION_NAME)
    except PackageNotFoundError:
        return _LOCAL_VERSION


def _version_callback(value: object) -> None:
    if value:
        typer.echo(_installed_version())
        raise typer.Exit


def _ensure_nonebot_initialized() -> None:
    import nonebot

    try:
        nonebot.get_driver()
    except ValueError:
        localstore_options = {
            name.lower(): value
            for name in (
                "LOCALSTORE_CONFIG_DIR",
                "LOCALSTORE_DATA_DIR",
                "LOCALSTORE_CACHE_DIR",
                "LOCALSTORE_USE_CWD",
            )
            if (value := os.environ.get(name)) is not None
        }
        nonebot.init(
            _env_file=None,
            log_level="WARNING",
            **localstore_options,
        )


def _localstore_paths() -> tuple[tuple[str, Path], ...]:
    _ensure_nonebot_initialized()
    from nonebot_plugin_localstore import get_cache_dir, get_config_dir, get_data_dir

    return (
        ("config", get_config_dir(_LOCALSTORE_PLUGIN_NAME)),
        ("data", get_data_dir(_LOCALSTORE_PLUGIN_NAME)),
        ("cache", get_cache_dir(_LOCALSTORE_PLUGIN_NAME)),
    )


@app.callback()
def root(
    *,
    version_requested: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the installed Lingchu Bot version and exit.",
        ),
    ] = False,
) -> None:
    """Run Lingchu Bot operational commands."""
    _ = version_requested


@config_app.command("path")
def config_path() -> None:
    """Show localstore-owned Lingchu Bot directories."""
    for label, path in _localstore_paths():
        typer.echo(f"{label}: {path}")


def _config_file(path: Path | None) -> Path:
    if path is not None:
        return path
    return dict(_localstore_paths())["config"] / CONFIG_FILENAME


def _config_dir(path: Path | None) -> Path:
    if path is not None:
        return path
    return dict(_localstore_paths())["config"]


def _fail(error: ConfigFileError | OSError) -> Never:
    typer.echo(str(error), err=True)
    raise typer.Exit(1) from error


@config_app.command("init")
def config_init(
    path: Annotated[Path | None, typer.Option("--path")] = None,
    *,
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Create explicit localstore TOML defaults without overwriting by default."""
    target = _config_file(path)
    try:
        created = initialize_config(target, force=force)
        llm_target = target.parent / LLM_CONFIG_FILENAME
        llm_created = initialize_llm_config(llm_target)
    except OSError as error:
        _fail(error)
    typer.echo(f"created: {target}" if created else f"exists: {target}")
    typer.echo(f"created: {llm_target}" if llm_created else f"exists: {llm_target}")


@config_app.command("validate")
def config_validate(
    path: Annotated[Path | None, typer.Option("--path")] = None,
) -> None:
    """Validate the mutable runtime TOML without environment overrides."""
    target = _config_file(path)
    try:
        validate_config(target)
    except ConfigFileError as error:
        _fail(error)
    typer.echo(f"valid: {target}")


@schema_app.command("install")
def schema_install(
    config_dir: Annotated[Path | None, typer.Option("--config-dir")] = None,
) -> None:
    """Install the JSON Schema generated from the mutable runtime model."""
    try:
        target = install_config_schema(_config_dir(config_dir))
    except OSError as error:
        _fail(error)
    typer.echo(f"installed: {target}")


@app.command()
def doctor(
    *,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Report required runtime component health without loading the bot."""
    checks: list[dict[str, str | None]] = []
    for distribution in _DOCTOR_DISTRIBUTIONS:
        try:
            installed = version(distribution)
        except PackageNotFoundError:
            checks.append({"name": distribution, "status": "missing", "version": None})
        else:
            checks.append({"name": distribution, "status": "ok", "version": installed})
    healthy = all(check["status"] == "ok" for check in checks)
    if json_output:
        typer.echo(json.dumps({"ok": healthy, "checks": checks}, sort_keys=False))
    else:
        for check in checks:
            suffix = check["version"] if check["version"] is not None else "missing"
            typer.echo(f"{check['name']}: {suffix}")
    if not healthy:
        raise typer.Exit(2)


def main() -> None:
    """Run the standalone console entry point."""
    app()
