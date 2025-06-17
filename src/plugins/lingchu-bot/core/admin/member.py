from typing import Optional, Tuple
from ..lib.basic import *
from ..lib.event import admin_rule
from ..auth.level_validator import check_qq_auth

kick = on_command("移出", aliases={"踢","踢出"}, priority=5, block=True, rule=admin_rule)

async def check_kick_permission(event: GroupMessageEvent, target_qq: int) -> Optional[Message]:
    if target_qq in {event.user_id, event.self_id}: return Message("不能移出自己或机器人")
    try:
        member_info = await get_bot().get_group_member_info(group_id=event.group_id, user_id=target_qq, no_cache=True)
        if member_info.get("role") in {"owner", "admin"}: return Message("不能移出群主或管理员")
        if check_qq_auth(str(target_qq)): return Message("无法对特殊权限用户执行移出操作")
    except Exception: return Message("权限检查失败，禁止操作")

async def parse_kick_target_qq(event: GroupMessageEvent) -> Tuple[int, Optional[Message]]:
    if not (target_qq := next((int(seg.data["qq"]) for seg in event.message if seg.type == "at" and seg.data.get("qq") != "all"), None)):
        return 0, Message("请使用标准格式：移出@某人")
    return (0, await check_kick_permission(event, target_qq)) if await check_kick_permission(event, target_qq) else (target_qq, None)

async def execute_kick_action(group_id: int, matcher: Matcher, user_id: int):
    try:
        await get_bot().set_group_kick(group_id=group_id, user_id=user_id)
        await matcher.send(Message(f"已移出 [CQ:at,qq={user_id}]"))
    except Exception as e:
        await matcher.send(Message(f"移出失败: {str(e)}"))

@kick.handle()
async def handle_kick(event: GroupMessageEvent, matcher: Matcher):
    target_qq, error_msg = await parse_kick_target_qq(event)
    if error_msg: 
        await matcher.send(error_msg)
        return
    await execute_kick_action(event.group_id, matcher, target_qq)