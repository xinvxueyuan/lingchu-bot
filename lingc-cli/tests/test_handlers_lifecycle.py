"""Tests for lingc_cli.handlers.lifecycle."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from packaging.requirements import Requirement

from lingc_cli.handlers import lifecycle
from lingc_cli.handlers.doctor import Check

if TYPE_CHECKING:
    import pytest

DEFAULT = "nonebot-plugin-lingchu-bot"


class FakeExecutor:
    def __init__(self, *, cwd: Path) -> None:
        self.cwd = cwd
        self.calls: list[tuple[str, list[str]]] = []

    async def install(self, *packages: Requirement, extra_args=(), dev=False) -> None:
        del extra_args, dev
        self.calls.append(("install", [str(p) for p in packages]))

    async def uninstall(self, *packages: Requirement, extra_args=()) -> None:
        del extra_args
        self.calls.append(("uninstall", [str(p) for p in packages]))

    async def update(self, *packages: Requirement, extra_args=()) -> None:
        del packages, extra_args
        self.calls.append(("update", []))


def _patch_executor(monkeypatch: pytest.MonkeyPatch) -> FakeExecutor:
    fake = FakeExecutor(cwd=Path())
    monkeypatch.setattr(lifecycle, "probe_manager", lambda _cwd=None: ("uv", "uv"))
    monkeypatch.setattr(lifecycle, "UvEnvironmentExecutor", lambda **_kw: fake)
    monkeypatch.setattr(lifecycle, "PipEnvironmentExecutor", lambda **_kw: fake)
    return fake


async def test_install_default_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _patch_executor(monkeypatch)
    monkeypatch.setattr(lifecycle, "package_version", lambda _name: None)
    installed = await lifecycle.install(tmp_path)
    assert installed == [Requirement(DEFAULT)]
    assert fake.calls == [("install", [DEFAULT])]


async def test_install_idempotent_when_already_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _patch_executor(monkeypatch)
    monkeypatch.setattr(
        lifecycle, "package_version", lambda name: "0.1.0" if name == DEFAULT else None
    )
    installed = await lifecycle.install(tmp_path)
    assert installed == []
    assert fake.calls == []


async def test_install_explicit_packages_always_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _patch_executor(monkeypatch)
    monkeypatch.setattr(lifecycle, "package_version", lambda _name: "0.1.0")
    installed = await lifecycle.install(tmp_path, ["foo"])
    assert installed == [Requirement("foo")]
    assert fake.calls == [("install", ["foo"])]


async def test_uninstall_with_yes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _patch_executor(monkeypatch)
    removed = await lifecycle.uninstall(tmp_path, yes=True)
    assert removed == [Requirement(DEFAULT)]
    assert fake.calls == [("uninstall", [DEFAULT])]


async def test_uninstall_declined_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _patch_executor(monkeypatch)
    monkeypatch.setattr(lifecycle, "_confirm_uninstall", lambda _requirements: False)
    removed = await lifecycle.uninstall(tmp_path)
    assert removed == []
    assert fake.calls == []


async def test_uninstall_accepted_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _patch_executor(monkeypatch)
    monkeypatch.setattr(lifecycle, "_confirm_uninstall", lambda _requirements: True)
    removed = await lifecycle.uninstall(tmp_path)
    assert removed == [Requirement(DEFAULT)]
    assert fake.calls == [("uninstall", [DEFAULT])]


async def test_update_pulls_git_then_updates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _patch_executor(monkeypatch)
    (tmp_path / ".git").mkdir()
    pulled: list[Path] = []

    async def _git_pull(root: Path) -> None:
        pulled.append(root)

    monkeypatch.setattr(lifecycle, "_git_pull", _git_pull)
    await lifecycle.update(tmp_path)
    assert pulled == [tmp_path]
    assert fake.calls == [("update", [])]


async def test_update_ignores_git_pull_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _patch_executor(monkeypatch)
    (tmp_path / ".git").mkdir()

    async def _git_pull(_root: Path) -> None:
        raise RuntimeError

    monkeypatch.setattr(lifecycle, "_git_pull", _git_pull)
    await lifecycle.update(tmp_path)
    assert fake.calls == [("update", [])]


async def test_update_without_git_skips_pull(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _patch_executor(monkeypatch)
    pulled: list[Path] = []

    async def _git_pull(root: Path) -> None:
        pulled.append(root)

    monkeypatch.setattr(lifecycle, "_git_pull", _git_pull)
    await lifecycle.update(tmp_path)
    assert pulled == []
    assert fake.calls == [("update", [])]


async def test_repair_performs_all_missing_fixes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checks = [
        Check(name="core", status="missing", detail="x"),
        Check(name="config", status="missing", detail="x"),
        Check(name="migration", status="missing", detail="x"),
        Check(name="adapters", status="ok", detail="x"),
    ]
    monkeypatch.setattr(lifecycle, "run_checks", lambda _root: checks)
    installed: list[tuple[Path, object]] = []
    inited: list[Path] = []
    migrated: list[list[str]] = []

    async def _install(root: Path, packages=None):
        installed.append((root, packages))

    def _init(root: Path, *, force: bool = False) -> list[Path]:
        del force
        inited.append(root)
        return []

    def _run_db(args: list[str]) -> int:
        migrated.append(args)
        return 0

    monkeypatch.setattr(lifecycle, "install", _install)
    monkeypatch.setattr(lifecycle, "init_project", _init)
    monkeypatch.setattr(lifecycle, "run_db", _run_db)
    actions = await lifecycle.repair(tmp_path)
    assert actions == ["install", "init", "db upgrade"]
    assert installed == [(tmp_path, None)]
    assert inited == [tmp_path]
    assert migrated == [["upgrade"]]


async def test_repair_no_missing_no_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checks = [
        Check(name="core", status="ok", detail="2.3.3"),
        Check(name="adapters", status="warning", detail="none"),
    ]
    monkeypatch.setattr(lifecycle, "run_checks", lambda _root: checks)
    actions = await lifecycle.repair(tmp_path)
    assert actions == []
