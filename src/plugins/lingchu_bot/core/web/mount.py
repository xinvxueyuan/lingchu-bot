from pathlib import Path

from fastapi.staticfiles import StaticFiles
from nonebot import get_driver
from nonebot.log import logger


def mount_static_files() -> None:
    """挂载静态资源文件"""
    # 获取 NoneBot 驱动器
    driver = get_driver()
    logger.info(f"当前驱动类型：{driver.type}")

    # 确保只在使用 FastAPI 驱动时才挂载
    if driver.type in {"fastapi", "fastapi+httpx+websockets"}:
        try:
            # 获取 FastAPI 的 app 实例
            from nonebot.drivers.fastapi import Driver

            if isinstance(driver, Driver):
                fastapi_app = driver.server_app

                # 构造静态资源目录的绝对路径
                plugin_dir = Path(__file__).parent  # 当前插件 __init__.py 所在目录

                # 定义需要挂载的静态资源目录列表
                # 格式: (URL路径前缀, 实际目录路径, 挂载名称)
                static_dirs = [
                    (
                        "/web",
                        plugin_dir / "lingchu-bot-rewebui" / "dist",
                        "lingchu_bot_rewebui",
                    ),
                    # 可以在这里添加更多需要挂载的目录
                    # ("/admin", plugin_dir / "admin-panel" / "dist", "admin_panel"),
                    # ("/assets", plugin_dir / "assets", "static_assets"),
                ]

                # 挂载所有定义的静态资源目录
                for url_prefix, dir_path, mount_name in static_dirs:
                    if dir_path.exists() and dir_path.is_dir():
                        # 挂载静态资源
                        fastapi_app.mount(
                            url_prefix,  # URL 路径前缀
                            StaticFiles(directory=str(dir_path)),  # 静态文件实际目录
                            name=mount_name,  # 挂载名称
                        )
                        logger.info(
                            f"已挂载静态资源目录：{dir_path}，访问前缀为 {url_prefix}"
                        )
                    else:
                        logger.warning(f"静态资源目录不存在：{dir_path}，未挂载该目录")

                # 记录挂载完成
                logger.info("静态资源挂载完成")
            else:
                logger.warning("当前驱动不是 FastAPI 类型，无法挂载静态资源")
        except ImportError as e:
            logger.error(f"导入 FastAPI 相关模块失败：{e}")
        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"挂载静态资源时出错：{e}")
    else:
        logger.info("当前非 FastAPI 驱动，不挂载静态资源")
