from importlib import import_module
from typing import Any

from arclet.alconna import Alconna, Args
from nonebot import logger
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import At

from ....i18n import _async as _

set_group_member_card_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("设置群名片", Args["user", At]["card", str]),
    aliases={"改群名片", "修改群名片", "设置成员名片"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
set_group_member_special_title_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("设置群头衔", Args["user", At]["special_title", str]),
    aliases={"设置专属头衔", "设置群成员专属头衔", "改群头衔"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
set_group_member_admin_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("设置群管理员", Args["user", At]["is_set?", bool, True]),
    aliases={"设置管理员", "任命群管理员"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
unset_group_member_admin_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("取消群管理员", Args["user", At]),
    aliases={"取消管理员", "撤销群管理员"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
kick_group_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("踢出群成员", Args["user", At]["reject_add_request?", bool, False]),
    aliases={"踢出", "踢人", "移出群成员"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "milkybot_set_group_member_card": ".milky.member",
    "milkybot_set_group_member_special_title": ".milky.member",
    "milkybot_set_group_member_admin": ".milky.member",
    "milkybot_unset_group_member_admin": ".milky.member",
    "milkybot_kick_group_member": ".milky.member",
    "onebot11_set_group_member_card": ".onebot_v11.member",
    "onebot11_set_group_member_special_title": ".onebot_v11.member",
    "onebot11_set_group_member_admin": ".onebot_v11.member",
    "onebot11_unset_group_member_admin": ".onebot_v11.member",
    "onebot11_kick_group_member": ".onebot_v11.member",
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
