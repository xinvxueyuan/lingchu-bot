"""Runtime management commands for declared handle defaults."""

from importlib import import_module
from typing import Any

from arclet.alconna import Alconna, Args
from nonebot import require
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna

from .triggers import COMMAND_TRIGGERS

require("nonebot_plugin_alconna")

_MANAGE_HANDLE_DEFAULTS = COMMAND_TRIGGERS["manage_handle_defaults"]

manage_handle_defaults_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _MANAGE_HANDLE_DEFAULTS.primary,
        Args["handle?", str, None]["field?", str, None]["value?", str, None],
    ),
    aliases=_MANAGE_HANDLE_DEFAULTS.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "onebot11_manage_handle_defaults": "..adapters.onebot11.default.handle_defaults",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
