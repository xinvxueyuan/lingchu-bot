""" 名单系统 """
from ..lib.basic import *
from .admin_utils import check_qq_auth
from ..lib.management import check_bot_admin_status, get_group_muted_list
from ..lib.event import admin_rule

# 禁言通知事件处理器，优先级为 5，不阻止事件传播
ban_monitor = on_notice(priority=5, block=False)


@ban_monitor.handle()
async def handle_ban_monitor(bot: Bot, event: GroupBanNoticeEvent):
    # 检查是否为禁言事件、禁言时长大于 0 且被禁言用户具有特殊权限
    if (
        event.sub_type == "ban"
        and event.duration > 0
        and check_qq_auth(str(event.user_id))
    ):
        try:
            # 检查机器人是否具有管理员权限
            if not await check_bot_admin_status(event.group_id):
                # 记录警告日志并通知群成员机器人无权限解禁
                logger.warning(f"机器人无管理员权限，无法解禁用户 {event.user_id}")
                await bot.send_group_msg(
                    group_id=event.group_id,
                    message=f"检测到特殊权限用户被禁言，但机器人无管理员权限，无法自动解禁\n被禁言用户: {event.user_id}",
                )
                return

            # 解除特殊权限用户的禁言
            await bot.set_group_ban(
                group_id=event.group_id, user_id=event.user_id, duration=0
            )
            # 获取禁言操作者的信息
            operator_info = await bot.get_group_member_info(
                group_id=event.group_id, user_id=event.operator_id, no_cache=True
            )
            # 获取操作者的群名片或昵称
            operator_name = operator_info.get("card") or operator_info.get("nickname")
            # 通知群成员已自动解禁特殊权限用户
            await bot.send_group_msg(
                group_id=event.group_id,
                message=f"检测到特殊权限用户被禁言，已自动解禁\n操作者: {operator_name}({event.operator_id})",
            )
        except Exception as e:
            # 记录自动解禁失败的错误日志
            logger.error(f"自动解禁特殊权限用户失败: {str(e)}")


# 禁言命令处理器，支持多个命令别名，优先级为 5，阻止事件传播，需要管理员权限
mute_list = on_command(
    "禁言列表",
    aliases={"查禁言", "查询禁言列表"},
    priority=5,
    block=True,
    rule=admin_rule,
)


@mute_list.handle()
async def handle_mute_list(bot: Bot, event: GroupMessageEvent):
    # 检查机器人是否具有管理员权限
    if not await check_bot_admin_status(event.group_id):
        # 通知群成员机器人无权限查询禁言列表
        await bot.send_group_msg(
            group_id=event.group_id, message="机器人无管理员权限，无法查询禁言列表"
        )
        return

    # 获取群内的禁言成员列表
    muted_list = await get_group_muted_list(event.group_id)
    # 检查禁言列表是否为空
    if not muted_list:
        # 通知群成员当前群内没有被禁言的成员
        await bot.send_group_msg(
            group_id=event.group_id, message="当前群内没有被禁言的成员"
        )
        return

    # 构建禁言成员列表消息
    msg = "当前禁言成员列表:\n"
    for member in muted_list:
        msg += f"{member['nickname']}({member['user_id']})-剩余{member['time_left']}秒\n"

    # 发送禁言成员列表消息到群内
    await bot.send_group_msg(group_id=event.group_id, message=msg)
