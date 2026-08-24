from typing import Any

from nonebot import logger, require
from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
    PrivateMessageEvent as OneBot11PrivateMessageEvent,
)
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed

require("nonebot_plugin_orm")
from nonebot_plugin_orm import async_scoped_session

from ......core.runtime_config import reload_runtime_configs_from_disk
from ......i18n import _async as _
from ......services.protocol_restart_feedback import (
    clear_pending_restart_feedback_for,
    register_pending_restart_feedback,
)
from ......services.restart_app import register_pending_restart_app
from ....commands.common import selected_adapter_handle
from ....commands.lifecycle import (
    quit_group_cmd,
    reset_runtime_config_cmd,
    restart_app_cmd,
    restart_protocol_endpoint_cmd,
)

_CURRENT_PLATFORM_ALIASES = {
    "",
    "当前平台",
    "本平台",
    "qq",
    "QQ",
    "onebot",
    "onebot11",
    "onebot-v11",
    "~onebot.v11",
}


def _is_current_onebot11_platform(platform: str | None) -> bool:
    if platform is None:
        return True
    return platform.strip() in _CURRENT_PLATFORM_ALIASES


@selected_adapter_handle(quit_group_cmd, "~onebot.v11", "leave_group")
async def onebot11_quit_group(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    # 1. 执行退出群操作
    try:
        await bot.set_group_leave(group_id=event.group_id, is_dismiss=False)
    except OneBot11ActionFailed as e:
        logger.error(f"退出群失败，操作被拒绝: {e!r}")
        return await quit_group_cmd.finish(await _("退出群失败，操作被拒绝"))

    # 2. 反馈结果
    return await quit_group_cmd.finish(await _("退出当前群"))


@selected_adapter_handle(
    restart_protocol_endpoint_cmd, "~onebot.v11", "restart_protocol_endpoint"
)
async def onebot11_restart_protocol_endpoint(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    session: async_scoped_session,
    platform: str | None = None,
) -> Any:
    if not _is_current_onebot11_platform(platform):
        return await restart_protocol_endpoint_cmd.finish(
            await _("当前仅支持重启当前 QQ OneBot V11 协议端")
        )

    bot_id = str(getattr(bot, "self_id", ""))
    await restart_protocol_endpoint_cmd.send(
        await _("已请求重启协议端，重新连接后会发送反馈")
    )
    register_pending_restart_feedback(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id=bot_id,
        conversation_type="group",
        conversation_id=str(event.group_id),
    )
    try:
        await bot.call_api("set_restart")
    except OneBot11ActionFailed as e:
        clear_pending_restart_feedback_for(
            platform_id="qq", adapter_id="~onebot.v11", bot_id=bot_id
        )
        logger.error(f"重启协议端失败，操作被拒绝: {e!r}")
        return await restart_protocol_endpoint_cmd.finish(
            await _("重启协议端失败，操作被拒绝")
        )

    return None


@selected_adapter_handle(restart_app_cmd, "~onebot.v11", "restart_app")
async def onebot11_restart_app(
    bot: OneBot11Bot,
    event: OneBot11PrivateMessageEvent | OneBot11GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    del session
    bot_id = str(getattr(bot, "self_id", ""))
    if isinstance(event, OneBot11PrivateMessageEvent):
        conversation_type = "private"
        conversation_id = str(event.user_id)
    else:
        conversation_type = "group"
        conversation_id = str(event.group_id)
    account_id = str(event.user_id)
    await restart_app_cmd.send(
        (
            await _(
                "确认要重启应用吗？回复「是」确认，回复「否」取消，{seconds} 秒内有效"
            )
        ).format(seconds=60)
    )
    register_pending_restart_app(
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id=bot_id,
        conversation_type=conversation_type,
        conversation_id=conversation_id,
        account_id=account_id,
    )
    return None


@selected_adapter_handle(
    reset_runtime_config_cmd,
    "~onebot.v11",
    "reset_runtime_config",
)
async def onebot11_reset_runtime_config(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    session: async_scoped_session,
) -> Any:
    del bot, event, session
    await reload_runtime_configs_from_disk()
    return await reset_runtime_config_cmd.finish(await _("灵初配置已从磁盘重置"))
