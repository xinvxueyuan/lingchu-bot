"""NovelAI image-generation nested subplugin."""

from nonebot.plugin import PluginMetadata

from ..contracts import register_subplugin_menu_feature
from .config import ensure_novelai_config_files

__plugin_meta__ = PluginMetadata(
    name="NovelAI image generation",
    description="Convert user descriptions and generate one NovelAI image.",
    usage="生图 <描述> / novelai-image <description>",
    type="application",
    homepage="https://github.com/xinvxueyuan/lingchu-bot",
)

ensure_novelai_config_files()

from ....handle.menu import LocalizedText, MenuAvailability, MenuFeature
from ....platforms import PlatformCapability
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
