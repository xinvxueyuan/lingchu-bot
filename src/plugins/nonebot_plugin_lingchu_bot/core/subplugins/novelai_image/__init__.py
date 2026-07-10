"""NovelAI image-generation nested subplugin."""

from nonebot.plugin import PluginMetadata

from .config import ensure_novelai_config_files

__plugin_meta__ = PluginMetadata(
    name="NovelAI image generation",
    description="Convert user descriptions and generate one NovelAI image.",
    usage="生图 <描述> / novelai-image <description>",
    type="application",
    homepage="https://github.com/xinvxueyuan/lingchu-bot",
)

ensure_novelai_config_files()

from . import handler as handler
