from importlib import import_module
from typing import Any

from arclet.alconna import Alconna, Args
from nonebot import logger
from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import At

from ....i18n import _async as _
from ....services.permissions import bind_command_key
from .command_triggers import COMMAND_TRIGGERS

_BLOCK_MEMBER = COMMAND_TRIGGERS["block_member"]
_GLOBAL_BLOCK_MEMBER = COMMAND_TRIGGERS["global_block_member"]
_UNBLOCK_MEMBER = COMMAND_TRIGGERS["unblock_member"]
_GLOBAL_UNBLOCK_MEMBER = COMMAND_TRIGGERS["global_unblock_member"]
_CLEAR_BLOCKLIST = COMMAND_TRIGGERS["clear_blocklist"]
_GLOBAL_CLEAR_BLOCKLIST = COMMAND_TRIGGERS["global_clear_blocklist"]

block_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _BLOCK_MEMBER.primary,
        Args["user", At]["duration?", int, None]["reason?", str, None],
    ),
    aliases=_BLOCK_MEMBER.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
bind_command_key(block_member_cmd, "block_member")
global_block_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _GLOBAL_BLOCK_MEMBER.primary,
        Args["user", At]["duration?", int, None]["reason?", str, None],
    ),
    aliases=_GLOBAL_BLOCK_MEMBER.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
bind_command_key(global_block_member_cmd, "global_block_member")
unblock_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _UNBLOCK_MEMBER.primary,
        Args["user", At]["reason?", str, None],
    ),
    aliases=_UNBLOCK_MEMBER.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
bind_command_key(unblock_member_cmd, "unblock_member")
global_unblock_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _GLOBAL_UNBLOCK_MEMBER.primary,
        Args["user", At]["reason?", str, None],
    ),
    aliases=_GLOBAL_UNBLOCK_MEMBER.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
bind_command_key(global_unblock_member_cmd, "global_unblock_member")
clear_blocklist_cmd: type[Matcher] = on_alconna(
    command=Alconna(_CLEAR_BLOCKLIST.primary, Args["reason?", str, None]),
    aliases=_CLEAR_BLOCKLIST.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
bind_command_key(clear_blocklist_cmd, "clear_blocklist")
global_clear_blocklist_cmd: type[Matcher] = on_alconna(
    command=Alconna(_GLOBAL_CLEAR_BLOCKLIST.primary, Args["reason?", str, None]),
    aliases=_GLOBAL_CLEAR_BLOCKLIST.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
bind_command_key(global_clear_blocklist_cmd, "global_clear_blocklist")

_LAZY_EXPORTS = {
    "onebot11_block_member": "..onebot.v11.default.group.block",
    "onebot11_global_block_member": "..onebot.v11.default.group.block",
    "onebot11_unblock_member": "..onebot.v11.default.group.block",
    "onebot11_global_unblock_member": "..onebot.v11.default.group.block",
    "onebot11_clear_blocklist": "..onebot.v11.default.group.block",
    "onebot11_global_clear_blocklist": "..onebot.v11.default.group.block",
    "onebot11_kick_blocklisted_message": "..onebot.v11.default.group.block",
    "onebot11_reject_blocklisted_group_request": "..onebot.v11.default.group.block",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value


async def import_handle() -> Any:
    logger.debug(await _("导入block处理器..."))
