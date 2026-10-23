from typing import Any

from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)

from ......i18n import _async as _
from ......services.webui.launcher import (
    ensure_webui_mounted,
    webui_status_summary,
)
from ....commands.common import selected_adapter_handle
from ....commands.webui import webui_start_cmd

# NOTE: 本模块被 @selected_adapter_handle 包装，禁止 from __future__ import
# annotations。NoneBot 通过 get_typed_signature 解析 wrapper.__globals__ 中的
# 前向引用，而 @wraps 不会复制 __globals__，加了 future annotations 会让
# OneBot11 的事件类型在启动时 NameError。


@selected_adapter_handle(
    webui_start_cmd,
    "~onebot.v11",
    "webui_start",
    bypass_gate=True,
    bypass_silent=True,
)
async def onebot11_webui_start(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    """启动 WebUI（幂等），关机与静默状态下同样可用。"""
    status = await ensure_webui_mounted()
    return await webui_start_cmd.finish(await _(webui_status_summary(status)))
