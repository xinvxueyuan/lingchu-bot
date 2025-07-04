from nonebot_plugin_apscheduler import scheduler
from nonebot.matcher import Matcher
from datetime import datetime, timedelta
from typing import Optional, Literal, List, Tuple, Any, Dict
import re
import time
import random
from ..lib.basic import on_command, logger
from ..lib.event import admin_rule, GroupMessageEvent
from ..lib.database import db_operation
from ..lib.management import manage_group_mute_all, manage_group_notice
from ..auth.level_validator import check_qq_auth
from nonebot import get_driver
import asyncio

# 并发控制设置
MAX_CONCURRENT = 5
SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT)

# 命令别名配置
CMD_ALIASES = {
    "任务": {"设置任务", "计划任务", ("任务",)},
    "任务列表": {"查询任务", "查看任务", ("任务列表",)},
    "删除任务": {"取消任务", ("删除任务",)}
}

# 注册命令处理器
scheduler_cmd = on_command("任务", aliases=CMD_ALIASES["任务"], priority=5, block=True, rule=admin_rule)
list_cmd = on_command("任务列表", aliases=CMD_ALIASES["任务列表"], priority=5, block=True, rule=admin_rule)
delete_cmd = on_command("删除任务", aliases=CMD_ALIASES["删除任务"], priority=5, block=True, rule=admin_rule)

class SchedulerState:
    """管理用户会话状态"""
    __slots__ = ("states", "timeouts")
    
    def __init__(self):
        self.states: Dict[int, Dict] = {}
        self.timeouts: Dict[int, float] = {}

state = SchedulerState()
TIMEOUT = 60  # 会话超时时间(秒)

def parse_duration(duration_str: str) -> timedelta:
    """解析时间字符串为timedelta对象"""
    if not (match := re.fullmatch(r"(?:(\d+)天)?(?:(\d+)小时)?(?:(\d+)分钟)?(?:(\d+)秒)?", duration_str)):
        raise ValueError("无效的时间格式")
    return timedelta(
        days=int(match.group(1) or 0),
        hours=int(match.group(2) or 0),
        minutes=int(match.group(3) or 0),
        seconds=int(match.group(4) or 0)
    )

async def _add_job(task_id: str, exec_time: datetime, exec_type: Literal["once", "interval"], delta: timedelta) -> None:
    """添加任务到调度器"""
    if exec_type == "once":
        scheduler.add_job(
            execute_task,
            "date",
            run_date=exec_time,
            args=(task_id,),
            id=task_id,
            jobstore="default",
            executor="default",
            replace_existing=True
        )
    else:
        scheduler.add_job(
            execute_task,
            "interval",
            seconds=delta.total_seconds(),
            args=(task_id,),
            id=task_id,
            jobstore="default",
            executor="default",
            replace_existing=True
        )

async def add_task(
    task_type: Literal["global", "single"],
    exec_type: Literal["once", "interval"],
    duration: str,
    operation: str,
    group_id: int,
    operator_id: int,
    operation_value: Optional[str] = None,
    image_url: Optional[str] = None
) -> bool:
    """添加新任务"""
    try:
        if task_type == "global" and not check_qq_auth(str(operator_id)):
            return False
            
        delta = parse_duration(duration)
        exec_time = datetime.now() + delta
        task_id = f"{int(time.time())}{random.randint(100, 999)}"
        
        await db_operation(
            operation_type="insert",
            table_name="scheduled_tasks",
            data={
                "id": task_id,
                "group_id": group_id if task_type == "single" else None,
                "operation": operation,
                "operation_value": operation_value,
                "image_url": image_url,
                "exec_time": exec_time.isoformat(),
                "task_type": task_type,
                "interval": duration if exec_type == "interval" else None
            }
        )
        
        await _add_job(task_id, exec_time, exec_type, delta)
        return True
    except Exception as e:
        logger.error(f"添加任务失败: {e}")
        return False

