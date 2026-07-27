import importlib
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq import (
    adapters as group_loader,
    commands as commands_loader,
)
from src.plugins.nonebot_plugin_lingchu_bot.platforms import (
    ProtocolImplementationInfo,
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

# The loader resolves registry ``module_path`` values (logical paths relative
# to the plugin root) to absolute Python import paths by prefixing
# ``_PLUGIN_ROOT``. In the test environment the plugin is loaded as
# ``src.plugins.nonebot_plugin_lingchu_bot``, so the absolute path for
# ``handle.qq.adapters.onebot11.default`` is
# ``src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default``.
_PLUGIN_ROOT = group_loader._PLUGIN_ROOT


@pytest.fixture(autouse=True)
def _reset_loader_cache() -> Any:
    """Clear the loader cache between tests so registry state stays fresh."""
    group_loader._loaded_handlers.clear()
    yield
    group_loader._loaded_handlers.clear()


def test_plugin_root_derived_from_loader_package() -> None:
    """``_PLUGIN_ROOT`` is the plugin's top-level package (no ``handle.`` suffix)."""
    assert _PLUGIN_ROOT
    assert ".handle." not in _PLUGIN_ROOT
    assert group_loader.__name__.partition(".handle.")[0] == _PLUGIN_ROOT


def test_shared_group_modules_do_not_import_concrete_adapters() -> None:
    for module_name in SHARED_GROUP_MODULES:
        assert "nonebot.adapters." not in (GROUP_DIR / module_name).read_text(
            encoding="utf-8"
        )


@pytest.mark.asyncio
async def test_group_loader_imports_only_onebot11_command_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """import_handle("command") loads every protocol module_path for the adapter.

    Module paths come from the registry (logical paths relative to the plugin
    root) and are prefixed with ``_PLUGIN_ROOT`` so ``import_module`` receives
    an absolute path — no relative-import ``package`` parameter.
    """
    loaded_modules: list[str] = []
    called_handlers: list[str] = []
    expected_path = f"{_PLUGIN_ROOT}.handle.qq.adapters.onebot11.default"

    def fake_import_module(module_path: str) -> Any:
        loaded_modules.append(module_path)

        async def fake_import_handle_for_module() -> None:
            called_handlers.append(module_path)

        return SimpleNamespace(import_handle=fake_import_handle_for_module)

    monkeypatch.setattr(
        group_loader, "resolve_enabled_adapters", lambda: {"~onebot.v11"}
    )
    monkeypatch.setattr(
        group_loader,
        "get_protocol_implementations",
        lambda adapter_id: (
            ProtocolImplementationInfo(
                protocol_id="default",
                adapter_id=adapter_id,
                display_name="Default",
                module_path="handle.qq.adapters.onebot11.default",
            ),
        ),
    )
    monkeypatch.setattr(group_loader, "import_module", fake_import_module)

    await group_loader.import_handle("command")

    assert loaded_modules == [expected_path]
    assert called_handlers == [expected_path]


@pytest.mark.asyncio
async def test_group_loader_skips_enabled_adapter_without_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the registry returns no implementations, no module is imported."""
    loaded_modules: list[str] = []

    def fake_import_module(module_path: str) -> Any:
        loaded_modules.append(module_path)
        return SimpleNamespace()

    monkeypatch.setattr(group_loader, "resolve_enabled_adapters", lambda: {"~unknown"})
    monkeypatch.setattr(
        group_loader,
        "get_protocol_implementations",
        lambda **_kwargs: (),
    )
    monkeypatch.setattr(group_loader, "import_module", fake_import_module)

    await group_loader.import_handle("command")

    assert loaded_modules == []


@pytest.mark.asyncio
async def test_group_loader_menu_kind_appends_menu_suffix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """import_handle("menu") loads default-protocol module_path + '.menu' only."""
    loaded_modules: list[str] = []
    expected_path = f"{_PLUGIN_ROOT}.handle.qq.adapters.onebot11.default.menu"

    def fake_import_module(module_path: str) -> Any:
        loaded_modules.append(module_path)

        async def fake_import_handle_for_module() -> None:
            return None

        return SimpleNamespace(import_handle=fake_import_handle_for_module)

    monkeypatch.setattr(
        group_loader, "resolve_enabled_adapters", lambda: {"~onebot.v11"}
    )
    monkeypatch.setattr(
        group_loader,
        "get_protocol_implementations",
        lambda adapter_id: (
            ProtocolImplementationInfo(
                protocol_id="default",
                adapter_id=adapter_id,
                display_name="Default",
                module_path="handle.qq.adapters.onebot11.default",
            ),
            ProtocolImplementationInfo(
                protocol_id="napcat",
                adapter_id=adapter_id,
                display_name="NapCat",
                module_path="handle.qq.adapters.onebot11.napcat",
            ),
        ),
    )
    monkeypatch.setattr(group_loader, "import_module", fake_import_module)

    await group_loader.import_handle("menu")

    assert loaded_modules == [expected_path]


def test_load_adapter_handlers_telegram_loads_real_module_not_shim() -> None:
    """Telegram command handlers load from the real module, not the deleted shim.

    The shim lived at ``handle.qq.adapters.telegram.default`` (a ``handle.qq``
    namespace path). With the registry-backed loader, the real module at
    ``handle.telegram.adapters.default`` is imported instead, and the deleted
    shim path is never touched.
    """
    # Clear any prior shim-shaped sys.modules entries so the assertion is
    # meaningful even if a previous test imported the shim path.
    for shim_path in (
        "handle.qq.adapters.telegram",
        "handle.qq.adapters.telegram.default",
        f"{_PLUGIN_ROOT}.handle.qq.adapters.telegram",
        f"{_PLUGIN_ROOT}.handle.qq.adapters.telegram.default",
    ):
        sys.modules.pop(shim_path, None)

    handlers = group_loader.load_adapter_handlers("~telegram", "command")

    telegram_default = importlib.import_module(
        f"{_PLUGIN_ROOT}.handle.telegram.adapters.default"
    )

    assert telegram_default.import_handle in handlers
    # The deleted shim path must not have been imported under either the
    # logical short form or the plugin-rooted absolute form.
    assert "handle.qq.adapters.telegram.default" not in sys.modules
    assert "handle.qq.adapters.telegram" not in sys.modules
    assert f"{_PLUGIN_ROOT}.handle.qq.adapters.telegram.default" not in sys.modules
    assert f"{_PLUGIN_ROOT}.handle.qq.adapters.telegram" not in sys.modules


def test_load_adapter_handlers_onebot_v11_command_returns_default_and_napcat() -> None:
    """~onebot.v11 command handlers include both default and napcat implementations."""
    handlers = group_loader.load_adapter_handlers("~onebot.v11", "command")

    assert len(handlers) == 2
    onebot_default = importlib.import_module(
        f"{_PLUGIN_ROOT}.handle.qq.adapters.onebot11.default"
    )
    onebot_napcat = importlib.import_module(
        f"{_PLUGIN_ROOT}.handle.qq.adapters.onebot11.napcat"
    )

    assert onebot_default.import_handle in handlers
    assert onebot_napcat.import_handle in handlers


def test_load_adapter_handlers_onebot_v11_menu_returns_default_menu_only() -> None:
    """~onebot.v11 menu handlers include only default.menu (napcat has no menu)."""
    handlers = group_loader.load_adapter_handlers("~onebot.v11", "menu")

    assert len(handlers) == 1
    onebot_default_menu = importlib.import_module(
        f"{_PLUGIN_ROOT}.handle.qq.adapters.onebot11.default.menu"
    )

    assert onebot_default_menu.import_handle in handlers


def test_load_adapter_handlers_caches_by_kind_and_adapter_id() -> None:
    """Loader caches results under f"{kind}:{adapter_id}" — second call returns the same tuple."""
    first_command = group_loader.load_adapter_handlers("~onebot.v11", "command")
    second_command = group_loader.load_adapter_handlers("~onebot.v11", "command")
    menu_handlers = group_loader.load_adapter_handlers("~onebot.v11", "menu")

    assert first_command is second_command
    assert menu_handlers is not first_command
    assert len(menu_handlers) == 1
