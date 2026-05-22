from nonebot.internal.driver.abstract import Driver

from ..handle.command.mute import import_handle as mute_import_handle
from ..i18n import warm_translation_cache


async def startup() -> None:
    await warm_translation_cache()
    await mute_import_handle()


from nonebot import get_driver

driver: Driver = get_driver()


@driver.on_startup
async def do_something() -> None:
    # TODO: 这里可以放一些启动时需要执行的代码，比如预加载一些数据等
    pass


@driver.on_shutdown
async def do_something_else() -> None:
    # TODO: 这里可以放一些关闭时需要执行的代码，比如清理资源等
    pass


@driver.on_bot_connect
async def do_something_else_else() -> None:
    # TODO: 这里可以放一些机器人连接时需要执行的代码，比如发送欢迎消息等
    pass


@driver.on_bot_disconnect
async def do_something_else_else_else() -> None:
    # TODO: 这里可以放一些机器人断开连接时需要执行的代码，比如发送告别消息等
    pass
