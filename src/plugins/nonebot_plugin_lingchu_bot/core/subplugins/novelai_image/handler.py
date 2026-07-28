"""Locale-aware OneBot V11 image command and generation pipeline."""

import base64
from pathlib import Path
import secrets
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import aiofiles
from arclet.alconna import Alconna, Args, Arparma, Nargs, Option, Subcommand
from nonebot import logger, require

require("nonebot_plugin_alconna")
from nonebot_plugin_alconna import AlconnaMatcher, on_alconna
from nonebot_plugin_alconna.uniseg import Image as UniImage

from ..contracts import (
    download_public_http_bytes,
    get_subplugin_trigger,
    image_message,
    register_subplugin_handler,
)
from .config import NovelAIConfig, get_novelai_config
from .constants import ControlNetModel, DirectorTool, Emotion, EmotionLevel
from .i18n import translate
from .intent import IntentAnalysisError, analyze_prompt_intent
from .models import (
    GenerationOverrides,
    NovelAIGenerationPlan,
    TipoRequest,
    VisualResearch,
)
from .planner import InvalidGenerationOverrideError, build_generation_plan
from .search import research_visual_facts
from .service import get_novelai_mcp_client
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
        Args["prompt", Nargs(str, "*")],
        Subcommand(
            "img2img",
            Args["action_prompt", Nargs(str)],
            Option("--image", Args["image", UniImage]),
            Option("--strength", Args["strength", float]),
            Option("--noise", Args["noise", float]),
        ),
        Subcommand(
            "inpaint",
            Args["action_prompt", Nargs(str)],
            Option("--image", Args["image", UniImage]),
            Option("--mask", Args["mask", UniImage]),
        ),
        Subcommand(
            "vibe",
            Args["action_prompt", Nargs(str)],
            Option("--reference", Args["reference", UniImage]),
            Option("--reference-strength", Args["reference_strength", float]),
        ),
        Subcommand(
            "tool",
            Args["tool_name", str],
            Option("--image", Args["image", UniImage]),
            Option("--prompt", Args["tool_prompt", str]),
            Option("--defry", Args["defry", int]),
            Option("--emotion", Args["emotion", str]),
            Option("--emotion-level", Args["emotion_level", int]),
        ),
        Subcommand(
            "upscale",
            Option("--image", Args["image", UniImage]),
            Option("--factor", Args["factor", int]),
        ),
        Subcommand(
            "annotate",
            Option("--image", Args["image", UniImage]),
            Option("--model", Args["controlnet_model", str]),
        ),
        Subcommand(
            "tags",
            Args["tag_prefix", str],
            Option("--model", Args["tag_model", str]),
            Option("--lang", Args["tag_language", str]),
        ),
        Subcommand("account", Args["account_kind", str]),
        Option("--width", Args["width", int]),
        Option("--height", Args["height", int]),
        Option("--steps", Args["steps", int]),
        Option("--scale", Args["scale", float]),
        Option("--sampler", Args["sampler", str]),
        Option("--seed", Args["seed", int]),
        Option("--negative", Args["negative", str]),
    )


def _b64(data: bytes) -> str:
    """Encode bytes as base64 string for MCP tool arguments."""
    return base64.b64encode(data).decode("ascii")


async def _read_uniseg_image(image: UniImage, *, config: NovelAIConfig) -> bytes:
    raw = getattr(image, "raw", None)
    if raw is not None:
        data = raw.getvalue() if hasattr(raw, "getvalue") else raw
        if isinstance(data, bytes):
            return data
    path = getattr(image, "path", None)
    if path is not None:
        async with aiofiles.open(Path(path), "rb") as stream:
            data = await stream.read(config.image_download_max_bytes + 1)
        if len(data) > config.image_download_max_bytes:
            raise ValueError("image is too large")
        return data
    url = getattr(image, "url", None)
    if not isinstance(url, str) or urlparse(url).scheme not in {"http", "https"}:
        raise ValueError("image must contain bytes, a path, or an HTTP(S) URL")
    data = await download_public_http_bytes(
        url,
        max_bytes=config.image_download_max_bytes,
        request_timeout=config.timeout,
    )
    if data is None:
        raise ValueError("HTTP image download is unavailable")
    return data


