"""Locale-aware OneBot V11 image command."""

import secrets

from arclet.alconna import Alconna, Args, Nargs
from nonebot import logger, require

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna

from ..contracts import (
    get_subplugin_trigger,
    image_message,
    register_subplugin_handler,
)
from .client import MissingNovelAITokenError, NovelAIError, generate_image
from .config import NovelAIConfig, get_novelai_config
from .i18n import translate
from .payload import NovelAIImageRequest
from .prompt import PromptConversionError, compose_prompts, convert_prompt

_novelai_trigger = get_subplugin_trigger("novelai_image")

novelai_image_cmd: type[AlconnaMatcher] = on_alconna(
    command=Alconna(_novelai_trigger.primary, Args["prompt", Nargs(str)]),
    aliases=set(_novelai_trigger.aliases),
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)


async def run_novelai_image(
    prompt: list[str],
    *,
    config: NovelAIConfig | None = None,
) -> None:
    selected = config or get_novelai_config()
    if not selected.enabled:
        await novelai_image_cmd.finish(translate("disabled"))
        return
    user_text = " ".join(prompt).strip()
    if not user_text:
        await novelai_image_cmd.finish(translate("empty"))
        return
    try:
        converted = await convert_prompt(user_text, config=selected)
        composed = compose_prompts(
            converted,
            default_negative=selected.negative_prompt,
        )
    except PromptConversionError as exc:
        logger.error(f"NovelAI prompt conversion failed: {exc!r}")
        await novelai_image_cmd.finish(translate("prompt_failed"))
        return
    request = NovelAIImageRequest(
        prompt=", ".join((converted.description, *converted.tags)),
        negative_prompt=composed.negative_caption,
        model=selected.model,
        width=selected.width,
        height=selected.height,
        steps=selected.steps,
        scale=selected.scale,
        sampler=selected.sampler,
        seed=secrets.randbelow(2**32),
        v4_base_caption=composed.base_caption if composed.use_coords else None,
        v4_char_captions=composed.char_captions,
        v4_character_prompts=composed.character_prompts,
        use_coords=composed.use_coords,
    )
    try:
        image = await generate_image(request, config=selected)
    except MissingNovelAITokenError:
        await novelai_image_cmd.finish(translate("token_missing"))
        return
    except NovelAIError as exc:
        logger.error(f"NovelAI image generation failed: {exc!r}")
        await novelai_image_cmd.finish(translate("generation_failed"))
        return
    await novelai_image_cmd.finish(image_message(image))


@register_subplugin_handler(novelai_image_cmd, "novelai_image", "~onebot.v11")
async def novelai_image_handler(prompt: list[str]) -> None:
    await run_novelai_image(prompt)
