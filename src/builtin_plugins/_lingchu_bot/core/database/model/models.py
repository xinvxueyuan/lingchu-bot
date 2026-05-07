"""数据库模型"""

from nonebot import require

require("nonebot_plugin_orm")

from nonebot_plugin_orm import Model
from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship


class LoginInfo(Model):
    """配置信息"""

    id: Mapped[int] = mapped_column(primary_key=True)
    login_id: Mapped[int] = mapped_column(unique=True, index=True)
    login_name: Mapped[str] = mapped_column(index=True)
    login_status: Mapped[bool] = mapped_column(index=True, default=False)
    feat_status: Mapped[bool] = mapped_column(index=True, default=False)
    silent_mode: Mapped[bool] = mapped_column(index=True, default=False)
    loaded_plugins: Mapped[list[str]] = mapped_column(JSON, default=list)


class UiConfig(Model):
    """可视化配置"""

    id: Mapped[int] = mapped_column(primary_key=True)
    ui_enabled: Mapped[bool] = mapped_column(default=True, index=True)
    ui_token: Mapped[str] = mapped_column(default="", index=True)


class GlobalAdminUser(Model):
    """全局管理员用户"""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(unique=True, index=True)
    permission: Mapped[int] = mapped_column(default=0, index=True)


class GlobalConfig(Model):
    """全局管理配置"""

    id: Mapped[int] = mapped_column(primary_key=True)


class GlobalGroupConfig(Model):
    """全局群聊配置"""

    id: Mapped[int] = mapped_column(primary_key=True)
    # 全局黑名单
    blacklist: Mapped[list[int]] = mapped_column(JSON, default=list)
    # 全局管理员
    admin_list: Mapped[list[int]] = mapped_column(JSON, default=list)


class GlobalChatConfig(Model):
    """全局聊天配置"""

    id: Mapped[int] = mapped_column(primary_key=True)
    # 全局黑名单
    blacklist: Mapped[list[int]] = mapped_column(JSON, default=list)
    # 全局管理员
    admin_list: Mapped[list[int]] = mapped_column(JSON, default=list)


class GroupList(Model):
    """群聊列表（群组列表）"""

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(unique=True, index=True)
    state: Mapped[int] = mapped_column(default=0)
    group_config: Mapped["GroupConfig"] = relationship(
        back_populates="group",
        uselist=False,
        cascade="all, delete-orphan",
    )


class GroupConfig(Model):
    """单群配置"""

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("lingchu_bot_grouplist.group_id"), unique=True
    )
    group: Mapped["GroupList"] = relationship(back_populates="group_config")
    blacklist: Mapped[list[int]] = mapped_column(JSON, default=list)
    admin_list: Mapped[list[int]] = mapped_column(JSON, default=list)


class ChatList(Model):
    """聊天列表（好友列表）"""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(unique=True, index=True)
    nickname: Mapped[str] = mapped_column(default="")
    remark: Mapped[str] = mapped_column(nullable=True)
    state: Mapped[bool] = mapped_column(default=False)
    chat_config: Mapped["ChatConfig"] = relationship(
        back_populates="chat", uselist=False, cascade="all, delete-orphan"
    )


class ChatConfig(Model):
    """聊天配置（好友聊天）"""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("lingchu_bot_chatlist.user_id"), unique=True
    )
    chat: Mapped["ChatList"] = relationship(back_populates="chat_config")
