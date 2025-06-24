"""公告系统"""
from typing import Optional
import asyncio
from ..lib.basic import *
from ..lib.event import admin_rule
from ..lib.management import manage_group_notice, check_bot_admin_status
from ..lib.database import db_operation

CMD_ALIASES = {
    "发公告": {"发布公告", ("群公告",)},  # 添加一个元组元素
    "群发公告": {"全局公告", ("分群公告",)}  # 添加一个元组元素
}

bulletin = on_command("发公告", aliases=CMD_ALIASES["发公告"], priority=5, block=True, rule=admin_rule)
bulletin_all = on_command("群发公告", aliases=CMD_ALIASES["群发公告"], priority=5, block=True, rule=admin_rule)

MAX_CONCURRENT = 5
SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT)

async def send_notice(group_id: int, content: str, image: Optional[str] = None) -> bool:
    async with SEMAPHORE:
        try:
            return await manage_group_notice(group_id, content, image)
        except Exception:
            return False

async def batch_send(group_ids: list[int], content: str, image: Optional[str] = None) -> int:
    tasks = [send_notice(gid, content, image) for gid in group_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return sum(1 for r in results if r is True)

async def process_bulletin_content(event: GroupMessageEvent) -> tuple[str, Optional[str]]:
    image_seg = next((seg for seg in event.message if seg.type == "image"), None)
    image_url = image_seg.data.get("url") if image_seg else None
    
    content = "".join(
        seg.data["text"] if seg.type == "text" else ""
        for seg in event.message
    ).strip()
    
    for cmd in CMD_ALIASES:
        if content.startswith(cmd):
            content = content[len(cmd):].strip()
            break
    
    return content, image_url

async def send_bulletin(event: GroupMessageEvent, matcher: Matcher, all_groups: bool = False) -> None:
    if not await check_bot_admin_status(event.group_id):
        await matcher.send("机器人无管理员权限，无法发送公告")
        return
    
    content, image_url = await process_bulletin_content(event)
    if not content and not image_url:
        await matcher.send("公告内容不能为空")
        return

    if not all_groups:
        success = await manage_group_notice(event.group_id, content, image_url)
        await matcher.send("公告发送成功" if success else "公告发送失败")
        return

    db_result = await db_operation(operation_type="query", table_name="groups", columns="id")
    if not isinstance(db_result, list) or not db_result:
        await matcher.send("获取群组列表失败")
        return
    
    success = await batch_send([row[0] for row in db_result], content, image_url)
    await matcher.send(f"公告已发送到 {success}/{len(db_result)} 个群组")

@bulletin.handle()
@bulletin_all.handle()
async def _(event: GroupMessageEvent, matcher: Matcher):
    is_all = event.get_plaintext().strip().startswith("群发")
    if msg := await send_bulletin(event, matcher, is_all):
        await matcher.send(msg)