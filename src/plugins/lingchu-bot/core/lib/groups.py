from .basic import *
from nonebot import get_driver, on_notice, get_bots, require
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import GroupIncreaseNoticeEvent
from .database import db_operation
from typing import Set, Dict, Any
from .management import check_bot_admin_status

require("nonebot_plugin_apscheduler")

@get_driver().on_startup
async def check_and_create_groups_table() -> None:
    """初始化群组数据库表
    
    功能：
    1. 初始化数据库连接池
    2. 检查groups表是否存在，不存在则创建
    3. 启动定时同步任务(秒级)
    """
    from .database import init_db_pool
    
    init_db_pool()
 
    try:
        await db_operation(
            operation_type="query", 
            table_name="groups", 
            columns="1", 
            condition="1=0"
        )
    except ValueError as e:
        if "表不存在" in str(e):
            await db_operation(
                operation_type="create_table", 
                table_name="groups", 
                columns=["id INTEGER PRIMARY KEY"]
            )


async def update_groups_table() -> None:
    """同步群组数据到数据库"""
    try:
        logger.debug("开始执行群组数据同步...")
        bots = get_bots()
        if not bots:
            return
        
        current_groups: Set[str] = set()
        for bot in bots.values():
            try:
                groups = await bot.get_group_list()
                for group in groups:
                    if await check_bot_admin_status(group['group_id']):
                        current_groups.add(str(group['group_id']))
            except Exception as e:
                logger.warning(f"获取群组列表失败: {e}")
                continue
        
        db_result = await db_operation(
            operation_type="query", 
            table_name="groups", 
            columns="id"
        )
        db_groups: Set[str] = {str(row[0]) for row in db_result} if isinstance(db_result, list) else set()
        
        # 处理新增群组
        added = current_groups - db_groups
        for group_id in added:
            try:
                await db_operation(
                    operation_type="insert",
                    table_name="groups",
                    data={"id": int(group_id)}
                )
            except Exception as e:
                logger.error(f"新增群组 {group_id} 失败: {e}")
        
        # 处理已退出群组
        removed = db_groups - current_groups
        for group_id in removed:
            try:
                # 删除群组时同时删除该群的所有任务
                await db_operation(
                    operation_type="delete",
                    table_name="scheduled_tasks",
                    condition=f"group_id = {group_id}"
                )
                await db_operation(
                    operation_type="delete",
                    table_name="groups",
                    condition=f"id = {group_id}"
                )
            except Exception as e:
                logger.error(f"删除群组 {group_id} 失败: {e}")
                
        logger.debug(f"群组数据同步完成: 新增 {len(added)} 个, 删除 {len(removed)} 个")
    except Exception as e:
        logger.error(f"群组数据同步失败: {e}")
        raise

@on_notice
async def handle_group_increase(event: GroupIncreaseNoticeEvent) -> bool:
    """处理群成员增加事件"""
    try:
        if event.user_id == event.self_id:
            await db_operation(
                operation_type="insert",
                table_name="groups",
                data={"id": event.group_id}
            )
            logger.info(f"机器人被邀请加入群 {event.group_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"处理群成员增加事件失败: {e}")
        return False

async def execute_all_groups(operation: str, **kwargs: Any) -> Dict[int, bool]:
    """在所有群组中执行指定操作
    
    参数:
        operation: 要执行的操作名称(来自management模块)
        **kwargs: 传递给操作的参数
        
    返回:
        字典格式: {群组ID: 操作是否成功}
    """
    import inspect
    from . import management
    
    operation_map = {
        name: func 
        for name, func in inspect.getmembers(management, inspect.iscoroutinefunction)
        if not name.startswith('_')
    }
    
    if operation not in operation_map:
        raise ValueError(f"无效操作: {operation}. 可用操作: {', '.join(operation_map.keys())}")
    
    db_result = await db_operation(
        operation_type="query",
        table_name="groups",
        columns="id"
    )
    if not isinstance(db_result, list):
        return {}
    
    func = operation_map[operation]
    results: Dict[int, bool] = {}
    
    for row in db_result:
        group_id = row[0]
        try:
            kwargs['group_id'] = group_id
            results[group_id] = await func(**kwargs)
        except Exception as e:
            logger.error(f"群组 {group_id} 执行 {operation} 失败: {e}")
            results[group_id] = False
    
    return results

