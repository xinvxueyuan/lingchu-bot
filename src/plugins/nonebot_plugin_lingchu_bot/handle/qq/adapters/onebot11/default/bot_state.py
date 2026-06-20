from typing import Any

from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)

from ......core.bot_state import set_global_handle_active, set_global_silent_mode
from ......i18n import _async as _
from ....commands.bot_state import (
    bot_boot_cmd,
    bot_shutdown_cmd,
    bot_silence_cmd,
    bot_speak_cmd,
)
from ....commands.common import selected_adapter_handle


@selected_adapter_handle(
    bot_silence_cmd, "~onebot.v11", "bot_silence", bypass_silent=True
)
async def onebot11_bot_silence(
    bot: OneBot11Bot,  # noqa: ARG001
    event: OneBot11GroupMessageEvent,  # noqa: ARG001
) -> Any:
    set_global_silent_mode(silent=True)
    return await bot_silence_cmd.finish(await _("已进入静默模式"))


@selected_adapter_handle(bot_speak_cmd, "~onebot.v11", "bot_speak", bypass_silent=True)
async def onebot11_bot_speak(
    bot: OneBot11Bot,  # noqa: ARG001
    event: OneBot11GroupMessageEvent,  # noqa: ARG001
) -> Any:
    set_global_silent_mode(silent=False)
    return await bot_speak_cmd.finish(await _("已退出静默模式"))


@selected_adapter_handle(
    bot_boot_cmd, "~onebot.v11", "bot_boot", bypass_gate=True, bypass_silent=True
)
async def onebot11_bot_boot(
    bot: OneBot11Bot,  # noqa: ARG001
    event: OneBot11GroupMessageEvent,  # noqa: ARG001
) -> Any:
    set_global_handle_active(active=True)
    return await bot_boot_cmd.finish(await _("已开机"))


@selected_adapter_handle(
    bot_shutdown_cmd,
    "~onebot.v11",
    "bot_shutdown",
    bypass_gate=True,
    bypass_silent=True,
)
async def onebot11_bot_shutdown(
    bot: OneBot11Bot,  # noqa: ARG001
    event: OneBot11GroupMessageEvent,  # noqa: ARG001
) -> Any:
    set_global_handle_active(active=False)
    return await bot_shutdown_cmd.finish(await _("已关机"))
