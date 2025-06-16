# 菜单功能
from ..lib.basic import *
from ..lib.configure import *
from ..lib.event import is_group_admin
globalmenu = on_command("菜单", priority=15, block=True)
membermenu = on_command("成员管理", priority=15, block=True)
speechmenu = on_command("发言管理", priority=15, block=True)
noticemenu = on_command("公告系统", priority=15, block=True)
listmenu = on_command("名单系统", priority=15, block=True)
permissionmenu = on_command("权限管理", priority=15, block=True)
timemenu = on_command("定时任务", priority=15, block=True)
selfmenu = on_command("自身撤回", priority=15, block=True)
remotemenu = on_command("远程系统", priority=15, block=True)
logmenu = on_command("操作日志", priority=15, block=True)

def check_menu_config() -> tuple[bool, str]:
    """
    检查菜单配置文件是否存在
    
    Returns:
        tuple[bool, str]: (文件是否存在, 规范化后的文件路径)
    """
    menu_path = os.path.join(os.path.dirname(__file__), '../../data/全局_设置/菜单.ini')
    menu_path = os.path.normpath(menu_path)
    return (os.path.exists(menu_path), menu_path)

async def read_and_send_menu(menu_path: str, section: str) -> bool:
    """
    读取并发送菜单内容
    
    Args:
        menu_path: 菜单文件路径
        section: ini文件中的section名称
        
    Returns:
        bool: 是否成功发送菜单
    """
    try:
        with open(menu_path, 'r', encoding='utf-8') as f:
            iniconfig.read_file(f)
        menu_content = eval(f'f"""{iniconfig.get(section, "Con").replace("/r", "\n").replace("{", "{plugin_config.")}"""')
        await globalmenu.send(menu_content)
        logger.info(f"发送{section}菜单")
        return True
    except Exception as e:
        await globalmenu.send("读取菜单配置时出错")
        logger.error(f"读取菜单配置时出错: {e}")
        return False

async def handle_menu_section(section: str, event: MessageEvent) -> None:
    """
    处理指定section的菜单请求
    
    Args:
        section: 要处理的菜单section名称
    """
        # 检查是否为群聊消息事件
    if not is_group_admin(event):
        await globalmenu.send("该命令仅限群聊使用")
        return
    
    exists, menu_path = check_menu_config()
    if not exists:
        await globalmenu.send("菜单配置文件不存在")
        logger.error(f"菜单配置文件不存在: {menu_path}")
        return
    
    await read_and_send_menu(menu_path, section)


@globalmenu.handle()
async def handle_globalmenu(event: MessageEvent):
    await handle_menu_section("菜单", event)

@membermenu.handle()
async def handle_membermenu(event: MessageEvent):
    await handle_menu_section("成员管理", event)

@speechmenu.handle()
async def handle_speechmenu(event: MessageEvent):
    await handle_menu_section("发言管理", event)

@noticemenu.handle()
async def handle_noticemenu(event: MessageEvent):
    await handle_menu_section("公告系统", event)

@listmenu.handle()
async def handle_listmenu(event: MessageEvent):
    await handle_menu_section("名单系统", event)

@permissionmenu.handle()
async def handle_permissionmenu(event: MessageEvent):
    await handle_menu_section("权限管理", event)

@timemenu.handle()
async def handle_timemenu(event: MessageEvent):
    await handle_menu_section("定时任务", event)

@selfmenu.handle()
async def handle_selfmenu(event: MessageEvent):
    await handle_menu_section("自身撤回", event)

@remotemenu.handle()
async def handle_remotemenu(event: MessageEvent):
    await handle_menu_section("远程系统", event)
    
@logmenu.handle()
async def handle_logmenu(event: MessageEvent):
    await handle_menu_section("操作日志", event)
