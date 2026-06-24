from importlib import import_module
from typing import Any

from arclet.alconna import Alconna, Args
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import At

from .triggers import COMMAND_TRIGGERS

_PROTECT_MEMBER = COMMAND_TRIGGERS["protect_member"]
_GLOBAL_PROTECT_MEMBER = COMMAND_TRIGGERS["global_protect_member"]
_UNPROTECT_MEMBER = COMMAND_TRIGGERS["unprotect_member"]
_GLOBAL_UNPROTECT_MEMBER = COMMAND_TRIGGERS["global_unprotect_member"]

protect_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _PROTECT_MEMBER.primary,
        Args["user", At | int]["reason?", str, None],
    ),
    aliases=_PROTECT_MEMBER.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
global_protect_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _GLOBAL_PROTECT_MEMBER.primary,
        Args["user", At | int]["reason?", str, None],
    ),
    aliases=_GLOBAL_PROTECT_MEMBER.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
unprotect_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _UNPROTECT_MEMBER.primary,
        Args["user", At | int]["reason?", str, None],
    ),
    aliases=_UNPROTECT_MEMBER.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
global_unprotect_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _GLOBAL_UNPROTECT_MEMBER.primary,
        Args["user", At | int]["reason?", str, None],
    ),
    aliases=_GLOBAL_UNPROTECT_MEMBER.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "onebot11_protect_member": "..adapters.onebot11.default.protect",
    "onebot11_global_protect_member": "..adapters.onebot11.default.protect",
    "onebot11_unprotect_member": "..adapters.onebot11.default.protect",
    "onebot11_global_unprotect_member": "..adapters.onebot11.default.protect",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
