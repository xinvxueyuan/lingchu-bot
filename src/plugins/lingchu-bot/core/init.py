from .lib.state import check_plugins_state
from .lib.basic import *
import asyncio
from configparser import ConfigParser
from nonebot import on_notice
from nonebot.adapters.onebot.v11 import GroupIncreaseNoticeEvent, GroupDecreaseNoticeEvent

# 群成员变化事件处理器
group_change = on_notice(priority=10, block=False)

@group_change.handle()
async def handle_group_change(event: GroupIncreaseNoticeEvent | GroupDecreaseNoticeEvent):
    await update_group_ids()

async def update_group_ids():
    config = ConfigParser()
    os.makedirs('data/Groups', exist_ok=True)
    
    while True:
        try:
            bot = get_bot()
            group_list = await bot.get_group_list()
            if group_list:
                config['Groups'] = {'ids': '\n'.join(str(g['group_id']) for g in group_list)}
                with open('data/Groups/ID.ini', 'w') as f:
                    config.write(f)
        except Exception as e:
            logger.error(f"更新群列表失败: {e}")
        await asyncio.sleep(600)  # 改为10分钟(600秒)检查一次

if check_plugins_state():
    from .admin.index import *