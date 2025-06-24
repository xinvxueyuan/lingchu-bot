from .basic import *
from nonebot import get_driver
from .database import db_operation
from nonebot import get_bots
from typing import Set
from nonebot_plugin_apscheduler import scheduler
from .management import check_bot_admin_status


@get_driver().on_startup
async def check_and_create_groups_table():
    """初始化数据库表结构"""
    # 确保数据库连接池已初始化
    from .database import init_db_pool
    init_db_pool()
    
    try:
        # 尝试查询表是否存在
        await db_operation(
            operation_type="query", 
            table_name="groups", 
            columns="1", 
            condition="1=0"
        )
    except ValueError as e:
        if "表不存在" in str(e):
            # 如果表不存在则创建
            await db_operation(
                operation_type="create_table", 
                table_name="groups", 
                columns=["id INTEGER PRIMARY KEY"]
            )
        else:
            raise
    
    scheduler.add_job(
        update_groups_table,
        "interval",
        seconds=60,
        id="update_groups_table",
        replace_existing=True
    )

async def update_groups_table():
    try:
        logger.debug("开始执行群组数据同步...")
        """同步群组数据
        
        功能：
        1. 获取所有机器人当前所在群组
        2. 检查机器人是否有管理权限
        3. 与数据库中的群组记录对比
        4. 新增未记录的群组
        5. 删除已退出的群组
        """
        bots = get_bots()
        if not bots:
            return
        
        # 获取当前所有群组ID（仅记录有管理权限的群）
        current_groups: Set[str] = set()
        for bot in bots.values():
            try:
                groups = await bot.get_group_list()
                for group in groups:
                    # 检查机器人是否有管理权限
                    if await check_bot_admin_status(group['group_id']):
                        current_groups.add(str(group['group_id']))
            except Exception:
                continue
        
        # 获取数据库中的群组记录
        db_result = await db_operation(
            operation_type="query", 
            table_name="groups", 
            columns="id"
        )
        db_groups: Set[str] = set()
        if isinstance(db_result, list):
            db_groups = {str(row[0]) for row in db_result}
        
        # 同步差异数据
        for group_id in current_groups - db_groups:
            await db_operation(
                operation_type="insert",
                table_name="groups",
                data={"id": int(group_id)}
            )
        
        for group_id in db_groups - current_groups:
            await db_operation(
                operation_type="delete",
                table_name="groups",
                condition=f"id = {group_id}"
            )
        logger.debug("群组数据同步完成")
    except Exception as e:
        logger.error(f"群组数据同步失败: {e}")
        raise


@on_notice
async def handle_group_increase(event: GroupIncreaseNoticeEvent):
    """处理机器人入群事件
    
    当检测到机器人加入新群时，自动记录群号到数据库
    """
    if event.user_id == int(get_driver().config.bot_id):
        await db_operation(
            operation_type="insert",
            table_name="groups",
            data={"id": event.group_id}
        )
    return True

async def execute_all_groups(operation: str, **kwargs):
    """批量执行群组操作
    
    参数:
        operation: management模块中的异步函数名
        **kwargs: 传递给操作的参数
        
    返回:
        dict: 各群组的执行结果 {群号: 成功/失败}
    """
    import inspect
    from importlib import import_module
    from . import management
    
    # 获取所有可用的管理操作
    operation_map = {
        name: func 
        for name, func in inspect.getmembers(management, inspect.iscoroutinefunction)
        if not name.startswith('_')
    }
    
    if operation not in operation_map:
        raise ValueError(f"无效操作: {operation}. 可用操作: {', '.join(operation_map.keys())}")
    
    # 获取所有群组ID
    db_result = await db_operation(
        operation_type="query",
        table_name="groups",
        columns="id"
    )
    if not isinstance(db_result, list):
        return {}
    
    func = operation_map[operation]
    results = {}
    
    # 遍历执行
    for row in db_result:
        group_id = row[0]
        try:
            if 'group_id' not in kwargs:
                kwargs['group_id'] = group_id
            results[group_id] = await func(**kwargs)
        except Exception:
            results[group_id] = False
    
    return results

