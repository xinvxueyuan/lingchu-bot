from importlib import import_module
from typing import Any

from nonebot import logger, on_command
from nonebot.internal.matcher.matcher import Matcher

from ....i18n import _async as _

echo_cmd: type[Matcher] = on_command(
    "echo",
    aliases={"回显", "回声"},
    priority=5,
    block=True,
)

_LAZY_EXPORTS = {
    "onebot11_echo": ".onebot_v11.test",
    "milkybot_echo": ".milky.test",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value


async def import_handle() -> Any:
    logger.debug(await _("导入test处理器..."))
