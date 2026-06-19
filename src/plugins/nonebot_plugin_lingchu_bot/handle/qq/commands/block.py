from importlib import import_module
from typing import Any

from arclet.alconna import Alconna, Args
from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import At

from .triggers import COMMAND_TRIGGERS

_BLOCK_MEMBER = COMMAND_TRIGGERS["block_member"]
_GLOBAL_BLOCK_MEMBER = COMMAND_TRIGGERS["global_block_member"]
_UNBLOCK_MEMBER = COMMAND_TRIGGERS["unblock_member"]
_GLOBAL_UNBLOCK_MEMBER = COMMAND_TRIGGERS["global_unblock_member"]
_CLEAR_BLOCKLIST = COMMAND_TRIGGERS["clear_blocklist"]
_GLOBAL_CLEAR_BLOCKLIST = COMMAND_TRIGGERS["global_clear_blocklist"]

block_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _BLOCK_MEMBER.primary,
        Args["user", At | int]["duration?", int, None]["reason?", str, None],
    ),
    aliases=_BLOCK_MEMBER.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
global_block_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _GLOBAL_BLOCK_MEMBER.primary,
        Args["user", At | int]["duration?", int, None]["reason?", str, None],
    ),
    aliases=_GLOBAL_BLOCK_MEMBER.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
unblock_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _UNBLOCK_MEMBER.primary,
        Args["user", At | int]["reason?", str, None],
    ),
    aliases=_UNBLOCK_MEMBER.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
global_unblock_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(
        _GLOBAL_UNBLOCK_MEMBER.primary,
        Args["user", At | int]["reason?", str, None],
    ),
    aliases=_GLOBAL_UNBLOCK_MEMBER.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
clear_blocklist_cmd: type[Matcher] = on_alconna(
    command=Alconna(_CLEAR_BLOCKLIST.primary, Args["reason?", str, None]),
    aliases=_CLEAR_BLOCKLIST.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
global_clear_blocklist_cmd: type[Matcher] = on_alconna(
    command=Alconna(_GLOBAL_CLEAR_BLOCKLIST.primary, Args["reason?", str, None]),
    aliases=_GLOBAL_CLEAR_BLOCKLIST.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "onebot11_block_member": "..adapters.onebot11.default.block",
    "onebot11_global_block_member": "..adapters.onebot11.default.block",
    "onebot11_unblock_member": "..adapters.onebot11.default.block",
    "onebot11_global_unblock_member": "..adapters.onebot11.default.block",
    "onebot11_clear_blocklist": "..adapters.onebot11.default.block",
    "onebot11_global_clear_blocklist": "..adapters.onebot11.default.block",
    "onebot11_kick_blocklisted_message": "..adapters.onebot11.default.block",
    "onebot11_reject_blocklisted_group_request": "..adapters.onebot11.default.block",
    "milkybot_block_member": "..adapters.milky.default.block",
    "milkybot_global_block_member": "..adapters.milky.default.block",
    "milkybot_unblock_member": "..adapters.milky.default.block",
    "milkybot_global_unblock_member": "..adapters.milky.default.block",
    "milkybot_clear_blocklist": "..adapters.milky.default.block",
    "milkybot_global_clear_blocklist": "..adapters.milky.default.block",
    "milkybot_kick_blocklisted_message": "..adapters.milky.default.block",
    "milkybot_reject_blocklisted_group_request": "..adapters.milky.default.block",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
