from typing import Any

from arclet.alconna import Alconna, Args
from nonebot.adapters.milky import Bot as MilkyBot
from nonebot.adapters.milky.event import GroupMessageEvent as MilkyGroupMessageEvent
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import At

from ....i18n import _async as _
from .common import run_group_action, target_user

set_group_member_card_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("设置群名片", Args["user", At]["card", str]),
    aliases={"改群名片", "修改群名片", "设置成员名片"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
set_group_member_special_title_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("设置群头衔", Args["user", At]["special_title", str]),
    aliases={"设置专属头衔", "设置群成员专属头衔", "改群头衔"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
set_group_member_admin_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("设置群管理员", Args["user", At]["is_set?", bool, True]),
    aliases={"设置管理员", "任命群管理员"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
unset_group_member_admin_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("取消群管理员", Args["user", At]),
    aliases={"取消管理员", "撤销群管理员"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)
kick_group_member_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna("踢出群成员", Args["user", At]["reject_add_request?", bool, False]),
    aliases={"踢出", "踢人", "移出群成员"},
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)


@set_group_member_card_cmd.handle()
async def milkybot_set_group_member_card(
    user: At,
    card: str,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    target_user_id, target_name = target_user(user, event)
    return await run_group_action(
        set_group_member_card_cmd,
        await _("设置群名片"),
        lambda: bot.set_group_member_card(
            group_id=event.data.peer_id, user_id=target_user_id, card=card
        ),
        (await _("已设置群名片: {target_name}({target_user_id}) -> {card}")).format(
            target_name=target_name, target_user_id=target_user_id, card=card
        ),
    )


@set_group_member_special_title_cmd.handle()
async def milkybot_set_group_member_special_title(
    user: At,
    special_title: str,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    target_user_id, target_name = target_user(user, event)
    return await run_group_action(
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


@set_group_member_admin_cmd.handle()
async def milkybot_set_group_member_admin(
    user: At,
    is_set: bool,  # noqa: FBT001
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    target_user_id, target_name = target_user(user, event)
    action_text = await _("设置") if is_set else await _("取消")
    return await run_group_action(
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


@unset_group_member_admin_cmd.handle()
async def milkybot_unset_group_member_admin(
    user: At,
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    return await milkybot_set_group_member_admin(
        user=user, is_set=False, bot=bot, event=event
    )


@kick_group_member_cmd.handle()
async def milkybot_kick_group_member(
    user: At,
    reject_add_request: bool,  # noqa: FBT001
    bot: MilkyBot,
    event: MilkyGroupMessageEvent,
) -> Any:
    target_user_id, target_name = target_user(user, event)
    return await run_group_action(
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
