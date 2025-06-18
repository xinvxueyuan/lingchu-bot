from ..lib.basic import *
from .admin_utils import check_qq_auth
from ..lib.management import check_bot_admin_status, get_group_muted_list
from ..lib.event import admin_rule

ban_monitor = on_notice(priority=5, block=False)

@ban_monitor.handle()
async def handle_ban_monitor(bot: Bot, event: GroupBanNoticeEvent):
    if event.sub_type == "ban" and event.duration > 0 and check_qq_auth(str(event.user_id)):
        try:
            if not await check_bot_admin_status(event.group_id):
                logger.warning(f"机器人无管理员权限，无法解禁用户 {event.user_id}")
                await bot.send_group_msg(
                    group_id=event.group_id,
                    message=f"检测到特殊权限用户被禁言，但机器人无管理员权限，无法自动解禁\n被禁言用户: {event.user_id}"
                )
                return
                
            await bot.set_group_ban(group_id=event.group_id, user_id=event.user_id, duration=0)
            operator_info = await bot.get_group_member_info(group_id=event.group_id, user_id=event.operator_id, no_cache=True)
            operator_name = operator_info.get("card") or operator_info.get("nickname")
            await bot.send_group_msg(group_id=event.group_id, message=f"检测到特殊权限用户被禁言，已自动解禁\n操作者: {operator_name}({event.operator_id})")
        except Exception as e: logger.error(f"自动解禁特殊权限用户失败: {str(e)}")


mute_list = on_command("禁言列表", aliases={"查禁言","查询禁言列表"}, priority=5, block=True, rule=admin_rule)

@mute_list.handle()
async def handle_mute_list(bot: Bot, event: GroupMessageEvent):
    if not await check_bot_admin_status(event.group_id):
        await bot.send_group_msg(
            group_id=event.group_id,
            message="机器人无管理员权限，无法查询禁言列表"
        )
        return
    
    muted_list = await get_group_muted_list(event.group_id)
    if not muted_list:
        await bot.send_group_msg(
            group_id=event.group_id,
            message="当前群内没有被禁言的成员"
        )
        return
    
    msg = "当前禁言成员列表:\n"
    for member in muted_list:
        msg += f"{member['nickname']}({member['user_id']}) - 剩余时间: {member['time_left']}秒\n"
    
    await bot.send_group_msg(
        group_id=event.group_id,
        message=msg
    )
