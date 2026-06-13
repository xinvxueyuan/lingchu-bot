from importlib import import_module
from typing import Any

from arclet.alconna import Alconna, Args
from nonebot import logger
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import At

from ....i18n import _async as _
from .command_triggers import COMMAND_TRIGGERS

_SET_MEMBER_CARD = COMMAND_TRIGGERS["set_member_card"]
_SET_MEMBER_TITLE = COMMAND_TRIGGERS["set_member_title"]
_SET_MEMBER_ADMIN = COMMAND_TRIGGERS["set_member_admin"]
_UNSET_MEMBER_ADMIN = COMMAND_TRIGGERS["unset_member_admin"]
_KICK_MEMBER = COMMAND_TRIGGERS["kick_member"]

set_group_member_card_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(_SET_MEMBER_CARD.primary, Args["user", At]["card", str]),
    aliases=_SET_MEMBER_CARD.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
set_group_member_special_title_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(_SET_MEMBER_TITLE.primary, Args["user", At]["special_title", str]),
    aliases=_SET_MEMBER_TITLE.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
set_group_member_admin_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(_SET_MEMBER_ADMIN.primary, Args["user", At]["is_set?", bool, True]),
    aliases=_SET_MEMBER_ADMIN.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
unset_group_member_admin_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(_UNSET_MEMBER_ADMIN.primary, Args["user", At]),
    aliases=_UNSET_MEMBER_ADMIN.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
kick_group_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _KICK_MEMBER.primary,
        Args["user", At]["reject_add_request?", bool, False],
    ),
    aliases=_KICK_MEMBER.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "milkybot_set_group_member_card": "..milky.v1_2.default.group.member",
    "milkybot_set_group_member_special_title": "..milky.v1_2.default.group.member",
    "milkybot_set_group_member_admin": "..milky.v1_2.default.group.member",
    "milkybot_unset_group_member_admin": "..milky.v1_2.default.group.member",
    "milkybot_kick_group_member": "..milky.v1_2.default.group.member",
    "onebot11_set_group_member_card": "..onebot.v11.default.group.member",
    "onebot11_set_group_member_special_title": "..onebot.v11.default.group.member",
    "onebot11_set_group_member_admin": "..onebot.v11.default.group.member",
    "onebot11_unset_group_member_admin": "..onebot.v11.default.group.member",
    "onebot11_kick_group_member": "..onebot.v11.default.group.member",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value


async def import_handle() -> Any:
    logger.debug(await _("导入member处理器..."))
