from ..lib.basic import *
from ..lib.event import admin_rule
from ..lib.management import manage_group_kick, check_bot_admin_status
from .admin_utils import parse_target_qq

kick = on_command("移出", aliases={"踢","踢出"}, priority=5, block=True, rule=admin_rule)


async def handle_kick_action(event: GroupMessageEvent, matcher: Matcher):
    """统一处理移出操作"""
    try:
        if not await check_bot_admin_status(event.group_id):
            await matcher.send("机器人无管理员权限，无法执行移出操作")
            return
            
        target_qq, error_msg = await parse_target_qq(event)
        if error_msg:
            await matcher.send(error_msg)
            return
        
        success = await manage_group_kick(group_id=event.group_id, user_id=target_qq)
        if success:
            await matcher.send(Message(f"已移出 [CQ:at,qq={target_qq}]"))
        else:
            await matcher.send(Message(f"移出 [CQ:at,qq={target_qq}] 失败"))
    except Exception as e:
        await matcher.send(Message(f"移出失败: {str(e)}"))

@kick.handle()
async def handle_kick(event: GroupMessageEvent, matcher: Matcher):
    await handle_kick_action(event, matcher)