from importlib import import_module
from typing import Any

from arclet.alconna import Alconna
from nonebot.internal.matcher.matcher import Matcher
from nonebot_plugin_alconna import on_alconna

from .triggers import COMMAND_TRIGGERS

_BOT_SILENCE = COMMAND_TRIGGERS["bot_silence"]
_BOT_SPEAK = COMMAND_TRIGGERS["bot_speak"]
_BOT_BOOT = COMMAND_TRIGGERS["bot_boot"]
_BOT_SHUTDOWN = COMMAND_TRIGGERS["bot_shutdown"]

bot_silence_cmd: type[Matcher] = on_alconna(
    command=Alconna(_BOT_SILENCE.primary),
    aliases=_BOT_SILENCE.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
bot_speak_cmd: type[Matcher] = on_alconna(
    command=Alconna(_BOT_SPEAK.primary),
    aliases=_BOT_SPEAK.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
bot_boot_cmd: type[Matcher] = on_alconna(
    command=Alconna(_BOT_BOOT.primary),
    aliases=_BOT_BOOT.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
bot_shutdown_cmd: type[Matcher] = on_alconna(
    command=Alconna(_BOT_SHUTDOWN.primary),
    aliases=_BOT_SHUTDOWN.aliases,
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)

_LAZY_EXPORTS = {
    "onebot11_bot_silence": "..adapters.onebot11.default.bot_state",
    "onebot11_bot_speak": "..adapters.onebot11.default.bot_state",
    "onebot11_bot_boot": "..adapters.onebot11.default.bot_state",
    "onebot11_bot_shutdown": "..adapters.onebot11.default.bot_state",
}


def __getattr__(name: str) -> Any:
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module = import_module(_LAZY_EXPORTS[name], __package__)
    value = getattr(module, name)
    globals()[name] = value
    return value
