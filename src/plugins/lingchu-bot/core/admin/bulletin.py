"""公告系统"""
from typing import Optional
import asyncio
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from ..lib.basic import on_command
from ..lib.event import admin_rule
from ..lib.management import manage_group_notice, check_bot_admin_status
from ..lib.database import db_operation

CMD_ALIASES = {
    "发公告": {"发布公告", ("群公告",)},
    "群发公告": {"全局公告", ("分群公告",)} 
}

bulletin = on_command("发公告", aliases=CMD_ALIASES["发公告"], priority=5, block=True, rule=admin_rule)
bulletin_all = on_command("群发公告", aliases=CMD_ALIASES["群发公告"], priority=5, block=True, rule=admin_rule)

MAX_CONCURRENT = 5
SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT)

async def send_notice(group_id: int, content: str, image: Optional[str] = None) -> bool:
    """发送单条公告"""
    async with SEMAPHORE:
        try:
            return await manage_group_notice(group_id, content, image)
        except Exception:
            return False

async def batch_send(group_ids: list[int], content: str, image: Optional[str] = None) -> int:
    """批量发送公告"""
    tasks = [send_notice(gid, content, image) for gid in group_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return sum(1 for r in results if r is True)

async def process_bulletin_content(event: GroupMessageEvent) -> tuple[str, Optional[str]]:
    """处理公告内容"""
    image_url = next((seg.data["url"] for seg in event.message if seg.type == "image"), None)
    content = event.get_plaintext().strip()
    
    for cmd in (*CMD_ALIASES["发公告"], *CMD_ALIASES["群发公告"]):
        content = content.replace(cmd, "").strip()
    
    return content, image_url

async def send_bulletin(event: GroupMessageEvent, matcher: Matcher, all_groups: bool = False) -> Optional[str]:
    """公告发送核心逻辑"""
    if not await check_bot_admin_status(event.group_id):
        return "机器人无管理员权限，无法发送公告"
    
    content, image_url = await process_bulletin_content(event)
    if not content and not image_url:
        return "公告内容不能为空"

    if not all_groups:
        success = await manage_group_notice(event.group_id, content, image_url)
        return "公告发送成功" if success else "公告发送失败"

    db_result = await db_operation(operation_type="query", table_name="groups", columns="id")
    if not isinstance(db_result, list) or not db_result:
        return "获取群组列表失败"
    
    success = await batch_send([row[0] for row in db_result], content, image_url)
    return f"公告已发送到 {success}/{len(db_result)} 个群组"

@bulletin.handle()
@bulletin_all.handle()
async def _(event: GroupMessageEvent, matcher: Matcher):
    is_all = event.get_plaintext().strip().startswith("群发")
    if msg := await send_bulletin(event, matcher, is_all):
        await matcher.send(msg)