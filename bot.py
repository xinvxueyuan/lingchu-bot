import nonebot

# from nonebot.adapters.discord import Adapter as DISCORDAdapter
# from nonebot.adapters.github import Adapter as GITHUBAdapter
from nonebot.adapters.milky import Adapter as MILKYAdapter

# from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter
# from nonebot.adapters.onebot.v12 import Adapter as ONEBOT_V12Adapter
# from nonebot.adapters.telegram import Adapter as TELEGRAMAdapter
from nonebot.internal.driver.abstract import Driver

init_config: dict[str, bool | str] = {
    "LOCALSTORE_USE_CWD": True,
}
nonebot.init(init_config=init_config)

driver: Driver = nonebot.get_driver()
# driver.register_adapter(adapter=ONEBOT_V11Adapter)
# driver.register_adapter(adapter=ONEBOT_V12Adapter)
# driver.register_adapter(adapter=GITHUBAdapter)
driver.register_adapter(adapter=MILKYAdapter)
# driver.register_adapter(adapter=TELEGRAMAdapter)
# driver.register_adapter(adapter=DISCORDAdapter)


nonebot.load_from_toml(file_path="pyproject.toml")
nonebot.load_plugins("src/builtin_plugins")

if __name__ == "__main__":
    nonebot.run()
