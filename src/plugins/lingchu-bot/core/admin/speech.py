from typing import Optional, Tuple
from ..lib.basic import *
from ..lib.event import admin_rule
from ..auth.level_validator import check_qq_auth

mute = on_command("禁言", aliases={"禁"}, priority=5, block=True, rule=admin_rule)
unmute = on_command("解禁", aliases={"解"}, priority=5, block=True, rule=admin_rule)
mute_all = on_command("全体禁言", aliases={"全部禁言", "全员禁言"}, priority=5, block=True, rule=admin_rule)
unmute_all = on_command("全体解禁", aliases={"全部解禁", "全员解禁"}, priority=5, block=True, rule=admin_rule)
ban_monitor = on_notice(priority=10, block=False)

async def check_mute_permission(event: GroupMessageEvent, target_qq: int) -> Optional[Message]:
    if target_qq in {event.user_id, event.self_id}: return Message("不能禁言自己或机器人")
    try:
        member_info = await get_bot().get_group_member_info(group_id=event.group_id, user_id=target_qq, no_cache=True)
        if member_info.get("role") in {"owner", "admin"}: return Message("不能禁言群主或管理员")
        if check_qq_auth(str(target_qq)): return Message("无法对特殊权限用户执行禁言操作")
    except Exception: return Message("权限检查失败，禁止操作")

async def parse_target_qq(event: GroupMessageEvent) -> Tuple[int, Optional[Message]]:
    if not (target_qq := next((int(seg.data["qq"]) for seg in event.message if seg.type == "at" and seg.data.get("qq") != "all"), None)):
        return 0, Message("请使用标准格式：禁言@某人 时间(秒)")
    return (0, await check_mute_permission(event, target_qq)) if await check_mute_permission(event, target_qq) else (target_qq, None)

async def execute_group_action(group_id: int, matcher: Matcher, action_name: str, **kwargs):
    try:
        if "duration" in kwargs:
            await get_bot().set_group_ban(group_id=group_id, user_id=kwargs["user_id"], duration=kwargs["duration"])
            msg = (f"已解禁 [CQ:at,qq={kwargs['user_id']}]" if kwargs["duration"] == 0 
                  else f"已禁言 [CQ:at,qq={kwargs['user_id']}]({kwargs['user_id']}) {kwargs['duration']}秒")
        else:
            await get_bot().set_group_whole_ban(group_id=group_id, enable=kwargs["enable"])
            msg = f"已{'开启' if kwargs['enable'] else '关闭'}全员禁言"
        await matcher.send(Message(msg))
    except Exception as e: await matcher.send(Message(f"{action_name}失败: {str(e)}"))

async def handle_mute_action(event: GroupMessageEvent, matcher: Matcher, action: str, duration: Optional[int] = None):
    if action in ["禁言", "解禁"]:
        target_qq, error_msg = await parse_target_qq(event)
        if error_msg: await matcher.send(error_msg); return
        await execute_group_action(event.group_id, matcher, action, user_id=target_qq, duration=duration or 0)
    else:
        await execute_group_action(event.group_id, matcher, action, enable=action == "全员禁言")

@mute.handle()
async def handle_mute(event: GroupMessageEvent, matcher: Matcher):
    try:
        mute_time = min(max(1, int(event.message.extract_plain_text().strip().split()[-1])), 2592000)
        await handle_mute_action(event, matcher, "禁言", mute_time)
    except: await matcher.send(Message("禁言时间必须是大于0的数字"))

@unmute.handle()
async def handle_unmute(event: GroupMessageEvent, matcher: Matcher):
    await handle_mute_action(event, matcher, "解禁")

@mute_all.handle()
async def handle_mute_all(event: GroupMessageEvent, matcher: Matcher):
    await handle_mute_action(event, matcher, "全员禁言")

@unmute_all.handle()
async def handle_unmute_all(event: GroupMessageEvent, matcher: Matcher):
    await handle_mute_action(event, matcher, "全员解禁")

@ban_monitor.handle()
async def handle_ban_monitor(bot: Bot, event: GroupBanNoticeEvent):
    if event.sub_type == "ban" and event.duration > 0 and check_qq_auth(str(event.user_id)):
        try:
            await bot.set_group_ban(group_id=event.group_id, user_id=event.user_id, duration=0)
            operator_info = await bot.get_group_member_info(group_id=event.group_id, user_id=event.operator_id, no_cache=True)
            operator_name = operator_info.get("card") or operator_info.get("nickname")
            await bot.send_group_msg(group_id=event.group_id, message=f"检测到特殊权限用户被禁言，已自动解禁\n操作者: {operator_name}({event.operator_id})")
        except Exception as e: logger.error(f"自动解禁特殊权限用户失败: {str(e)}")