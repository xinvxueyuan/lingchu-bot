# 修正后的导入方式
from nonebot import on
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
import asyncio
from nonebot.log import logger
# 创建消息监听器（支持发送/接收）
message_listener = on(type="message")

@message_listener.handle()
async def handle_all_messages(bot: Bot, event: MessageEvent):
    # 仅处理机器人发送的消息
    if event.post_type != "message_sent": 
        return
    
    # 仅处理群消息（可选）
    if not hasattr(event, "group_id") or not event.group_id:
        return

    # 提取关键信息
    message_id = event.message_id
    group_id = event.group_id

    # 异步延迟撤回
    async def withdraw():
        await asyncio.sleep(3)
        try:
            await bot.delete_msg(message_id=message_id)
            logger.success(f"已撤回消息 {message_id}")
        except Exception as e:
            logger.error(f"撤回失败: {e}")

    asyncio.create_task(withdraw())