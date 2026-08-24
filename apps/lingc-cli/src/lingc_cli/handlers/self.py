"""Self-update for Lingc CLI (lc self-update).

Probes how lingc-cli was installed (uv tool vs pipx) and upgrades it in
place, falling back to instructing a manual upgrade when neither is found.
"""

from __future__ import annotations

import asyncio
import shutil

from lingc_cli.exceptions import ProcessExecutionError
from lingc_cli.i18n import _

_DISTRIBUTION = "lingc-cli"


async def _run(*command: str) -> None:
    """Spawn a subprocess and surface a non-zero exit as an error."""
    process = await asyncio.create_subprocess_exec(*command)
    if await process.wait() != 0:
        message = _("Failed to run: {cmd}").format(cmd=" ".join(command))
        raise ProcessExecutionError(message)


async def self_update() -> str:
    """Upgrade lingc-cli via its installer.

    Returns:
        The installation method used: "uv", "pipx", or "manual" when neither
        tool is available.
    """
    if shutil.which("uv") is not None:
        await _run("uv", "tool", "upgrade", _DISTRIBUTION)
        return "uv"
    if shutil.which("pipx") is not None:
        await _run("pipx", "upgrade", _DISTRIBUTION)
        return "pipx"
    return "manual"


__all__ = ["self_update"]
