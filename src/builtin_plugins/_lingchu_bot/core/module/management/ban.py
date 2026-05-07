from nonebot import logger, on_startswith
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.adapters.onebot.v11.exception import ActionFailed
from nonebot_plugin_alconna.uniseg import UniMessage

from .utils.parse_id import (
    parse_ids_and_time,
    parse_ids_by_cmd,
)
from .utils.tools import check_permission_and_send_message, process_user_ids

# ================= 指令注册 =================
ban_cmd = on_startswith("禁言", priority=5, block=True)
whole_ban_cmd = on_startswith("全体禁言", priority=5, block=True)
unban_cmd = on_startswith("解禁", priority=5, block=True)
whole_unban_cmd = on_startswith("全体解禁", priority=5, block=True)


# ================= 事件处理 =================
@ban_cmd.handle()
async def handle_mute(bot: Bot, event: GroupMessageEvent) -> None:
    """
    处理禁言命令，支持多用户和单用户
    """
    user_ids, mute_time = parse_ids_and_time(event.raw_message, ["禁言"])
    if not user_ids or mute_time is None:
        await UniMessage.text(
            "格式错误，请使用：禁言@某人 时间（单位：秒）或 禁言[QQ号] 时间（单位：秒）"
            "\nTip: 多个请用空格分隔"
        ).send(reply_to=True)
        return
    if not await check_permission_and_send_message(
        event, {"admin", "owner", "super"}, "权限不足，仅管理员及以上可执行此操作"
    ):
        return

    await process_user_ids(
        event,
        user_ids,
        lambda uid: bot.set_group_ban(
            group_id=event.group_id, user_id=int(uid), duration=mute_time
        ),
        success_message="禁言成功: {users}",
        failure_message="禁言失败: {users}",
    )


@whole_ban_cmd.handle()
async def handle_whole_mute(bot: Bot, event: GroupMessageEvent) -> None:
    """
    处理全体禁言命令
    """
    if not await check_permission_and_send_message(
        event, {"admin", "owner", "super"}, "权限不足，仅管理员及以上可执行此操作"
    ):
        return
    try:
        await bot.set_group_whole_ban(group_id=event.group_id, enable=True)
        await UniMessage.text("全体禁言成功").send(reply_to=True)
    except ActionFailed as e:
        logger.error(f"全体禁言失败: {e}")
        await UniMessage.text("全体禁言失败").send(reply_to=True)


@unban_cmd.handle()
async def handle_unmute(bot: Bot, event: GroupMessageEvent) -> None:
    """
    处理解禁命令，支持多用户和单用户
    """
    user_ids = parse_ids_by_cmd(event.raw_message, ["解禁"])
    if not user_ids:
        await UniMessage.text(
            "格式错误，请使用：解禁@某人 或 解禁[QQ号]\nTip: 多个请用空格分隔"
        ).send(reply_to=True)
        return
    if not await check_permission_and_send_message(
        event, {"admin", "owner", "super"}, "权限不足，仅管理员及以上可执行此操作"
    ):
        return

    await process_user_ids(
        event,
        user_ids,
        lambda uid: bot.set_group_ban(
            group_id=event.group_id, user_id=int(uid), duration=0
        ),
        success_message="解禁成功: {users}",
        failure_message="解禁失败: {users}",
    )


@whole_unban_cmd.handle()
async def handle_whole_unmute(bot: Bot, event: GroupMessageEvent) -> None:
    """
    处理全体解禁命令
    """
    if not await check_permission_and_send_message(
        event, {"admin", "owner", "super"}, "权限不足，仅管理员及以上可执行此操作"
    ):
        return
    try:
        await bot.set_group_whole_ban(group_id=event.group_id, enable=False)
        await UniMessage.text("全体解禁成功").send(reply_to=True)
    except ActionFailed as e:
        logger.error(f"全体解禁失败: {e}")
        await UniMessage.text("全体解禁失败").send(reply_to=True)