async def _execute_operation(
    group_id: int, 
    operation: str, 
    operation_value: Optional[str] = None, 
    image_url: Optional[str] = None
) -> bool:
    """执行具体群操作"""
    try:
        if operation == "全员禁言":
            await manage_group_mute_all(group_id, True)
        elif operation == "全员解禁":
            await manage_group_mute_all(group_id, False)
        elif operation == "公告" and operation_value:
            return await manage_group_notice(group_id, operation_value, image_url)
        return True
    except Exception as e:
        logger.error(f"群 {group_id} 任务执行异常: {e}")
        return False

async def execute_task(task_id: str) -> None:
    try:
        if not (tasks := await db_operation(
            operation_type="query",
            table_name="scheduled_tasks",
            condition=f"id = '{task_id}'"
        )) or not isinstance(tasks, list):
            return
            
        task = tasks[0]
        operation, operation_value, image_url = task[2], task[3], task[4]
        
        if task[5] == "global":  # 全局任务
            db_result = await db_operation(
                operation_type="query", 
                table_name="groups", 
                columns="id"
            )
            
            if not isinstance(db_result, list) or not db_result:
                logger.warning("没有可用的群组执行全局任务")
                return
                
            for row in db_result:
                group_id = row[0]
                new_task_id = f"{task_id}_{group_id}"
                await db_operation(
                    operation_type="insert",
                    table_name="scheduled_tasks",
                    data={
                        "id": new_task_id,
                        "group_id": group_id,
                        "operation": operation,
                        "operation_value": operation_value,
                        "image_url": image_url,
                        "exec_time": task[4],
                        "task_type": "single",
                        "interval": task[7]
                    }
                )
                
                if task[7]:  # 间隔任务
                    delta = parse_duration(task[7])
                    await _add_job(new_task_id, datetime.fromisoformat(task[4]), "interval", delta)
                else:  # 单次任务
                    await _add_job(new_task_id, datetime.fromisoformat(task[4]), "once", timedelta())
            
            await db_operation(
                operation_type="delete",
                table_name="scheduled_tasks",
                condition=f"id = '{task_id}'"
            )
            scheduler.remove_job(task_id)
            
        else:  # 单群任务
            await _execute_operation(task[1], operation, operation_value, image_url)
            
            if task[7] is None:  # 单次任务执行后删除
                await db_operation(
                    operation_type="delete",
                    table_name="scheduled_tasks",
                    condition=f"id = '{task_id}'"
                )
    except Exception as e:
        logger.error(f"执行任务失败: {e}")

async def get_group_tasks(group_id: int) -> List[Tuple[Any, ...]]:
    """获取群组任务列表"""
    if (result := await db_operation(
        operation_type="query",
        table_name="scheduled_tasks",
        condition=f"(group_id = {group_id} OR task_type = 'global') AND exec_time > datetime('now')",
        order_by="exec_time ASC"
    )) and isinstance(result, list):
        return result
    return []

async def delete_task(task_id: str, operator_id: int) -> bool:
    """删除任务"""
    try:
        if not (tasks := await db_operation(
            operation_type="query",
            table_name="scheduled_tasks",
            condition=f"id = '{task_id}'"
        )) or not isinstance(tasks, list):
            return False
            
        if tasks[0][5] == "global" and not check_qq_auth(str(operator_id)):
            return False
            
        scheduler.remove_job(task_id)
        await db_operation(
            operation_type="delete",
            table_name="scheduled_tasks",
            condition=f"id = '{task_id}'"
        )
        return True
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        return False

async def handle_interaction(event: GroupMessageEvent, matcher: Matcher, options: Optional[List[str]] = None):
    """通用交互处理"""
    if event.get_plaintext().strip() == "退出":
        await clear_state(event.user_id)
        await matcher.finish("已取消操作")
    
    if await check_timeout(event.user_id):
        await clear_state(event.user_id)
        await matcher.finish("操作超时，请重新开始")
    
    if not (user_state := state.states.get(event.user_id)):
        await matcher.finish("会话已过期，请重新开始")
    
    await reset_timeout(event.user_id)
    text = event.get_plaintext().strip()
    
    if options and text not in options:
        await matcher.reject(f"请输入{'或'.join(options)}选择\n输入'退出'可取消操作")
    
    return user_state, text

