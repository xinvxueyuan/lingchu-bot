"""Load the explicitly supported nested subplugins through NoneBot."""

from typing import Final

import nonebot
from nonebot.plugin import Plugin

_SUBPLUGIN_NAMES: Final = ("llm_chat", "novelai_image")
SUBPLUGIN_MODULES: Final = tuple(f"{__package__}.{name}" for name in _SUBPLUGIN_NAMES)


def load_subplugins() -> set[Plugin]:
    """Load declared nested subplugins through NoneBot's plugin manager."""
    return nonebot.load_all_plugins(SUBPLUGIN_MODULES, ())
