from ..lib.basic import *
from ..lib.event import admin_rule
from .admin_utils import parse_target_qq
from ..lib.management import manage_user_mute, manage_group_mute_all, check_bot_admin_status

mute = on_command("禁言", aliases={"禁"}, priority=5, block=True, rule=admin_rule)
unmute = on_command("解禁", aliases={"解"}, priority=5, block=True, rule=admin_rule)
mute_all = on_command("全体禁言", aliases={"全部禁言", "全员禁言"}, priority=5, block=True, rule=admin_rule)
unmute_all = on_command("全体解禁", aliases={"全部解禁", "全员解禁"}, priority=5, block=True, rule=admin_rule)

async def handle_mute_action(event: GroupMessageEvent, matcher: Matcher, action: str, duration: int = 0):
    """统一处理禁言相关操作"""
    if not await check_bot_admin_status(event.group_id):
        await matcher.send(Message("机器人没有管理员权限，无法执行此操作"))
        return
        
    try:
        if action in ["禁言", "解禁"]:
            target_qq, error_msg = await parse_target_qq(event)
            if error_msg: 
                await matcher.send(error_msg)
                return
            
            success = await manage_user_mute(
                group_id=event.group_id,
                user_id=target_qq,
                duration=duration
            )
            msg = f"已{'禁言' if duration else '解禁'} [CQ:at,qq={target_qq}]" + (f" {duration}秒" if duration else "")
        else:
            success = await manage_group_mute_all(
                group_id=event.group_id,
                enable=action == "全员禁言"
            )
            msg = f"已{'开启' if action == '全员禁言' else '关闭'}全员禁言"
        
        if not success:
            raise Exception("操作执行失败")
        await matcher.send(Message(msg))
    except Exception as e: 
        await matcher.send(Message(f"{action}失败: {str(e)}"))

@mute.handle()
async def handle_mute(event: GroupMessageEvent, matcher: Matcher):
    try:
        mute_time = min(max(1, int(event.message.extract_plain_text().strip().split()[-1])), 2592000)
        await handle_mute_action(event, matcher, "禁言", mute_time)
    except ValueError:
        await matcher.send(Message("禁言时间必须是大于0的数字"))

@unmute.handle()
async def handle_unmute(event: GroupMessageEvent, matcher: Matcher):
    await handle_mute_action(event, matcher, "解禁")

@mute_all.handle()
async def handle_mute_all(event: GroupMessageEvent, matcher: Matcher):
    await handle_mute_action(event, matcher, "全员禁言")

@unmute_all.handle()
async def handle_unmute_all(event: GroupMessageEvent, matcher: Matcher):
    await handle_mute_action(event, matcher, "全员解禁")