async def check_timeout(user_id: int) -> bool:
    return (datetime.now().timestamp() - state.timeouts[user_id]) > TIMEOUT if user_id in state.timeouts else False

async def reset_timeout(user_id: int) -> None:
    state.timeouts[user_id] = datetime.now().timestamp()

async def clear_state(user_id: int) -> None:
    state.states.pop(user_id, None)
    state.timeouts.pop(user_id, None)

@get_driver().on_startup
async def clean_expired_tasks_on_startup():
    """启动时清理过期任务(包括单群和全局的单次任务)"""
    try:
        await db_operation(
            operation_type="clean_expired_tasks",
            table_name="scheduled_tasks"
        )
        logger.info("已清理所有过期定时任务")
    except Exception as e:
        logger.error(f"清理过期任务失败: {e}")

@scheduler_cmd.handle()
async def handle_scheduler(event: GroupMessageEvent, matcher: Matcher):
    state.states[event.user_id] = {"step": 1, "data": {}}
    await reset_timeout(event.user_id)
    await matcher.send("请选择任务范围:\n1. 全局\n2. 单群\n输入'退出'可随时取消操作")

@scheduler_cmd.got("scope")
async def handle_scope(event: GroupMessageEvent, matcher: Matcher):
    user_state, scope = await handle_interaction(event, matcher, ["1", "2"])
    user_state["data"]["task_type"] = "global" if scope == "1" else "single"
    user_state["step"] = 2
    await matcher.send("请选择任务类型:\n1. 定时\n2. 单次\n输入'退出'可随时取消操作")

@scheduler_cmd.got("exec_type")
async def handle_exec_type(event: GroupMessageEvent, matcher: Matcher):
    user_state, exec_type = await handle_interaction(event, matcher, ["1", "2"])
    user_state["data"]["exec_type"] = "interval" if exec_type == "1" else "once"
    user_state["step"] = 3
    await matcher.send("请输入执行时间(如: 1天12小时30分钟15秒):\n输入'退出'可随时取消操作")

@scheduler_cmd.got("duration")
async def handle_duration(event: GroupMessageEvent, matcher: Matcher):
    user_state, _ = await handle_interaction(event, matcher)
    try:
        parse_duration(event.get_plaintext().strip())
    except ValueError:
        await matcher.reject("时间格式无效，请重新输入(如: 1天12小时30分钟15秒)\n输入'退出'可取消操作")
    
    user_state["data"]["duration"] = event.get_plaintext().strip()
    user_state["step"] = 4
    await matcher.send("请选择操作:\n1. 全员禁言\n2. 全员解禁\n3. 公告\n输入'退出'可随时取消操作")

@scheduler_cmd.got("operation")
async def handle_operation(event: GroupMessageEvent, matcher: Matcher):
    user_state, operation = await handle_interaction(event, matcher, ["1", "2", "3"])
    ops = ["全员禁言", "全员解禁", "公告"]
    user_state["data"]["operation"] = ops[int(operation)-1]
    user_state["step"] = 5
    
    if operation == "3":
        await matcher.send("请输入公告内容:\n输入'退出'可随时取消操作")
    else:
        await handle_final(event, matcher)

@scheduler_cmd.got("operation_value")
async def handle_final(event: GroupMessageEvent, matcher: Matcher):
    user_state, _ = await handle_interaction(event, matcher)
    data = user_state["data"]
    
    if data["operation"] == "公告":
        image_seg = next((seg for seg in event.message if seg.type == "image"), None)
        data.update({
            "operation_value": "".join(
                seg.data["text"] if seg.type == "text" else ""
                for seg in event.message
            ).strip(),
            "image_url": image_seg.data.get("url") if image_seg else None
        })
    
    success = await add_task(
        task_type=data["task_type"],
        exec_type=data["exec_type"],
        duration=data["duration"],
        operation=data["operation"],
        group_id=event.group_id,
        operator_id=event.user_id,
        operation_value=data.get("operation_value"),
        image_url=data.get("image_url")
    )
    
    await matcher.finish("任务添加成功!" if success else "任务添加失败，可能是权限不足或参数错误")
    await clear_state(event.user_id)  # 使用 clear_state 清理所有状态

