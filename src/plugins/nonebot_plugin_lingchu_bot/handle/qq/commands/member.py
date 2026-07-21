from importlib import import_module
from typing import Any

from arclet.alconna import Alconna, Args
from nonebot import require

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import At

from .triggers import COMMAND_TRIGGERS

_SET_MEMBER_CARD = COMMAND_TRIGGERS["set_member_card"]
_SET_MEMBER_TITLE = COMMAND_TRIGGERS["set_member_title"]
_SET_MEMBER_ADMIN = COMMAND_TRIGGERS["set_member_admin"]
_UNSET_MEMBER_ADMIN = COMMAND_TRIGGERS["unset_member_admin"]

set_group_member_card_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _SET_MEMBER_CARD.primary,
        Args["user", At | int]["card", str],
    ),
    aliases=_SET_MEMBER_CARD.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
set_group_member_special_title_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _SET_MEMBER_TITLE.primary,
        Args["user", At | int]["special_title", str],
    ),
    aliases=_SET_MEMBER_TITLE.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
set_group_member_admin_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _SET_MEMBER_ADMIN.primary,
        Args["user", At | int],
    ),
    aliases=_SET_MEMBER_ADMIN.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
unset_group_member_admin_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _UNSET_MEMBER_ADMIN.primary,
        Args["user", At | int],
    ),
    aliases=_UNSET_MEMBER_ADMIN.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "onebot11_set_group_member_card": "..adapters.onebot11.default.member",
    "onebot11_set_group_member_special_title": "..adapters.onebot11.default.member",
    "onebot11_set_group_member_admin": "..adapters.onebot11.default.member",
    "onebot11_unset_group_member_admin": "..adapters.onebot11.default.member",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
