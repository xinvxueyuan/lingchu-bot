"""Verify Lingchu CLI entry points from the built wheel in isolated environments."""

from __future__ import annotations

from configparser import ConfigParser
from email.parser import BytesParser
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

_DISTRIBUTION_PREFIX = "nonebot_plugin_lingchu_bot-"
_CONSOLE_ENTRY = "_lingchu_bot_cli.app:main"
_NB_PLUGIN_ENTRY = "_lingchu_bot_cli.nb_plugin:install"


def _only_wheel(dist_dir: Path) -> Path:
    wheels = tuple(dist_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(
            f"expected exactly one wheel in {dist_dir}, found {len(wheels)}"
        )
    return wheels[0].resolve()


def _metadata_files(archive: ZipFile) -> tuple[str, str]:
    names = archive.namelist()
    entry_points = [
        name for name in names if name.endswith(".dist-info/entry_points.txt")
    ]
    metadata = [name for name in names if name.endswith(".dist-info/METADATA")]
    if len(entry_points) != 1 or len(metadata) != 1:
        raise RuntimeError("wheel must contain one entry_points.txt and one METADATA")
    return entry_points[0], metadata[0]


def _verify_metadata(wheel: Path) -> None:
    with ZipFile(wheel) as archive:
        entry_name, metadata_name = _metadata_files(archive)
        parser = ConfigParser()
        parser.read_string(archive.read(entry_name).decode())
        if parser.get("console_scripts", "lingchu") != _CONSOLE_ENTRY:
            raise RuntimeError("unexpected lingchu console entry point")
        if parser.get("nb", "lingchu") != _NB_PLUGIN_ENTRY:
            raise RuntimeError("unexpected lingchu nb plugin entry point")
        metadata = BytesParser().parsebytes(archive.read(metadata_name))

    requirements = metadata.get_all("Requires-Dist", [])
    normalized = tuple(requirement.lower() for requirement in requirements)
    if not any(requirement.startswith("typer") for requirement in normalized):
        raise RuntimeError("wheel does not declare Typer as a runtime dependency")
    if any(requirement.startswith("nb-cli") for requirement in normalized):
        raise RuntimeError("wheel must not declare nb-cli as a runtime dependency")


def _isolated_environment() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("LINGCHU_", "LOCALSTORE_"))
        and key not in {"ENVIRONMENT", "PYTHONPATH", "UV_PROJECT_ENVIRONMENT"}
    }
    env["ENVIRONMENT"] = "test"
    return env


