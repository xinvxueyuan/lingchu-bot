from importlib import import_module
from typing import Any

from arclet.alconna import Alconna, Args
from nonebot import require
from nonebot.internal.matcher.matcher import Matcher

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import At

from .triggers import COMMAND_TRIGGERS

_MEMBER_MUTE = COMMAND_TRIGGERS["member_mute"]
_SET_DEFAULT_MUTE_DURATION = COMMAND_TRIGGERS["set_default_mute_duration"]
_WHOLE_MUTE = COMMAND_TRIGGERS["whole_mute"]
_MEMBER_UNMUTE = COMMAND_TRIGGERS["member_unmute"]
_WHOLE_UNMUTE = COMMAND_TRIGGERS["whole_unmute"]
_RECALL_MESSAGE = COMMAND_TRIGGERS["recall_message"]

member_mute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _MEMBER_MUTE.primary,
        Args["user", At | int]["duration?", int, None]["reason?", str, None],
    ),
    aliases=_MEMBER_MUTE.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
set_default_mute_duration_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _SET_DEFAULT_MUTE_DURATION.primary,
        Args["duration", int],
    ),
    aliases=_SET_DEFAULT_MUTE_DURATION.aliases,
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
recall_message_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _RECALL_MESSAGE.primary,
        Args["target?", At | int, None]["count?", int, None],
    ),
    aliases=_RECALL_MESSAGE.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "onebot11_mute": "..adapters.onebot11.default.mute",
    "onebot11_set_default_mute_duration": "..adapters.onebot11.default.mute",
    "onebot11_whole_mute": "..adapters.onebot11.default.mute",
    "onebot11_unmute": "..adapters.onebot11.default.mute",
    "onebot11_whole_unmute": "..adapters.onebot11.default.mute",
    "onebot11_recall_message": "..adapters.onebot11.default.mute",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
