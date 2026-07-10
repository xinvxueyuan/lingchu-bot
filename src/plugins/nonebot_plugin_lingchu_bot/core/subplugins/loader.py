"""Discover and load removable nested subplugins."""

from pathlib import Path
from typing import Final

import nonebot
from nonebot.plugin import Plugin

SUBPLUGINS_ROOT: Final = Path(__file__).parent


def discover_subplugin_dirs(root: Path = SUBPLUGINS_ROOT) -> tuple[Path, ...]:
    """Return public package directories in deterministic order."""
    return tuple(
        path
        for path in sorted(root.iterdir())
        if path.is_dir()
        and not path.name.startswith("_")
        and (path / "__init__.py").is_file()
    )


def load_subplugins() -> set[Plugin]:
    """Load every discovered nested subplugin."""
    return {
        plugin
        for path in discover_subplugin_dirs()
        if (plugin := nonebot.load_plugin(path)) is not None
    }
