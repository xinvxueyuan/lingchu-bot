"""Remote management commands for cross-group operations."""

from importlib import import_module
from typing import Any

from arclet.alconna import Alconna, Args
from nonebot import logger
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import At
from nonebot_plugin_alconna.uniseg import Image as UniImage

from ....i18n import _async as _
from .triggers import COMMAND_TRIGGERS

_REMOTE_MUTE = COMMAND_TRIGGERS["remote_mute"]
_REMOTE_UNMUTE = COMMAND_TRIGGERS["remote_unmute"]
_REMOTE_WHOLE_MUTE = COMMAND_TRIGGERS["remote_whole_mute"]
_REMOTE_WHOLE_UNMUTE = COMMAND_TRIGGERS["remote_whole_unmute"]
_REMOTE_KICK = COMMAND_TRIGGERS["remote_kick"]
_REMOTE_BLOCK = COMMAND_TRIGGERS["remote_block"]
_REMOTE_UNBLOCK = COMMAND_TRIGGERS["remote_unblock"]
_REMOTE_ANNOUNCEMENT = COMMAND_TRIGGERS["remote_announcement"]

# 远程禁言命令
remote_mute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _REMOTE_MUTE.primary,
        Args["group_id", (int, str)]["user", At | int]["duration?", int, 60][
            "reason?", str, None
        ],
    ),
    aliases=_REMOTE_MUTE.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

# 远程解禁命令
remote_unmute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _REMOTE_UNMUTE.primary,
        Args["group_id", (int, str)]["user", At | int]["reason?", str, None],
    ),
    aliases=_REMOTE_UNMUTE.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

# 远程全体禁言命令
remote_whole_mute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _REMOTE_WHOLE_MUTE.primary,
        Args["group_id", (int, str)],
    ),
    aliases=_REMOTE_WHOLE_MUTE.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

# 远程全体解禁命令
remote_whole_unmute_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _REMOTE_WHOLE_UNMUTE.primary,
        Args["group_id", (int, str)],
    ),
    aliases=_REMOTE_WHOLE_UNMUTE.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

# 远程踢出命令
remote_kick_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _REMOTE_KICK.primary,
        Args["group_id", (int, str)]["user", At | int]["reason?", str, None],
    ),
    aliases=_REMOTE_KICK.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

# 远程拉黑命令
remote_block_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _REMOTE_BLOCK.primary,
        Args["group_id", (int, str)]["user", At | int]["duration?", int, None][
            "reason?", str, None
        ],
    ),
    aliases=_REMOTE_BLOCK.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

# 远程删黑命令
remote_unblock_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _REMOTE_UNBLOCK.primary,
        Args["group_id", (int, str)]["user", At | int]["reason?", str, None],
    ),
    aliases=_REMOTE_UNBLOCK.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

# 远程公告命令
remote_announcement_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _REMOTE_ANNOUNCEMENT.primary,
        Args["group_id", (int, str)]["content", str]["image?", UniImage, None],
    ),
    aliases=_REMOTE_ANNOUNCEMENT.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "onebot11_remote_mute": "..adapters.onebot11.default.remote",
    "onebot11_remote_unmute": "..adapters.onebot11.default.remote",
    "onebot11_remote_whole_mute": "..adapters.onebot11.default.remote",
    "onebot11_remote_whole_unmute": "..adapters.onebot11.default.remote",
    "onebot11_remote_kick": "..adapters.onebot11.default.remote",
    "onebot11_remote_block": "..adapters.onebot11.default.remote",
    "onebot11_remote_unblock": "..adapters.onebot11.default.remote",
    "onebot11_remote_announcement": "..adapters.onebot11.default.remote",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value


async def import_handle() -> Any:
    logger.debug(await _("导入remote处理器..."))
