"""Locale-aware OneBot V11 image command and generation pipeline."""

import secrets
from typing import Any
from uuid import uuid4

from arclet.alconna import Alconna, Args, Arparma, Nargs, Option
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
from .intent import IntentAnalysisError, analyze_prompt_intent
from .models import GenerationOverrides, TipoRequest, VisualResearch
from .planner import InvalidGenerationOverrideError, build_generation_plan
from .search import research_visual_facts
from .tipo import TipoError, expand_with_tipo

_novelai_trigger = get_subplugin_trigger("novelai_image")
_MIN_DIMENSION = 64
_MAX_DIMENSION = 2048
_MAX_STEPS = 50
_MAX_SCALE = 20


def build_novelai_image_command() -> Alconna:
    """Build the locale-specific command parser."""
    return Alconna(
        _novelai_trigger.primary,
        Args["prompt", Nargs(str)],
        Option("--width", Args["width", int]),
        Option("--height", Args["height", int]),
        Option("--steps", Args["steps", int]),
        Option("--scale", Args["scale", float]),
        Option("--sampler", Args["sampler", str]),
        Option("--seed", Args["seed", int]),
        Option("--negative", Args["negative", str]),
    )


novelai_image_command = build_novelai_image_command()

novelai_image_cmd: type[AlconnaMatcher] = on_alconna(
    command=novelai_image_command,
    aliases=set(_novelai_trigger.aliases),
    priority=5,
    block=True,
    use_cmd_sep=True,
    use_cmd_start=True,
)


def generation_overrides_from_args(args: dict[str, Any]) -> GenerationOverrides:
    """Convert flattened Alconna arguments into the pipeline value object."""
    return GenerationOverrides(
        width=args.get("width"),
        height=args.get("height"),
        steps=args.get("steps"),
        scale=args.get("scale"),
        sampler=args.get("sampler"),
        seed=args.get("seed"),
        negative_prompt=args.get("negative"),
    )


def _validate_overrides(overrides: GenerationOverrides) -> None:
    validators = {
        "width": lambda value: _MIN_DIMENSION <= value <= _MAX_DIMENSION,
        "height": lambda value: _MIN_DIMENSION <= value <= _MAX_DIMENSION,
        "steps": lambda value: 1 <= value <= _MAX_STEPS,
        "scale": lambda value: 0 < value <= _MAX_SCALE,
        "sampler": lambda value: bool(value.strip()),
        "seed": lambda value: 0 <= value <= 2**32 - 1,
    }
    for field, validator in validators.items():
        value = getattr(overrides, field)
        if value is not None and not validator(value):
            raise InvalidGenerationOverrideError(field)


async def run_novelai_image(
    prompt: list[str],
    *,
    overrides: GenerationOverrides | None = None,
    config: NovelAIConfig | None = None,
) -> None:
    """Run intent, optional research/TIPO, planning, and image generation."""
    selected = config or get_novelai_config()
    if not selected.enabled:
        await novelai_image_cmd.finish(translate("disabled"))
        return
    user_text = " ".join(prompt).strip()
    if not user_text:
        await novelai_image_cmd.finish(translate("empty"))
        return

    selected_overrides = overrides or GenerationOverrides()
    try:
        _validate_overrides(selected_overrides)
    except InvalidGenerationOverrideError:
        await novelai_image_cmd.finish(translate("parameter_invalid"))
        return

    correlation_id = uuid4().hex
    random_seed = secrets.randbelow(2**32)
    try:
        intent = await analyze_prompt_intent(user_text)
    except IntentAnalysisError:
        await novelai_image_cmd.finish(translate("prompt_failed"))
        return

    research = VisualResearch((), ())
    if intent.search_required:
        research = await research_visual_facts(intent)

    tipo_prompt = None
    if selected.tipo_enabled:
        tipo_request = TipoRequest(
            description=intent.english_description,
            tags=intent.base_tags,
            visual_facts=research.facts,
            seed=random_seed,
        )
        try:
            tipo_prompt = await expand_with_tipo(tipo_request, config=selected)
        except TipoError as exc:
            logger.warning(
                "NovelAI pipeline degraded: correlation_id={}, stage=tipo, reason={}",
                correlation_id,
                type(exc).__name__,
            )

    plan = build_generation_plan(
        intent,
        tipo_prompt=tipo_prompt,
        overrides=selected_overrides,
        config=selected,
        random_seed=random_seed,
    )
    try:
        image = await generate_image(plan, config=selected)
    except MissingNovelAITokenError:
        await novelai_image_cmd.finish(translate("token_missing"))
        return
    except NovelAIError as exc:
        logger.warning(
            "NovelAI pipeline failed: correlation_id={}, stage=generation, reason={}",
            correlation_id,
            type(exc).__name__,
        )
        await novelai_image_cmd.finish(translate("generation_failed"))
        return
    await novelai_image_cmd.finish(image_message(image))


@register_subplugin_handler(novelai_image_cmd, "novelai_image", "~onebot.v11")
async def novelai_image_handler(
    prompt: list[str],
    result: Arparma,
) -> None:
    await run_novelai_image(
        prompt,
        overrides=generation_overrides_from_args(result.all_matched_args),
    )
