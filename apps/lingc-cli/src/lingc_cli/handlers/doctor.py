"""Environment checks for Lingc CLI (lc doctor).

Runs lightweight diagnostics against the project and its environment and
reports each as a structured Check. Never imports NoneBot or plugin internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from lingc_cli.handlers.env import list_adapters, package_version
from lingc_cli.i18n import _

if TYPE_CHECKING:
    from pathlib import Path

Status = Literal["ok", "warning", "missing"]

_REQUIRED_ENV_KEYS = ("NICKNAME", "DRIVER", "SUPERUSERS", "COMMAND_START")


@dataclass(frozen=True)
class Check:
    """A single diagnostic result."""

    name: str
    status: Status
    detail: str
    advice: str = field(default="")


def _read_env(root: Path) -> dict[str, str] | None:
    """Parse `.env` into key/value pairs, or None if the file is missing."""
    env_file = root / ".env"
    if not env_file.is_file():
        return None
    parsed: dict[str, str] = {}
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        parsed[key.strip()] = value.strip()
    return parsed


def run_checks(root: Path) -> list[Check]:
    """Run all diagnostics and return the resulting check list."""
    checks: list[Check] = []

    core = package_version("nonebot2")
    checks.append(
        Check(
            name="core",
            status="ok" if core else "missing",
            detail=core or _("NoneBot not installed"),
            advice=(
                _("Install NoneBot before starting the project.") if not core else ""
            ),
        )
    )

    adapters = list_adapters()
    if not core:
        adapter_status: Status = "missing"
        adapter_detail = _("adapters unavailable: core missing")
    elif adapters:
        adapter_status = "ok"
        adapter_detail = ", ".join(f"{name} {version}" for name, version in adapters)
    else:
        adapter_status = "warning"
        adapter_detail = _("no nonebot-adapter-* adapters detected")
    checks.append(
        Check(
            name="adapters",
            status=adapter_status,
            detail=adapter_detail,
            advice=(
                _("Install at least one adapter (e.g. nonebot-adapter-onebot).")
                if not adapters
                else ""
            ),
        )
    )

    env = _read_env(root)
    if env is None:
        checks.append(
            Check(
                name="config",
                status="missing",
                detail=_(".env missing"),
                advice=_("Run lc init to generate a minimal .env."),
            )
        )
    elif missing := [key for key in _REQUIRED_ENV_KEYS if key not in env]:
        checks.append(
            Check(
                name="config",
                status="warning",
                detail=f"missing required keys: {', '.join(missing)}",
                advice=_("Complete the required keys in .env."),
            )
        )
    else:
        checks.append(
            Check(name="config", status="ok", detail=_(".env parseable"), advice=""),
        )

    checks.append(
        Check(
            name="migration",
            status="warning",
            detail=_("check database migration status"),
            advice=_("Run database migrations if models changed."),
        )
    )

    return checks


def has_missing(checks: list[Check]) -> bool:
    """Return True if any check is in the missing state."""
    return any(check.status == "missing" for check in checks)


__all__ = ["Check", "Status", "has_missing", "run_checks"]
