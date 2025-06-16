from pydantic import BaseModel


# 所有配置项都可以在本插件data目录下的各个ini配置文件手动修改
# ini配置文件的配置项会覆盖此处相应配置项的值

class Config(BaseModel):
    plugins_state: bool = True #机器人插件全局状态，True为开启，False为关闭
    bot_id: str = '' #机器人QQ号（自动获取）
    bot_name: str = '灵初' #机器人昵称