from ..lib.basic import *
from ..lib.event import admin_rule
from typing import Optional

MENU_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), 
    '../../data/全局_设置/菜单.ini'
))

class MenuManager:
    def __init__(self):
        self._last_mtime = 0
        self.handlers = {}
        self._register_handlers()

    def _load_config(self) -> Optional[ConfigParser]:
        try:
            config = ConfigParser()
            with open(MENU_PATH, 'r', encoding='utf-8') as f:
                config.read_file(f)
            return config
        except Exception as e:
            logger.error(f"读取菜单配置失败: {e}")
            return None

    def _check_reload(self) -> bool:
        try:
            current_mtime = os.path.getmtime(MENU_PATH)
            if current_mtime > self._last_mtime:
                self._last_mtime = current_mtime
                return True
        except Exception as e:
            logger.error(f"检查菜单修改时间失败: {e}")
        return False

    async def _send_menu(self, section: str) -> bool:
        config = self._load_config()
        if not config:
            return False
            
        try:
            content = config.get(section, "Con").replace("/r", "\n")
            await self.handlers[section].send(content)
            return True
        except Exception as e:
            await self.handlers[section].send(f"读取{section}菜单配置时出错")
            logger.error(f"读取{section}菜单配置时出错: {e}")
            return False

    def _register_handlers(self):
        config = self._load_config()
        if not config:
            return
            
        # 清理旧处理器
        for handler in self.handlers.values():
            handler.destroy()
        self.handlers.clear()
        
        # 注册新处理器
        for section in config.sections():
            handler = on_command(section, rule=admin_rule, priority=15, block=True)
            self.handlers[section] = handler
            
            @handler.handle()
            async def handle(event: MessageEvent, sec=section):
                if self._check_reload():
                    self._register_handlers()
                await self._send_menu(sec)

menu_manager = MenuManager()