from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

from packaging.requirements import Requirement
import pytest

from lingc_cli.core import config, environment
from lingc_cli.core.environment import (
    EnvironmentExecutor,
    PipEnvironmentExecutor,
    UvEnvironmentExecutor,
    all_managers,
    probe_manager,
)
from lingc_cli.exceptions import ProcessExecutionError

if TYPE_CHECKING:
    from pathlib import Path


def _fake_process(exit_code: int = 0) -> AsyncMock:
    process = AsyncMock()
    process.wait.return_value = exit_code
    return process


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    return tmp_path


def test_probe_manager_infers_uv_when_lock_present(project_root: Path) -> None:
    (project_root / "uv.lock").write_text("", encoding="utf-8")
    with patch("lingc_cli.core.environment.which", return_value=None):
        assert probe_manager(project_root) == ("uv", "pip")
    with patch("lingc_cli.core.environment.which", return_value="/usr/bin/uv"):
        assert probe_manager(project_root) == ("uv", "uv")


def test_probe_manager_falls_back_to_pip_without_lock(project_root: Path) -> None:
    assert probe_manager(project_root) == ("pip", "pip")


def test_all_managers_always_includes_pip() -> None:
    with patch("lingc_cli.core.environment.which", return_value=None):
        assert all_managers() == ["pip"]
    with patch("lingc_cli.core.environment.which", return_value="/usr/bin/uv"):
        assert all_managers() == ["uv", "pip"]


@pytest.mark.asyncio
async def test_uv_install_argv(project_root: Path) -> None:
    executor = UvEnvironmentExecutor(cwd=project_root, executable="uv")
    process = _fake_process()
    with patch(
        "lingc_cli.core.environment.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=process),
    ) as mock_exec:
        await executor.install(Requirement("foobar>=2"), extra_args=("--extra",))
    mock_exec.assert_awaited_once_with(
        "uv", "add", "foobar>=2", "--extra", cwd=project_root
    )


@pytest.mark.asyncio
async def test_uv_install_dev_appends_flag(project_root: Path) -> None:
    executor = UvEnvironmentExecutor(cwd=project_root, executable="uv")
    with patch(
        "lingc_cli.core.environment.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=_fake_process()),
    ) as mock_exec:
        await executor.install(Requirement("foobar"), dev=True)
    mock_exec.assert_awaited_once_with("uv", "add", "foobar", "--dev", cwd=project_root)


@pytest.mark.asyncio
async def test_uv_update_argv(project_root: Path) -> None:
    executor = UvEnvironmentExecutor(cwd=project_root, executable="uv")
    with patch(
        "lingc_cli.core.environment.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=_fake_process()),
    ) as mock_exec:
        await executor.update(Requirement("foobar>=2"))
    mock_exec.assert_awaited_once_with(
        "uv", "add", "--upgrade", "foobar>=2", cwd=project_root
    )


@pytest.mark.asyncio
async def test_uv_uninstall_argv(project_root: Path) -> None:
    executor = UvEnvironmentExecutor(cwd=project_root, executable="uv")
    with patch(
        "lingc_cli.core.environment.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=_fake_process()),
    ) as mock_exec:
        await executor.uninstall(Requirement("foobar"))
    mock_exec.assert_awaited_once_with("uv", "remove", "foobar", cwd=project_root)


@pytest.mark.asyncio
async def test_uv_sync_argv(project_root: Path) -> None:
    executor = UvEnvironmentExecutor(cwd=project_root, executable="uv")
    with patch(
        "lingc_cli.core.environment.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=_fake_process()),
    ) as mock_exec:
        await executor.sync()
    mock_exec.assert_awaited_once_with("uv", "sync", cwd=project_root)


@pytest.mark.asyncio
async def test_pip_install_uses_resolved_python_by_default(project_root: Path) -> None:
    config.set_python("my-python")
    try:
        executor = PipEnvironmentExecutor(cwd=project_root)
        assert executor.executable == "my-python"
        with patch(
            "lingc_cli.core.environment.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=_fake_process()),
        ) as mock_exec:
            await executor.install(Requirement("foobar>=2"))
        mock_exec.assert_awaited_once_with(
            "my-python", "-m", "pip", "install", "foobar>=2", cwd=project_root
        )
    finally:
        config.set_python(None)


@pytest.mark.asyncio
async def test_pip_update_argv(project_root: Path) -> None:
    executor = PipEnvironmentExecutor(cwd=project_root, executable="python")
    with patch(
        "lingc_cli.core.environment.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=_fake_process()),
    ) as mock_exec:
        await executor.update(Requirement("foobar"))
    mock_exec.assert_awaited_once_with(
        "python", "-m", "pip", "install", "--upgrade", "foobar", cwd=project_root
    )


@pytest.mark.asyncio
async def test_pip_uninstall_argv(project_root: Path) -> None:
    executor = PipEnvironmentExecutor(cwd=project_root, executable="python")
    with patch(
        "lingc_cli.core.environment.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=_fake_process()),
    ) as mock_exec:
        await executor.uninstall(Requirement("foobar"))
    mock_exec.assert_awaited_once_with(
        "python", "-m", "pip", "uninstall", "foobar", cwd=project_root
    )


@pytest.mark.asyncio
async def test_pip_sync_argv(project_root: Path) -> None:
    executor = PipEnvironmentExecutor(cwd=project_root, executable="python")
    with patch(
        "lingc_cli.core.environment.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=_fake_process()),
    ) as mock_exec:
        await executor.sync()
    mock_exec.assert_awaited_once_with(
        "python", "-m", "pip", "install", "-e", ".", cwd=project_root
    )


@pytest.mark.asyncio
async def test_non_zero_exit_raises_process_execution_error(project_root: Path) -> None:
    executor = UvEnvironmentExecutor(cwd=project_root, executable="uv")
    with (
        patch(
            "lingc_cli.core.environment.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=_fake_process(exit_code=3)),
        ),
        pytest.raises(ProcessExecutionError),
    ):
        await executor.sync()


def test_exported_names() -> None:
    for name in (
        "EnvironmentExecutor",
        "UvEnvironmentExecutor",
        "PipEnvironmentExecutor",
        "probe_manager",
        "all_managers",
    ):
        assert hasattr(environment, name)
    assert EnvironmentExecutor.__abstractmethods__ >= {
        "sync",
        "install",
        "update",
        "uninstall",
    }
