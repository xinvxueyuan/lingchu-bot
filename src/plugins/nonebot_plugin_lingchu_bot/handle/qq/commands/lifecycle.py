from importlib import import_module
from typing import Any

from arclet.alconna import Alconna
from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import on_alconna

from .triggers import COMMAND_TRIGGERS

_LEAVE_GROUP = COMMAND_TRIGGERS["leave_group"]

quit_group_cmd: type[Matcher] = on_alconna(
    command=Alconna(_LEAVE_GROUP.primary),
    aliases=_LEAVE_GROUP.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "onebot11_quit_group": "..adapters.onebot11.default.lifecycle",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
