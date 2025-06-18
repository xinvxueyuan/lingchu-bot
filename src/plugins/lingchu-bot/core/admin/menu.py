# 菜单功能
from ..lib.basic import *
from ..lib.event import admin_rule


def load_menu_commands():
    menu_path = os.path.join(os.path.dirname(__file__), '../../data/全局_设置/菜单.ini')
    menu_path = os.path.normpath(menu_path)
    if not os.path.exists(menu_path):
        return {}
    
    config = ConfigParser()
    with open(menu_path, 'r', encoding='utf-8') as f:
        config.read_file(f)
    
    return {section: section for section in config.sections()}

menu_commands = load_menu_commands()

for cmd, section in menu_commands.items():
    globals()[f"{cmd.replace(' ', '_')}menu"] = on_command(cmd, rule=admin_rule, priority=15, block=True)

def check_menu_config() -> tuple[bool, str]:
    menu_path = os.path.join(os.path.dirname(__file__), '../../data/全局_设置/菜单.ini')
    menu_path = os.path.normpath(menu_path)
    return (os.path.exists(menu_path), menu_path)

async def read_and_send_menu(menu_path: str, section: str) -> bool:
    """读取并发送菜单内容"""
    try:
        config = ConfigParser()
        with open(menu_path, 'r', encoding='utf-8') as f:
            config.read_file(f)
        menu_content = config.get(section, "Con").replace("/r", "\n")
        await globals()[f"{section.replace(' ', '_')}menu"].send(menu_content)
        logger.info(f"发送{section}菜单")
        return True
    except Exception as e:
        await globals()[f"{section.replace(' ', '_')}menu"].send(f"读取{section}菜单配置时出错")
        logger.error(f"读取{section}菜单配置时出错: {e}")
        return False

_last_modified_time = 0
_menu_path = os.path.join(os.path.dirname(__file__), '../../data/全局_设置/菜单.ini')
_menu_path = os.path.normpath(_menu_path)

def check_reload_needed():
    global _last_modified_time
    try:
        current_mtime = os.path.getmtime(_menu_path)
        if current_mtime > _last_modified_time:
            _last_modified_time = current_mtime
            return True
    except:
        pass
    return False

async def handle_menu_section(section: str, event: MessageEvent) -> None:

    if check_reload_needed():
        reload_menu_commands()
    
    exists, menu_path = check_menu_config()
    if not exists:
        await globals()[f"{section.replace(' ', '_')}menu"].send("菜单配置文件不存在")
        logger.error(f"菜单配置文件不存在: {menu_path}")
        return
    
    await read_and_send_menu(menu_path, section)

# 添加重载函数
def reload_menu_commands():
    global menu_commands
    menu_commands = load_menu_commands()

    for cmd, section in menu_commands.items():
        cmd_key = f"{cmd.replace(' ', '_')}menu"
        if cmd_key not in globals():
            globals()[cmd_key] = on_command(cmd, rule=admin_rule, priority=15, block=True)
    
    register_menu_handlers()
    logger.info("菜单配置已重载")

try:
    _last_modified_time = os.path.getmtime(_menu_path)
except:
    pass

def register_menu_handlers():
    for cmd, section in menu_commands.items():
        cmd_handler = globals()[f"{cmd.replace(' ', '_')}menu"]
        
        @cmd_handler.handle()
        async def handler(event: MessageEvent, section=section):  # 通过默认参数固定section值
            await handle_menu_section(section, event)

register_menu_handlers()