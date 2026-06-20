from importlib import import_module
from typing import Any

from arclet.alconna import Alconna, Args
from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import At

from .triggers import COMMAND_TRIGGERS

_MEMBER_MUTE = COMMAND_TRIGGERS["member_mute"]
_WHOLE_MUTE = COMMAND_TRIGGERS["whole_mute"]
_MEMBER_UNMUTE = COMMAND_TRIGGERS["member_unmute"]
_WHOLE_UNMUTE = COMMAND_TRIGGERS["whole_unmute"]

member_mute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _MEMBER_MUTE.primary,
        Args["user", At | int]["duration?", int, 60]["reason?", str, None],
    ),
    aliases=_MEMBER_MUTE.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
whole_mute_cmd: type[Matcher] = on_alconna(
    command=Alconna(
        _WHOLE_MUTE.primary,
    ),
    aliases=_WHOLE_MUTE.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
member_unmute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _MEMBER_UNMUTE.primary,
        Args["user", At | int],
    ),
    aliases=_MEMBER_UNMUTE.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
whole_unmute_cmd: type[Matcher] = on_alconna(
    command=Alconna(
        _WHOLE_UNMUTE.primary,
    ),
    aliases=_WHOLE_UNMUTE.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "onebot11_mute": "..adapters.onebot11.default.mute",
    "onebot11_whole_mute": "..adapters.onebot11.default.mute",
    "onebot11_unmute": "..adapters.onebot11.default.mute",
    "onebot11_whole_unmute": "..adapters.onebot11.default.mute",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
