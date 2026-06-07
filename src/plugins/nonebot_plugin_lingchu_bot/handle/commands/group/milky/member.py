from typing import Any

from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
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
from .common import run_group_action_milky, target_user_milky


@selected_adapter_handle(set_group_member_card_cmd, "~milky")
async def milkybot_set_group_member_card(
    user: At,
    card: str,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    target_user_id, target_name = target_user_milky(user, event)
    return await run_group_action_milky(
        set_group_member_card_cmd,
        await _("设置群名片"),
        lambda: bot.set_group_member_card(
            group_id=event.data.peer_id, user_id=target_user_id, card=card
        ),
        (await _("已设置群名片: {target_name}({target_user_id}) -> {card}")).format(
            target_name=target_name, target_user_id=target_user_id, card=card
        ),
    )


@selected_adapter_handle(set_group_member_special_title_cmd, "~milky")
async def milkybot_set_group_member_special_title(
    user: At,
    special_title: str,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    target_user_id, target_name = target_user_milky(user, event)
    return await run_group_action_milky(
        set_group_member_special_title_cmd,
        await _("设置群成员专属头衔"),
        lambda: bot.set_group_member_special_title(
            group_id=event.data.peer_id,
            user_id=target_user_id,
            special_title=special_title,
        ),
        (
            await _("已设置群头衔: {target_name}({target_user_id}) -> {special_title}")
        ).format(
            target_name=target_name,
            target_user_id=target_user_id,
            special_title=special_title,
        ),
    )


@selected_adapter_handle(set_group_member_admin_cmd, "~milky")
async def milkybot_set_group_member_admin(
    user: At,
    is_set: bool,  # noqa: FBT001
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    target_user_id, target_name = target_user_milky(user, event)
    action_text = await _("设置") if is_set else await _("取消")
    return await run_group_action_milky(
        set_group_member_admin_cmd,
        await _("设置群管理员"),
        lambda: bot.set_group_member_admin(
            group_id=event.data.peer_id, user_id=target_user_id, is_set=is_set
        ),
        (await _("{action}群管理员: {target_name}({target_user_id})")).format(
            action=action_text,
            target_name=target_name,
            target_user_id=target_user_id,
        ),
    )


@selected_adapter_handle(unset_group_member_admin_cmd, "~milky")
async def milkybot_unset_group_member_admin(
    user: At,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    return await milkybot_set_group_member_admin(
        user=user, is_set=False, bot=bot, event=event
    )


@selected_adapter_handle(kick_group_member_cmd, "~milky")
async def milkybot_kick_group_member(
    user: At,
    reject_add_request: bool,  # noqa: FBT001
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    target_user_id, target_name = target_user_milky(user, event)
    return await run_group_action_milky(
        kick_group_member_cmd,
        await _("踢出群成员"),
        lambda: bot.kick_group_member(
            group_id=event.data.peer_id,
            user_id=target_user_id,
            reject_add_request=reject_add_request,
        ),
        (await _("已踢出群成员: {target_name}({target_user_id})")).format(
            target_name=target_name, target_user_id=target_user_id
        ),
    )
