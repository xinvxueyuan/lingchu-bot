from typing import Any

from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.event import (
    GroupMessageEvent as OneBot11GroupMessageEvent,
)
from nonebot_plugin_alconna.uniseg import At

from .....i18n import _async as _
from ..common import selected_adapter_handle
from ..member import (
    kick_group_member_cmd,
    set_group_member_admin_cmd,
    set_group_member_card_cmd,
    set_group_member_special_title_cmd,
    unset_group_member_admin_cmd,
)
from .common import run_group_action_onebot11, target_user_onebot11


@selected_adapter_handle(set_group_member_card_cmd, "~onebot.v11")
async def onebot11_set_group_member_card(
    user: At,
    card: str,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    target_user_id, target_name = target_user_onebot11(user, event)
    return await run_group_action_onebot11(
        set_group_member_card_cmd,
        await _("设置群名片"),
        lambda: bot.set_group_card(
            group_id=event.group_id, user_id=target_user_id, card=card
        ),
        (await _("已设置群名片: {target_name}({target_user_id}) -> {card}")).format(
            target_name=target_name, target_user_id=target_user_id, card=card
        ),
    )


@selected_adapter_handle(set_group_member_special_title_cmd, "~onebot.v11")
async def onebot11_set_group_member_special_title(
    user: At,
    special_title: str,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    target_user_id, target_name = target_user_onebot11(user, event)
    return await run_group_action_onebot11(
        set_group_member_special_title_cmd,
        await _("设置群成员专属头衔"),
        lambda: bot.set_group_special_title(
            group_id=event.group_id,
            user_id=target_user_id,
            special_title=special_title,
            duration=-1,
        ),
        (
            await _("已设置群头衔: {target_name}({target_user_id}) -> {special_title}")
        ).format(
            target_name=target_name,
            target_user_id=target_user_id,
            special_title=special_title,
        ),
    )


@selected_adapter_handle(set_group_member_admin_cmd, "~onebot.v11")
async def onebot11_set_group_member_admin(
    user: At,
    is_set: bool,  # noqa: FBT001
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    target_user_id, target_name = target_user_onebot11(user, event)
    action_text = await _("设置") if is_set else await _("取消")
    return await run_group_action_onebot11(
        set_group_member_admin_cmd,
        await _("设置群管理员"),
        lambda: bot.set_group_admin(
            group_id=event.group_id, user_id=target_user_id, enable=is_set
        ),
        (await _("{action}群管理员: {target_name}({target_user_id})")).format(
            action=action_text,
            target_name=target_name,
            target_user_id=target_user_id,
        ),
    )


@selected_adapter_handle(unset_group_member_admin_cmd, "~onebot.v11")
async def onebot11_unset_group_member_admin(
    user: At,
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    return await onebot11_set_group_member_admin(
        user=user, is_set=False, bot=bot, event=event
    )


@selected_adapter_handle(kick_group_member_cmd, "~onebot.v11")
async def onebot11_kick_group_member(
    user: At,
    reject_add_request: bool,  # noqa: FBT001
    bot: OneBot11Bot,
    event: OneBot11GroupMessageEvent,
) -> Any:
    target_user_id, target_name = target_user_onebot11(user, event)
    return await run_group_action_onebot11(
        kick_group_member_cmd,
        await _("踢出群成员"),
        lambda: bot.set_group_kick(
            group_id=event.group_id,
            user_id=target_user_id,
            reject_add_request=reject_add_request,
        ),
        (await _("已踢出群成员: {target_name}({target_user_id})")).format(
            target_name=target_name, target_user_id=target_user_id
        ),
    )
