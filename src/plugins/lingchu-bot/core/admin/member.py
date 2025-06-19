"""
此模块实现了群成员移出功能，只有具备管理员权限的用户才能触发该操作。
机器人需要有管理员权限才能执行移出操作。
"""

from ..lib.basic import *
from ..lib.event import admin_rule
from ..lib.management import manage_group_kick, check_bot_admin_status
from .admin_utils import parse_target_qq

# 定义命令处理器，监听 "移出"、"踢"、"踢出" 命令，优先级为 5，阻断其他同优先级事件，使用管理员规则
kick = on_command(
    "移出", aliases={"踢", "踢出"}, priority=5, block=True, rule=admin_rule
)


async def handle_kick_action(event: GroupMessageEvent, matcher: Matcher):
    """
    统一处理群成员移出操作。

    检查机器人是否有管理员权限，解析目标 QQ 号，调用移出函数并根据结果发送相应消息。

    Args:
        event (GroupMessageEvent): 群消息事件对象，包含群号和消息内容等信息。
        matcher (Matcher): 事件匹配器，用于发送消息。

    Returns:
        None
    """
    try:
        # 检查机器人是否有管理员权限
        if not await check_bot_admin_status(event.group_id):
            await matcher.send("机器人无管理员权限，无法执行移出操作")
            return

        # 解析目标 QQ 号
        target_qq, error_msg = await parse_target_qq(event)
        if error_msg:
            await matcher.send(error_msg)
            return

        # 执行群成员移出操作
        success = await manage_group_kick(group_id=event.group_id, user_id=target_qq)
        if success:
            await matcher.send(Message(f"已移出 [CQ:at,qq={target_qq}]"))
        else:
            await matcher.send(Message(f"移出 [CQ:at,qq={target_qq}] 失败"))
    except Exception as e:
        await matcher.send(Message(f"移出失败: {str(e)}"))


@kick.handle()
async def handle_kick(event: GroupMessageEvent, matcher: Matcher):
    """
    处理 "移出" 命令的入口函数，调用统一处理函数。

    Args:
        event (GroupMessageEvent): 群消息事件对象，包含群号和消息内容等信息。
        matcher (Matcher): 事件匹配器，用于发送消息。

    Returns:
        None
    """
    await handle_kick_action(event, matcher)
