"""LLM chat nested subplugin."""

from nonebot.plugin import PluginMetadata

from ..contracts import (
    LocalizedText,
    MenuAvailability,
    MenuFeature,
    PlatformCapability,
    register_subplugin_menu_feature,
)
from .config import ensure_chat_config_files

__plugin_meta__ = PluginMetadata(
    name="LLM Chat",
    description="Chat with AI using LLM providers.",
    usage="聊天 <文本> / chat <text>",
    type="application",
    homepage="https://github.com/xinvxueyuan/lingchu-bot",
)

ensure_chat_config_files()

from . import handler as handler

register_subplugin_menu_feature(
    MenuFeature(
        "chat",
        "chat",
        "entertainment",
        LocalizedText("与 AI 聊天", "Chat with AI"),
        LocalizedText("<文本>", "<text>"),
        PlatformCapability.LLM_CHAT,
        (MenuAvailability("qq", "~onebot.v11"),),
    )
)
