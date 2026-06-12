from importlib import import_module
from typing import Any

from arclet.alconna import Alconna
from nonebot import logger
from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import on_alconna

from ....i18n import _async as _

quit_group_cmd: type[Matcher] = on_alconna(
    command=Alconna("退出群"),
    aliases={"退群", "退出当前群"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "milkybot_quit_group": "..milky.v1_2.default.group.lifecycle",
    "onebot11_quit_group": "..onebot.v11.default.group.lifecycle",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value


async def import_handle() -> Any:
    logger.debug(await _("导入lifecycle处理器..."))
