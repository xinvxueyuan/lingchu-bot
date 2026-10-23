from importlib import import_module
from typing import Any

from arclet.alconna import Alconna
from nonebot import require
from nonebot.internal.matcher.matcher import Matcher

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import on_alconna

from .triggers import COMMAND_TRIGGERS

_WEBUI_START = COMMAND_TRIGGERS["webui_start"]

webui_start_cmd: type[Matcher] = on_alconna(
    command=Alconna(_WEBUI_START.primary),
    aliases=_WEBUI_START.aliases,
    priority=805,
    block=True,
    use_cmd_sep=False,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "onebot11_webui_start": "..adapters.onebot11.default.webui",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
