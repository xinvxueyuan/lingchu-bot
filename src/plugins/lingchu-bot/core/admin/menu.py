""" 菜单 """
from ..lib.basic import *
from ..lib.event import admin_rule
from typing import Optional

# 菜单配置文件的路径
MENU_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../data/全局_设置/菜单.ini")
)


class MenuManager:
    def __init__(self):
        # 记录菜单配置文件的最后修改时间，初始值为 0
        self._last_mtime = 0
        # 存储命令处理器的字典，键为命令名称，值为处理器对象
        self.handlers = {}
        # 注册命令处理器
        self._register_handlers()

    def _load_config(self) -> Optional[ConfigParser]:
        """
        加载菜单配置文件。

        Returns:
            Optional[ConfigParser]: 若加载成功，返回 ConfigParser 对象；若失败，返回 None。
        """
        try:
            # 创建 ConfigParser 对象
            config = ConfigParser()
            # 以 UTF-8 编码打开菜单配置文件并读取内容
            with open(MENU_PATH, "r", encoding="utf-8") as f:
                config.read_file(f)
            return config
        except Exception as e:
            # 记录读取菜单配置文件失败的错误信息
            logger.error(f"读取菜单配置失败: {e}")
            return None

    def _check_reload(self) -> bool:
        """
        检查菜单配置文件是否有更新，若有则更新最后修改时间。

        Returns:
            bool: 若文件有更新，返回 True；否则返回 False。
        """
        try:
            # 获取菜单配置文件的当前修改时间
            current_mtime = os.path.getmtime(MENU_PATH)
            # 若当前修改时间大于记录的最后修改时间，说明文件有更新
            if current_mtime > self._last_mtime:
                self._last_mtime = current_mtime
                return True
        except Exception as e:
            # 记录检查菜单修改时间失败的错误信息
            logger.error(f"检查菜单修改时间失败: {e}")
        return False

    async def _send_menu(self, section: str) -> bool:
        """
        发送指定菜单部分的内容。

        Args:
            section (str): 菜单配置文件中的章节名称。

        Returns:
            bool: 若发送成功，返回 True；否则返回 False。
        """
        # 加载菜单配置文件
        config = self._load_config()
        if not config:
            return False

        try:
            # 获取指定章节的内容，并将 /r 替换为换行符
            content = config.get(section, "Con").replace("/r", "\n")
            # 通过对应的处理器发送菜单内容
            await self.handlers[section].send(content)
            return True
        except Exception as e:
            # 发送读取菜单配置出错的提示信息
            await self.handlers[section].send(f"读取{section}菜单配置时出错")
            # 记录读取菜单配置出错的错误信息
            logger.error(f"读取{section}菜单配置时出错: {e}")
            return False

    def _register_handlers(self):
        """
        注册命令处理器，清理旧处理器并注册新处理器。
        """
        # 加载菜单配置文件
        config = self._load_config()
        if not config:
            return

        # 清理旧的命令处理器
        for handler in self.handlers.values():
            handler.destroy()
        self.handlers.clear()

        # 注册新的命令处理器
        for section in config.sections():
            # 创建命令处理器
            handler = on_command(section, rule=admin_rule, priority=15, block=True)
            self.handlers[section] = handler

            @handler.handle()
            async def handle(event: MessageEvent, sec=section):
                """
                处理命令事件，检查菜单配置文件是否更新，若更新则重新注册处理器并发送菜单内容。

                Args:
                    event (MessageEvent): 消息事件对象。
                    sec (str): 菜单配置文件中的章节名称，默认为当前循环的章节名。
                """
                if self._check_reload():
                    self._register_handlers()
                await self._send_menu(sec)


# 创建菜单管理器实例
menu_manager = MenuManager()