def _run(
    *args: str,
    cwd: Path,
    expected_code: int = 0,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        check=False,
        cwd=cwd,
        env=_isolated_environment(),
        capture_output=True,
        text=True,
    )
    if result.returncode != expected_code:
        raise RuntimeError(
            f"command returned {result.returncode}, expected {expected_code}: {args!r}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def _wheel_command(wheel: Path, *args: str) -> tuple[str, ...]:
    return (
        "uv",
        "run",
        "--no-project",
        "--with",
        str(wheel),
        "--",
        "lingchu",
        *args,
    )


def _verify_config_commands(wheel: Path, smoke_root: Path) -> None:
    project_dir = smoke_root / "project"
    config_dir = smoke_root / "localstore" / "config"
    project_dir.mkdir()
    config_dir.mkdir(parents=True)

    project_file = project_dir / "pyproject.toml"
    project_file.write_text("[project]\nname = 'wheel-smoke'\nversion = '0'\n")
    dotenv_file = project_dir / ".env"
    dotenv_file.write_text(
        "LINGCHU_MESSAGE_STORE_RETENTION_DAYS=-999\n"
        "LINGCHU_WHEEL_SMOKE_SENTINEL=must-not-be-read\n",
        encoding="utf-8",
    )
    project_snapshot = {
        path.relative_to(project_dir): path.read_bytes()
        for path in project_dir.iterdir()
    }

    config_file = config_dir / "runtime-overrides.toml"
    init_command = _wheel_command(wheel, "config", "init", "--path", str(config_file))
    first_init = _run(*init_command, cwd=project_dir)
    if "created:" not in first_init.stdout or not config_file.is_file():
        raise RuntimeError("config init did not create the requested config file")
    first_config = config_file.read_bytes()
    if b"must-not-be-read" in first_config or b"-999" in first_config:
        raise RuntimeError("config init read values from the temporary .env file")

    second_init = _run(*init_command, cwd=project_dir)
    if "exists:" not in second_init.stdout:
        raise RuntimeError("repeated config init did not report the existing file")
    if config_file.read_bytes() != first_config:
        raise RuntimeError("repeated config init modified the existing config file")

    validate_command = _wheel_command(
        wheel, "config", "validate", "--path", str(config_file)
    )
    valid = _run(*validate_command, cwd=project_dir)
    if "valid:" not in valid.stdout or config_file.read_bytes() != first_config:
        raise RuntimeError("config validate was not a successful read-only operation")

    invalid_file = config_dir / "invalid.toml"
    invalid_file.write_text(
        'permission_platform_runtime_passthrough = "invalid"\n', encoding="utf-8"
    )
    invalid_before = invalid_file.read_bytes()
    invalid = _run(
        *_wheel_command(wheel, "config", "validate", "--path", str(invalid_file)),
        cwd=project_dir,
        expected_code=1,
    )
    if "invalid configuration file" not in invalid.stderr:
        raise RuntimeError("invalid config validation did not report a domain error")
    if invalid_file.read_bytes() != invalid_before:
        raise RuntimeError("invalid config validation modified the input file")

    schema_command = _wheel_command(
        wheel, "schema", "install", "--config-dir", str(config_dir)
    )
    first_schema = _run(*schema_command, cwd=project_dir)
    schema_file = config_dir / "runtime-overrides.schema.json"
    if "installed:" not in first_schema.stdout or not schema_file.is_file():
        raise RuntimeError("schema install did not create the requested schema")
    schema_bytes = schema_file.read_bytes()
    json.loads(schema_bytes)
    _run(*schema_command, cwd=project_dir)
    if schema_file.read_bytes() != schema_bytes:
        raise RuntimeError("repeated schema install changed the generated schema")
    if tuple(config_dir.glob("*.tmp")):
        raise RuntimeError("configuration commands left temporary files behind")

    current_project = {
        path.relative_to(project_dir): path.read_bytes()
        for path in project_dir.iterdir()
    }
    if current_project != project_snapshot:
        raise RuntimeError(
            "configuration commands wrote into the temporary project cwd"
        )


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    wheel = _only_wheel(project_root / "dist")
    if not wheel.name.startswith(_DISTRIBUTION_PREFIX):
        raise RuntimeError(f"unexpected wheel: {wheel.name}")
    _verify_metadata(wheel)
    with TemporaryDirectory(prefix="lingchu-wheel-smoke-") as temp_dir:
        smoke_root = Path(temp_dir)
        (smoke_root / "pyproject.toml").write_text(
            "[tool.nonebot]\nplugin_dirs = []\n\n[tool.nonebot.plugins]\n"
            '"@local" = []\n\n[tool.nonebot.adapters]\n'
            '"@local" = []\n',
            encoding="utf-8",
        )
        _run(
            "uv",
            "run",
            "--no-project",
            "--with",
            str(wheel),
            "--",
            "lingchu",
            "--help",
            cwd=smoke_root,
        )
        _run(
            "uv",
            "run",
            "--no-project",
            "--with",
            "nb-cli==1.7.4",
            "--with",
            str(wheel),
            "--",
            "nb",
            "lingchu",
            "--help",
            cwd=smoke_root,
        )
        nb_prefix = (
            "uv",
            "run",
            "--no-project",
            "--with",
            "nb-cli==1.7.4",
            "--with",
            str(wheel),
            "--",
            "nb",
            "lingchu",
        )
        missing = _run(
            *nb_prefix,
            "config",
            "validate",
            "--path",
            str(smoke_root / "missing.toml"),
            cwd=smoke_root,
            expected_code=1,
        )
        if "missing configuration file" not in missing.stderr:
            raise RuntimeError("nb plugin did not preserve the Typer domain error")
        doctor = _run(*nb_prefix, "doctor", "--json", cwd=smoke_root)
        json.loads(doctor.stdout)
        _verify_config_commands(wheel, smoke_root)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"wheel entry-point check failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
