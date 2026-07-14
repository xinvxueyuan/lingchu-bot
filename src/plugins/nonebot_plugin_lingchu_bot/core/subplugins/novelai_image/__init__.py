"""NovelAI image-generation nested subplugin."""

from nonebot.plugin import PluginMetadata

from ..contracts import (
    LocalizedText,
    MenuAvailability,
    MenuFeature,
    PlatformCapability,
    register_subplugin_menu_feature,
)
from .config import ensure_novelai_config_files

__plugin_meta__ = PluginMetadata(
    name="NovelAI image generation",
    description=(
        "Complete NovelAI generation, Director tools, utilities, and account API."
    ),
    usage="生图 <描述|子命令> / novelai-image <description|subcommand>",
    type="application",
    homepage="https://github.com/xinvxueyuan/lingchu-bot",
)

ensure_novelai_config_files()

from . import handler as handler

register_subplugin_menu_feature(
    MenuFeature(
        "novelai-image",
        "novelai_image",
        "entertainment",
        LocalizedText("NovelAI 生图", "NovelAI Image"),
        LocalizedText("<描述>", "<description>"),
        PlatformCapability.LLM_CHAT,
        (MenuAvailability("qq", "~onebot.v11"),),
    )
)
