"""公告系统"""
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from typing import List, Optional
import asyncio

from ..lib.basic import on_command
from ..lib.event import admin_rule
from ..lib.management import manage_group_notice, check_bot_admin_status
from ..lib.database import db_operation

# 命令定义
bulletin = on_command("发公告", aliases={"发布公告", "群公告"}, priority=5, block=True, rule=admin_rule)
bulletin_all = on_command("群发公告", aliases={"全局公告", "分群公告"}, priority=5, block=True, rule=admin_rule)

MAX_CONCURRENT = 5
SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT)

async def send_notice(group_id: int, content: str) -> bool:
    """发送单条公告"""
    async with SEMAPHORE:
        try:
            return await manage_group_notice(group_id, content)
        except Exception:
            return False

async def batch_send(group_ids: List[int], content: str) -> int:
    """批量发送公告"""
    results = await asyncio.gather(
        *(send_notice(gid, content) for gid in group_ids),
        return_exceptions=True
    )
    return sum(1 for r in results if r is True)

async def send_bulletin(
    event: GroupMessageEvent, 
    matcher: Matcher, 
    all_groups: bool = False
) -> Optional[str]:
    """公告发送核心逻辑"""
    if not await check_bot_admin_status(event.group_id):
        return "机器人无管理员权限，无法发送公告"
    
    # 获取原始消息并去除命令部分
    raw_message = event.get_plaintext().strip()
    content = raw_message.replace("发公告", "").replace("发布公告", "").replace("群公告", "")
    content = content.replace("群发公告", "").replace("全局公告", "").replace("分群公告", "").strip()
    
    if not content:
        return "公告内容不能为空"

    if not all_groups:
        success = await manage_group_notice(event.group_id, content)
        return "公告发送成功" if success else "公告发送失败"

    db_result = await db_operation("query", "groups", "id")
    if not isinstance(db_result, list) or not db_result:
        return "获取群组列表失败"
    
    success = await batch_send([row[0] for row in db_result], content)
    return f"公告已发送到 {success}/{len(db_result)} 个群组"

@bulletin.handle()
async def _(event: GroupMessageEvent, matcher: Matcher):
    if msg := await send_bulletin(event, matcher):
        await matcher.send(msg)

@bulletin_all.handle()
async def _(event: GroupMessageEvent, matcher: Matcher):
    if msg := await send_bulletin(event, matcher, True):
        await matcher.send(msg)