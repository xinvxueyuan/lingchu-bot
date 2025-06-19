""" 发言管理 """

from ..lib.basic import *
from ..lib.event import admin_rule
from .admin_utils import parse_target_qq
from ..lib.management import (
    manage_user_mute,
    manage_group_mute_all,
    check_bot_admin_status,
)

# 定义禁言命令，支持别名 "禁"，优先级 5，阻断其他处理，需管理员权限
mute = on_command("禁言", aliases={"禁"}, priority=5, block=True, rule=admin_rule)
# 定义解禁命令，支持别名 "解"，优先级 5，阻断其他处理，需管理员权限
unmute = on_command("解禁", aliases={"解"}, priority=5, block=True, rule=admin_rule)
# 定义全员禁言命令，支持多个别名，优先级 5，阻断其他处理，需管理员权限
mute_all = on_command(
    "全体禁言",
    aliases={"全部禁言", "全员禁言", "全禁", "全体禁"},
    priority=5,
    block=True,
    rule=admin_rule,
)
# 定义全员解禁命令，支持多个别名，优先级 5，阻断其他处理，需管理员权限
unmute_all = on_command(
    "全体解禁",
    aliases={"全部解禁", "全员解禁", "全解", "全体解"},
    priority=5,
    block=True,
    rule=admin_rule,
)


async def handle_mute_action(
    event: GroupMessageEvent, matcher: Matcher, action: str, duration: int = 0
):
    """
    统一处理禁言相关操作，包括用户禁言、解禁以及全员禁言、解禁。

    Args:
        event (GroupMessageEvent): 群消息事件对象。
        matcher (Matcher): 消息匹配器对象。
        action (str): 操作类型，可选值为 "禁言", "解禁", "全员禁言", "全员解禁"。
        duration (int, optional): 禁言时长，单位为秒，默认为 0。

    Returns:
        None: 直接通过 matcher 发送消息反馈操作结果。
    """
    # 检查机器人是否具有管理员权限
    if not await check_bot_admin_status(event.group_id):
        await matcher.send(Message("机器人没有管理员权限，无法执行此操作"))
        return

    try:
        if action in ["禁言", "解禁"]:
            # 解析目标用户的 QQ 号
            target_qq, error_msg = await parse_target_qq(event)
            if error_msg:
                await matcher.send(error_msg)
                return

            # 执行用户禁言或解禁操作
            success = await manage_user_mute(
                group_id=event.group_id, user_id=target_qq, duration=duration
            )
            msg = f"已{'禁言' if duration else '解禁'} [CQ:at,qq={target_qq}]" + (
                f" {duration}秒" if duration else ""
            )
        else:
            # 执行全员禁言或解禁操作
            success = await manage_group_mute_all(
                group_id=event.group_id, enable=action == "全员禁言"
            )
            msg = f"已{'开启' if action == '全员禁言' else '关闭'}全员禁言"

        # 检查操作是否成功
        if not success:
            raise Exception("操作执行失败")
        await matcher.send(Message(msg))
    except Exception as e:
        await matcher.send(Message(f"{action}失败: {str(e)}"))


@mute.handle()
async def handle_mute(event: GroupMessageEvent, matcher: Matcher):
    """
    处理禁言命令，提取禁言时长并调用统一处理函数。

    Args:
        event (GroupMessageEvent): 群消息事件对象。
        matcher (Matcher): 消息匹配器对象。

    Returns:
        None: 直接通过 matcher 发送消息反馈操作结果。
    """
    try:
        # 提取并验证禁言时长，确保在 1 到 2592000 秒之间
        mute_time = min(
            max(1, int(event.message.extract_plain_text().strip().split()[-1])), 2592000
        )
        await handle_mute_action(event, matcher, "禁言", mute_time)
    except ValueError:
        await matcher.send(Message("禁言时间必须是大于0的数字"))


@unmute.handle()
async def handle_unmute(event: GroupMessageEvent, matcher: Matcher):
    """
    处理解禁命令，调用统一处理函数。

    Args:
        event (GroupMessageEvent): 群消息事件对象。
        matcher (Matcher): 消息匹配器对象。

    Returns:
        None: 直接通过 matcher 发送消息反馈操作结果。
    """
    await handle_mute_action(event, matcher, "解禁")


@mute_all.handle()
async def handle_mute_all(event: GroupMessageEvent, matcher: Matcher):
    """
    处理全员禁言命令，调用统一处理函数。

    Args:
        event (GroupMessageEvent): 群消息事件对象。
        matcher (Matcher): 消息匹配器对象。

    Returns:
        None: 直接通过 matcher 发送消息反馈操作结果。
    """
    await handle_mute_action(event, matcher, "全员禁言")


@unmute_all.handle()
async def handle_unmute_all(event: GroupMessageEvent, matcher: Matcher):
    """
    处理全员解禁命令，调用统一处理函数。

    Args:
        event (GroupMessageEvent): 群消息事件对象。
        matcher (Matcher): 消息匹配器对象。

    Returns:
        None: 直接通过 matcher 发送消息反馈操作结果。
    """
    await handle_mute_action(event, matcher, "全员解禁")
