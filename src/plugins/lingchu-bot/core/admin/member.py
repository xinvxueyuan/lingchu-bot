from typing import Optional, Tuple
from ..lib.basic import *
from ..lib.event import admin_rule
from ..lib.management import manage_group_kick
from .admin_utils import check_target_permission, parse_target_qq

kick = on_command("移出", aliases={"踢","踢出"}, priority=5, block=True, rule=admin_rule)


async def handle_kick_action(event: GroupMessageEvent, matcher: Matcher):
    """统一处理移出操作"""
    try:
        target_qq, error_msg = await parse_target_qq(event)
        if error_msg:
            await matcher.send(error_msg)
            return
        
        success = await manage_group_kick(group_id=event.group_id, user_id=target_qq)  # 修改为使用管理函数
        if success:
            await matcher.send(Message(f"已移出 [CQ:at,qq={target_qq}]"))
        else:
            await matcher.send(Message(f"移出 [CQ:at,qq={target_qq}] 失败"))
    except Exception as e:
        await matcher.send(Message(f"移出失败: {str(e)}"))

@kick.handle()
async def handle_kick(event: GroupMessageEvent, matcher: Matcher):
    await handle_kick_action(event, matcher)