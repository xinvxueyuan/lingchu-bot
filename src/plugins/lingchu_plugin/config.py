from pydantic import BaseModel



class Config(BaseModel):
    bot_state: bool = False #机器人插件全局状态，True为开启，False为关闭
    root_id: str = '' #主人(系统超级管理员)QQ号,可以是多个，用英文逗号隔开
    bot_id: str = '' #机器人QQ号(选填，不填则自动获取),