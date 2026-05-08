from pathlib import Path

import nonebot
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 获取全局配置
config = nonebot.get_driver().config

# 优先从配置读取数据库 URL，否则用默认路径
db_url = getattr(config, "sqlalchemy_database_url", None)
if not db_url:
    base_dir = Path(__file__).parent.parent.parent.parent.parent.parent
    default_db_path = (
        base_dir / "data" / "nonebot_plugin_orm" / "lc-bot_apscheduler_store_db.sqlite3"
    )
    db_url = f"sqlite:///{default_db_path}"

jobstores = {"default": SQLAlchemyJobStore(url=db_url)}

# 初始化调度器
scheduler = AsyncIOScheduler(jobstores=jobstores)