def _plan_to_mcp_args(
    plan: NovelAIGenerationPlan, *, config: NovelAIConfig
) -> dict[str, Any]:
    """Convert a generation plan to MCP generate_image tool arguments."""
    args: dict[str, Any] = {
        "prompt": plan.prompt,
        "negative_prompt": plan.negative_prompt,
        "model": config.model,
        "width": plan.width,
        "height": plan.height,
        "steps": plan.steps,
        "scale": plan.scale,
        "sampler": plan.sampler,
        "seed": plan.seed,
        "n_samples": config.n_samples,
        "quality": config.quality,
        "uc_preset": config.uc_preset,
        "noise_schedule": config.noise_schedule,
        "cfg_rescale": config.cfg_rescale,
    }
    if plan.character_prompts:
        args["character_prompts"] = [
            {
                "prompt": cp["prompt"],
                "uc": cp.get("uc", ""),
                "center": cp["center"],
                "enabled": cp.get("enabled", True),
            }
            for cp in plan.character_prompts
        ]
    return args


async def run_novelai_api_action(result: Arparma) -> bool:
    """Run a non-legacy NovelAI action. Return whether one was selected."""
    paths = (
        "img2img",
        "inpaint",
        "vibe",
        "tool",
        "upscale",
        "annotate",
        "tags",
        "account",
    )
    selected_path = next((path for path in paths if result.find(path)), None)
    if selected_path is None:
        return False
    config = get_novelai_config()
    try:
        client = get_novelai_mcp_client(config)
        args = result.all_matched_args
        if selected_path in {"img2img", "inpaint", "vibe"}:
            prompt = " ".join(args.get("action_prompt", [])).strip()
            if not prompt:
                raise ValueError("prompt is required")
            image_key = "reference" if selected_path == "vibe" else "image"
            segment = args.get(image_key)
            if not isinstance(segment, UniImage):
                raise ValueError("image is required")
            image_bytes = await _read_uniseg_image(segment, config=config)
            if selected_path == "vibe":
                result_bytes = await client.call_tool(
                    "generate_image",
                    {
                        "prompt": prompt,
                        "negative_prompt": config.negative_prompt,
                        "model": config.model,
                        "width": config.width,
                        "height": config.height,
                        "steps": config.steps,
                        "scale": config.scale,
                        "sampler": config.sampler,
                        "seed": secrets.randbelow(2**32),
                        "n_samples": config.n_samples,
                        "quality": config.quality,
                        "uc_preset": config.uc_preset,
                        "noise_schedule": config.noise_schedule,
                        "cfg_rescale": config.cfg_rescale,
                        "references": [_b64(image_bytes)],
                    },
                )
            elif selected_path == "inpaint":
                mask_segment = args.get("mask")
                if not isinstance(mask_segment, UniImage):
                    raise ValueError("mask is required")
                mask_bytes = await _read_uniseg_image(mask_segment, config=config)
                inpaint_model = (
                    config.model
                    if "inpaint" in config.model
                    else "nai-diffusion-4-5-full-inpainting"
                )
                result_bytes = await client.call_tool(
                    "inpaint",
                    {
                        "prompt": prompt,
                        "image": _b64(image_bytes),
                        "mask": _b64(mask_bytes),
                        "negative_prompt": config.negative_prompt,
                        "model": inpaint_model,
                        "width": config.width,
                        "height": config.height,
                        "steps": config.steps,
                        "scale": config.scale,
                        "sampler": config.sampler,
                        "seed": secrets.randbelow(2**32),
                        "n_samples": config.n_samples,
                        "quality": config.quality,
                        "uc_preset": config.uc_preset,
                        "noise_schedule": config.noise_schedule,
                        "cfg_rescale": config.cfg_rescale,
                        "strength": float(args.get("strength", 0.7)),
                        "noise": float(args.get("noise", 0.0)),
                    },
                )
            else:
                result_bytes = await client.call_tool(
                    "image_to_image",
                    {
                        "prompt": prompt,
                        "image": _b64(image_bytes),
                        "negative_prompt": config.negative_prompt,
                        "model": config.model,
                        "width": config.width,
                        "height": config.height,
                        "steps": config.steps,
                        "scale": config.scale,
                        "sampler": config.sampler,
                        "seed": secrets.randbelow(2**32),
                        "n_samples": config.n_samples,
                        "quality": config.quality,
                        "uc_preset": config.uc_preset,
                        "noise_schedule": config.noise_schedule,
                        "cfg_rescale": config.cfg_rescale,
                        "strength": float(args.get("strength", 0.7)),
                        "noise": float(args.get("noise", 0.0)),
                    },
                )
            if not result_bytes:
                await novelai_image_cmd.finish(translate("action_failed"))
                return True
            await novelai_image_cmd.finish(image_message(result_bytes))
            return True
        if selected_path == "tags":
            tag_prefix = str(args["tag_prefix"])
            tag_model = str(args.get("tag_model", config.model))
            tag_language = str(args.get("tag_language", "en"))
            tags_text = await client.call_tool(
                "suggest_tags",
                {
                    "prompt": tag_prefix,
                    "model": tag_model,
                    "language": tag_language,
                },
            )
            if not isinstance(tags_text, str) or not tags_text:
                await novelai_image_cmd.finish(translate("action_failed"))
                return True
            await novelai_image_cmd.finish(tags_text[:2_000])
            return True
        if selected_path == "account":
            kind = str(args["account_kind"])
            tool_name = (
                "get_subscription" if kind == "subscription" else "get_user_data"
            )
            data_text = await client.call_tool(tool_name, {})
            if not isinstance(data_text, str) or not data_text:
                await novelai_image_cmd.finish(translate("action_failed"))
                return True
            await novelai_image_cmd.finish(data_text[:2_000])
            return True
        segment = args.get("image")
        if not isinstance(segment, UniImage):
            raise ValueError("image is required")
        image_bytes = await _read_uniseg_image(segment, config=config)
        if selected_path == "tool":
            tool = DirectorTool(str(args["tool_name"]))
            emotion = Emotion(str(args["emotion"])) if args.get("emotion") else None
            emotion_level = EmotionLevel(int(args.get("emotion_level", 0)))
            result_bytes = await client.call_tool(
                "director_tool",
                {
                    "tool": tool.value,
                    "image": _b64(image_bytes),
                    "prompt": str(args.get("tool_prompt", "")),
                    "defry": int(args.get("defry", 0)),
                    "emotion": emotion.value if emotion else None,
                    "emotion_level": emotion_level.value,
                },
            )
        elif selected_path == "upscale":
            result_bytes = await client.call_tool(
                "upscale_image",
                {
                    "image": _b64(image_bytes),
                    "factor": int(args.get("factor", 4)),
                },
            )
        else:
            controlnet_model = ControlNetModel(
                str(args.get("controlnet_model", "fake_scribble"))
            )
            result_bytes = await client.call_tool(
                "annotate_image",
                {
                    "image": _b64(image_bytes),
                    "model": controlnet_model.value,
                },
            )
        if not result_bytes:
            await novelai_image_cmd.finish(translate("action_failed"))
            return True
        await novelai_image_cmd.finish(image_message(result_bytes))
    except (ValueError, OSError, RuntimeError) as exc:
        logger.warning(
            "NovelAI action failed: action={}, reason={}",
            selected_path,
            type(exc).__name__,
        )
        await novelai_image_cmd.finish(translate("action_failed"))
    return True


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
    mcp_args = _plan_to_mcp_args(plan, config=selected)
    try:
        image_bytes = await get_novelai_mcp_client(selected).call_tool(
            "generate_image", mcp_args
        )
    except Exception as exc:
        logger.warning(
            "NovelAI pipeline failed: correlation_id={}, stage=generation, reason={}",
            correlation_id,
            type(exc).__name__,
        )
        await novelai_image_cmd.finish(translate("generation_failed"))
        return
    if not image_bytes:
        await novelai_image_cmd.finish(translate("generation_failed"))
        return
    await novelai_image_cmd.finish(image_message(image_bytes))


@register_subplugin_handler(novelai_image_cmd, "novelai_image", "~onebot.v11")
async def novelai_image_handler(
    prompt: list[str],
    result: Arparma,
) -> None:
    if await run_novelai_api_action(result):
        return
    await run_novelai_image(
        prompt,
        overrides=generation_overrides_from_args(result.all_matched_args),
    )
