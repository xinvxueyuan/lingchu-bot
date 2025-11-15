from nonebot_plugin_orm import Model
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AdminUser(Model):
    """管理员用户"""

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[int] = mapped_column(unique=True)
    permission: Mapped[int] = mapped_column(default=0)


class GroupList(Model):
    """群列表"""

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    state: Mapped[int] = mapped_column(default=0)
    config: Mapped["GroupConfig"] = relationship(back_populates="group", uselist=False)


class GroupConfig(Model):
    """群配置"""

    id: Mapped[int] = mapped_column(primary_key=True)
    group_name: Mapped[str] = mapped_column(foreign_key="grouplist.name", unique=True)
    group: Mapped["GroupList"] = relationship(back_populates="config")


class ChatList(Model):
    """聊天列表"""

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    state: Mapped[int] = mapped_column(default=0)


class ChatConfig(Model):
    """聊天配置"""

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_name: Mapped[str] = mapped_column(foreign_key="chatlist.name", unique=True)
    chat: Mapped["ChatList"] = relationship(back_populates="config")
