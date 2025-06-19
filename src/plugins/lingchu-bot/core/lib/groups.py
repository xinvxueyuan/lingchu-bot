from .basic import *
from nonebot import get_driver
from .database import db_operation
from nonebot import get_bots
from typing import Set

@get_driver().on_startup
async def check_and_create_groups_table():
    """初始化数据库表结构
    
    在NoneBot2启动时执行：
    1. 检查groups表是否存在
    2. 不存在则创建表，包含id字段作为主键
    """
    table_exists = await db_operation(
        operation_type="query", 
        table_name="groups", 
        columns="1", 
        condition="1=0"
    )
    if not table_exists:
        await db_operation(
            operation_type="create_table", 
            table_name="groups", 
            columns=["id INTEGER PRIMARY KEY"]
        )

async def update_groups_table():
    """同步群组数据
    
    功能：
    1. 获取所有机器人当前所在群组
    2. 与数据库中的群组记录对比
    3. 新增未记录的群组
    4. 删除已退出的群组
    """
    bots = get_bots()
    if not bots:
        return
    
    # 获取当前所有群组ID
    current_groups: Set[str] = set()
    for bot in bots.values():
        try:
            groups = await bot.get_group_list()
            current_groups.update(str(group['group_id']) for group in groups)
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

@get_driver().on_bot_connect
async def handle_bot_connect():
    """机器人连接事件处理"""
    await update_groups_table()

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