@list_cmd.handle()
async def handle_list(event: GroupMessageEvent, matcher: Matcher):
    if not (tasks := await get_group_tasks(event.group_id)):
        await matcher.send("当前没有定时任务")
        return
    
    msg = ["当前任务列表:"]
    for task in tasks:
        task_id, group_id, operation, operation_value, exec_time, task_type, interval, image_url = task
        
        task_type = "全局" if task_type == "global" else "单群"
        op_name = {
            "全员禁言": "全员禁言",
            "全员解禁": "全员解禁",
            "公告": f"公告: {operation_value}" if operation_value else "公告"
        }.get(operation, "未知操作")
        
        # 修复执行时间解析逻辑
        exec_time_str = "立即执行"
        try:
            if exec_time:
                # 统一处理字符串和datetime对象
                if isinstance(exec_time, str):
                    # 处理SQLite返回的时间字符串格式
                    if 'T' in exec_time:  # ISO格式
                        exec_time_str = datetime.fromisoformat(exec_time.replace('T', ' ')).strftime("%Y-%m-%d %H:%M:%S")
                    else:  # SQLite格式
                        exec_time_str = datetime.strptime(exec_time, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(exec_time, datetime):
                    exec_time_str = exec_time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.warning(f"解析执行时间失败: {e}")
            exec_time_str = "时间解析错误"
            
        # 修复间隔显示逻辑
        # 修改这里的判断条件，使用 interval 而不是 task[6]
        interval_str = ""
        if interval and interval != "None":
            try:
                delta = parse_duration(interval)
                interval_str = f"重复间隔: {delta.days}天{delta.seconds//3600}小时{(delta.seconds//60)%60}分钟{delta.seconds%60}秒"
            except ValueError:
                interval_str = f"重复间隔: {interval}"
        else:
            interval_str = "单次任务"
        
        msg.append(
            f"ID: {task_id}\n"
            f"类型: {task_type}\n"
            f"操作: {op_name}\n"
            f"执行时间: {exec_time_str}\n"
            f"{interval_str}"
        )
    
    await matcher.send("\n\n".join(msg))

@delete_cmd.handle()
async def handle_delete_start(event: GroupMessageEvent, matcher: Matcher):
    state.states[event.user_id] = {"step": 1, "data": {}}
    await reset_timeout(event.user_id)
    await matcher.send("请输入要删除的任务ID:\n输入'退出'可随时取消操作")

@delete_cmd.got("task_id")
async def handle_delete_confirm(event: GroupMessageEvent, matcher: Matcher):
    user_state, task_id = await handle_interaction(event, matcher)
    
    if not (tasks := await db_operation(
        operation_type="query",
        table_name="scheduled_tasks",
        condition=f"id = '{task_id}'"
    )) or not isinstance(tasks, list):
        await clear_state(event.user_id)
        await matcher.finish("任务不存在或已删除")
    
    task = tasks[0]
    user_state["data"]["task_id"] = task_id
    user_state["step"] = 2
    
    await matcher.send(
        f"确认删除以下任务吗？\n"
        f"ID: {task_id}\n"
        f"类型: {'全局' if task[5] == 'global' else '单群'}\n"
        f"操作: {'全员禁言' if task[2] == '全员禁言' else '全员解禁' if task[2] == '全员解禁' else f'公告: {task[3]}' if task[3] else '公告'}\n"
        f"执行时间: {task[4]}\n"
        f"{'重复间隔: ' + task[6] if task[6] else ''}\n\n"
        f"请输入 '确认' 或 '取消'"
    )

@delete_cmd.got("confirm")
async def handle_delete_execute(event: GroupMessageEvent, matcher: Matcher):
    user_state, confirm = await handle_interaction(event, matcher, ["确认", "取消"])
    
    if confirm == "取消":
        await clear_state(event.user_id)
        await matcher.finish("已取消删除操作")
    
    success = await delete_task(user_state["data"]["task_id"], event.user_id)
    await clear_state(event.user_id)
    await matcher.send("任务删除成功" if success else "任务删除失败，可能是权限不足")

    await clear_state(event.user_id) 