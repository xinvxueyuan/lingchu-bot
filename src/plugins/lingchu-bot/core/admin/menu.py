# 菜单功能
from ..lib.basic import *
from ..lib.configure import *

globalmenu = on_command("菜单", priority=15, block=True)

@globalmenu.handle()
async def handle_function():
    menu_path = os.path.join(os.path.dirname(__file__), '../../data/全局_设置/菜单.ini')
    menu_path = os.path.normpath(menu_path)
    
    if not os.path.exists(menu_path):
        await globalmenu.send("菜单配置文件不存在")
        logger.error(f"菜单配置文件不存在: {menu_path}")
        return
    
    try:
        with open(menu_path, 'r', encoding='utf-8') as f:
            iniconfig.read_file(f)
        menu_content = eval(f'f"""{iniconfig.get("菜单", "Con").replace("/r", "\n").replace("{", "{plugin_config.")}"""')
        await globalmenu.send(menu_content)
        logger.info("发送全局菜单")
    except Exception as e:
        await globalmenu.send("读取菜单配置时出错")
        logger.error(f"读取菜单配置时出错: {e}")
