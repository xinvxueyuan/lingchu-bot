from pydantic import BaseModel


# 所有配置项都可以在本插件data目录下的各个ini配置文件手动修改
# ini配置文件的配置项会覆盖此处相应配置项的值

class Config(BaseModel):
    root_id: str = '' #主人(最高权限用户)QQ号,可以是多个，用英文逗号隔开
    root_name: str = '主人' #机器人对最高权限用户的称呼
    bot_state: bool = False #机器人插件全局状态，True为开启，False为关闭(默认)
    bot_id: str = '' #机器人QQ号（自动获取）
    bot_name: str = '灵初' #机器人昵称（覆盖QQ原始昵称）
    log_state: bool = False #是否开启日志记录，True为开启，False为关闭(默认)
    log_id: str = '' #机器人日志群群号（单个）