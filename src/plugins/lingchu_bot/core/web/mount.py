import threading
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from nonebot import get_driver, get_plugin_config
from nonebot.log import logger

from ...config import Config


def mount_static_files() -> None:
    driver = get_driver()
    logger.info(f"当前驱动类型：{driver.type}")
    try:
        cfg = get_plugin_config(Config)
        if not getattr(cfg, "web_static_enabled", True):
            logger.info("静态应用未启用")
            return

        plugin_dir = Path(__file__).parent
        static_dirs = [
            (
                "/web",
                plugin_dir / "webui" / "lingchu-bot-rewebui" / "dist",
                "lingchu_bot_rewebui",
            ),
        ]

        app = FastAPI()
        mounted = False
        for url_prefix, dir_path, mount_name in static_dirs:
            if dir_path.exists() and dir_path.is_dir():
                app.mount(
                    url_prefix, StaticFiles(directory=str(dir_path)), name=mount_name
                )
                logger.info(f"已挂载静态资源目录：{dir_path}，访问前缀为 {url_prefix}")
                mounted = True
            else:
                logger.warning(f"静态资源目录不存在：{dir_path}，未挂载该目录")

        if not mounted:
            logger.warning("未找到可挂载的静态资源目录")
            return

        host = getattr(cfg, "web_static_host", "127.0.0.1")
        port = int(getattr(cfg, "web_static_port", 8081))

        def run_server() -> None:
            uvicorn.run(app, host=host, port=port, log_level="info")

        threading.Thread(target=run_server, daemon=True).start()
        logger.info(f"静态应用已启动: http://{host}:{port}")
    except ImportError as e:
        logger.error(f"导入相关模块失败：{e}")
    except (OSError, ValueError, RuntimeError) as e:
        logger.error(f"挂载静态资源时出错：{e}")
