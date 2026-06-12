from typing import Any

from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot_plugin_alconna.uniseg import At

from .......i18n import _async as _
from .....group.common import selected_adapter_handle
from .....group.mute import (
    member_mute_cmd,
    member_unmute_cmd,
    whole_mute_cmd,
    whole_unmute_cmd,
)
from .common import run_group_action_onebot11, target_user_onebot11


@selected_adapter_handle(member_mute_cmd, "~onebot.v11")
async def onebot11_mute(
    user: At,
    duration: int,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    target_user_id, target_name = await target_user_onebot11(user, bot, event)
    reason_text = await _("违反群规「默认」") if reason is None else reason
    name_display = f"@{target_name}" if target_name else str(target_user_id)
    return await run_group_action_onebot11(
        member_mute_cmd,
        await _("禁言"),
        lambda: bot.set_group_ban(
            group_id=event.group_id, user_id=target_user_id, duration=duration
        ),
        (
            await _(
                "已禁言: \n"
                "名称: {name_display}\n"
                "时长: {duration} 秒\n"
                "原因: {reason}\n"
                "标识: {target_user_id}"
            )
        ).format(
            name_display=name_display,
            duration=duration,
            reason=reason_text,
            target_user_id=target_user_id,
        ),
    )


@selected_adapter_handle(whole_mute_cmd, "~onebot.v11")
async def onebot11_whole_mute(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    return await run_group_action_onebot11(
        whole_mute_cmd,
        await _("全体禁言"),
        lambda: bot.set_group_whole_ban(group_id=event.group_id, enable=True),
        await _("全体禁言成功"),
    )


@selected_adapter_handle(member_unmute_cmd, "~onebot.v11")
async def onebot11_unmute(
    user: At,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
    reason: str | None = None,
) -> Any:
    target_user_id, target_name = await target_user_onebot11(user, bot, event)
    reason_text = await _("管理员操作「默认」") if reason is None else reason
    name_display = f"@{target_name}" if target_name else str(target_user_id)
    return await run_group_action_onebot11(
        member_unmute_cmd,
        await _("解禁"),
        lambda: bot.set_group_ban(
            group_id=event.group_id, user_id=target_user_id, duration=0
        ),
        (
            await _(
                "已解禁: \n名称: {name_display}\n原因: {reason}\n标识: {target_user_id}"
            )
        ).format(
            name_display=name_display,
            reason=reason_text,
            target_user_id=target_user_id,
        ),
    )


@selected_adapter_handle(whole_unmute_cmd, "~onebot.v11")
async def onebot11_whole_unmute(
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    return await run_group_action_onebot11(
        whole_unmute_cmd,
        await _("全体解禁"),
        lambda: bot.set_group_whole_ban(group_id=event.group_id, enable=False),
        await _("全体解禁成功"),
    )
