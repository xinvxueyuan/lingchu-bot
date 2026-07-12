from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq import (
    adapters as group_loader,
    commands as commands_loader,
)

GROUP_DIR = Path(commands_loader.__file__).parent
SHARED_GROUP_MODULES = (
    "announcement.py",
    "common.py",
    "lifecycle.py",
    "member.py",
    "mute.py",
    "profile.py",
)


def test_group_loader_registry_uses_adapter_entry_modules() -> None:
    assert group_loader._ADAPTER_MODULES == {
        "~onebot.v11": (
            ".onebot11.default",
            ".onebot11.napcat",
        ),
    }


def test_shared_group_modules_do_not_import_concrete_adapters() -> None:
    for module_name in SHARED_GROUP_MODULES:
        assert "nonebot.adapters." not in (GROUP_DIR / module_name).read_text(
            encoding="utf-8"
        )


@pytest.mark.asyncio
async def test_group_loader_imports_only_onebot11_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded_modules: list[str] = []
    called_handlers: list[str] = []

    def fake_import_module(module_path: str, _package: str | None = None) -> Any:
        loaded_modules.append(module_path)

        async def fake_import_handle_for_module() -> None:
            called_handlers.append(module_path)

        return SimpleNamespace(import_handle=fake_import_handle_for_module)

    monkeypatch.setattr(
        group_loader, "resolve_enabled_adapters", lambda: {"~onebot.v11"}
    )
    monkeypatch.setattr(
        group_loader,
        "_ADAPTER_MODULES",
        {
            "~onebot.v11": (".onebot11.default",),
        },
    )
    monkeypatch.setattr(group_loader, "import_module", fake_import_module)
    group_loader._loaded_handlers.clear()

    await group_loader.import_handle()

    assert loaded_modules == [".onebot11.default"]
    assert called_handlers == [".onebot11.default"]


@pytest.mark.asyncio
async def test_group_loader_skips_enabled_adapter_without_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded_modules: list[str] = []

    def fake_import_module(module_path: str, _package: str | None = None) -> Any:
        loaded_modules.append(module_path)
        return SimpleNamespace()

    monkeypatch.setattr(group_loader, "resolve_enabled_adapters", lambda: {"~unknown"})
    monkeypatch.setattr(
        group_loader,
        "_ADAPTER_MODULES",
        {
            "~onebot.v11": (".onebot11.default",),
        },
    )
    monkeypatch.setattr(group_loader, "import_module", fake_import_module)
    group_loader._loaded_handlers.clear()

    await group_loader.import_handle()

    assert loaded_modules == []
