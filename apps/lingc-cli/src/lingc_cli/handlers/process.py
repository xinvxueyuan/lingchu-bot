"""Low-level asyncio subprocess helpers."""

from __future__ import annotations

import asyncio
import subprocess
from typing import TYPE_CHECKING

from lingc_cli.consts import WINDOWS

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


async def create_process(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    stdout: int | None = None,
    stderr: int | None = None,
) -> asyncio.subprocess.Process:
    """Spawn ``cmd`` as an asyncio subprocess, isolated in its own process group.

    On Windows the child is created with ``CREATE_NEW_PROCESS_GROUP``; on
    POSIX it gets its own session via ``start_new_session``. Both let a later
    SIGINT/SIGTERM be delivered to the child's whole process tree cleanly.
    ``stdout``/``stderr`` accept any ``asyncio.subprocess`` constant (``PIPE``
    to capture output, ``None`` to inherit the terminal).
    """
    process_env = dict(env) if env is not None else None
    if WINDOWS:
        return await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            env=process_env,
            stdout=stdout,
            stderr=stderr,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    return await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        env=process_env,
        stdout=stdout,
        stderr=stderr,
        start_new_session=True,
    )


async def await_process(proc: asyncio.subprocess.Process) -> int:
    """Wait for ``proc`` to finish and return its exit code."""
    return await proc.wait()
