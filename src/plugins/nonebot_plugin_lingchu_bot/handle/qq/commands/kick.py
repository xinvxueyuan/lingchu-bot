from importlib import import_module
from typing import Any

from arclet.alconna import Alconna, Args
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import At

from .triggers import COMMAND_TRIGGERS

_KICK_MEMBER = COMMAND_TRIGGERS["kick_member"]

kick_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _KICK_MEMBER.primary,
        Args["user", At | int]["reason?", str, None],
    ),
    aliases=_KICK_MEMBER.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "onebot11_kick_member": "..adapters.onebot11.default.kick",
    "milkybot_kick_member": "..adapters.milky.default.kick",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
