from importlib import import_module
from typing import Any

from arclet.alconna import Alconna, Args
from nonebot import logger
from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import At

from ....i18n import _async as _

member_mute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        "禁言",
        Args["user", At]["duration?", int, 60]["reason?", str, None],
    ),
    aliases={"禁言用户", "禁言群成员", "禁言成员", "禁", "封禁"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
whole_mute_cmd: type[Matcher] = on_alconna(
    command=Alconna(
        "全员禁言",
    ),
    aliases={
        "开启全体禁言",
        "全禁",
        "全禁言",
        "全体禁言",
        "全体禁言开启",
        "全员禁言开启",
        "开启全员禁言",
        "禁言群",
    },
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
member_unmute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        "解禁",
        Args["user", At]["reason?", str, None],
    ),
    aliases={
        "解禁用户",
        "解禁群成员",
        "解禁成员",
        "解禁",
        "解封",
        "解除封禁",
        "解除禁言",
    },
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

whole_unmute_cmd: type[Matcher] = on_alconna(
    command=Alconna(
        "全体解禁",
    ),
    aliases={
        "全员解禁",
        "关闭全体禁言",
        "解除全体禁言",
        "解禁全体",
        "解禁全员",
        "全解",
        "全解禁",
        "全体解禁",
        "关闭全员禁言",
        "解除全员禁言",
        "解禁群",
    },
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "milkybot_mute": ".milky.mute",
    "milkybot_whole_mute": ".milky.mute",
    "milkybot_unmute": ".milky.mute",
    "milkybot_whole_unmute": ".milky.mute",
    "onebot11_mute": ".onebot_v11.mute",
    "onebot11_whole_mute": ".onebot_v11.mute",
    "onebot11_unmute": ".onebot_v11.mute",
    "onebot11_whole_unmute": ".onebot_v11.mute",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value


async def import_handle() -> Any:
    logger.debug(await _("导入mute处理器..."))
