from importlib import import_module
from typing import Any

from arclet.alconna import Alconna, Args, Nargs
from nonebot import require

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna

from .triggers import COMMAND_TRIGGERS

_CHAT = COMMAND_TRIGGERS["chat"]


chat_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(_CHAT.primary, Args["text", Nargs(str)]),
    aliases=_CHAT.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "onebot11_chat": "..adapters.onebot11.default.chat",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
