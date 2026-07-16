"""Locale-aware OneBot V11 image command and generation pipeline."""

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
from .client import MissingNovelAITokenError, NovelAIError, generate_image
from .config import NovelAIConfig, get_novelai_config
from .constants import ControlNetModel, DirectorTool, Emotion, EmotionLevel, Model
from .i18n import translate
from .imaging import parse_image
from .intent import IntentAnalysisError, analyze_prompt_intent
from .models import GenerationOverrides, GenerationRequest, TipoRequest, VisualResearch
from .planner import InvalidGenerationOverrideError, build_generation_plan
from .search import research_visual_facts
from .service import create_novelai_client
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


async def _read_uniseg_image(image: UniImage, *, config: NovelAIConfig) -> bytes:
    raw = getattr(image, "raw", None)
    if raw is not None:
        data = raw.getvalue() if hasattr(raw, "getvalue") else raw
        if isinstance(data, bytes):
            parse_image(data)
            return data
    path = getattr(image, "path", None)
    if path is not None:
        async with aiofiles.open(Path(path), "rb") as stream:
            data = await stream.read(config.image_download_max_bytes + 1)
        if len(data) > config.image_download_max_bytes:
            raise ValueError("image is too large")
        parse_image(data)
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
    parse_image(data)
    return data


def _action_request(
    prompt: str,
    *,
    config: NovelAIConfig,
    image: str | None = None,
    mask: str | None = None,
    action: str = "generate",
    references: tuple[str, ...] = (),
    reference_strengths: tuple[float, ...] = (),
    strength: float | None = None,
    noise: float | None = None,
) -> GenerationRequest:
    from .constants import Action

    model = Model(config.model)
    if action == "infill" and "inpainting" not in model.value:
        model = Model.V4_5_INPAINT
    return GenerationRequest(
        prompt=prompt,
        model=model,
        action=Action(action),
        negative_prompt=config.negative_prompt,
        width=config.width,
        height=config.height,
        n_samples=config.n_samples,
        steps=config.steps,
        scale=config.scale,
        sampler=config.sampler,
        seed=secrets.randbelow(2**32),
        quality=config.quality,
        uc_preset=config.uc_preset,
        noise_schedule=config.noise_schedule,
        cfg_rescale=config.cfg_rescale,
        dynamic_thresholding=config.dynamic_thresholding,
        auto_smea=config.auto_smea,
        prefer_brownian=config.prefer_brownian,
        image=image,
        mask=mask,
        strength=strength,
        noise=noise,
        references=references,
        reference_strengths=reference_strengths,
    )


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
        client = create_novelai_client(config)
        args = result.all_matched_args
        if selected_path in {"img2img", "inpaint", "vibe"}:
            prompt = " ".join(args.get("action_prompt", [])).strip()
            if not prompt:
                raise ValueError("prompt is required")
            image_key = "reference" if selected_path == "vibe" else "image"
            segment = args.get(image_key)
            if not isinstance(segment, UniImage):
                raise ValueError("image is required")
            parsed = parse_image(await _read_uniseg_image(segment, config=config))
            if selected_path == "vibe":
                request = _action_request(
                    prompt,
                    config=config,
                    references=(parsed.base64,),
                    reference_strengths=(float(args.get("reference_strength", 0.6)),),
                )
            else:
                mask = None
                if selected_path == "inpaint":
                    mask_segment = args.get("mask")
                    if not isinstance(mask_segment, UniImage):
                        raise ValueError("mask is required")
                    mask = parse_image(
                        await _read_uniseg_image(mask_segment, config=config)
                    ).base64
                request = _action_request(
                    prompt,
                    config=config,
                    image=parsed.base64,
                    mask=mask,
                    action="infill" if selected_path == "inpaint" else "img2img",
                    strength=float(args.get("strength", 0.7)),
                    noise=float(args.get("noise", 0.0)),
                )
            images = await client.generate(request)
            for image in images[:-1]:
                await novelai_image_cmd.send(image_message(image.data))
            await novelai_image_cmd.finish(image_message(images[-1].data))
            return True
        if selected_path == "tags":
            tags = await client.suggest_tags(
                str(args["tag_prefix"]),
                model=Model(str(args.get("tag_model", config.model))),
                language=str(args.get("tag_language", "en")),
            )
            await novelai_image_cmd.finish(
                "\n".join(str(item.get("tag", "")) for item in tags[:20])
            )
            return True
        if selected_path == "account":
            kind = str(args["account_kind"])
            data = (
                await client.get_subscription()
                if kind == "subscription"
                else await client.get_user_data()
            )
            safe = {
                key: value
                for key, value in data.items()
                if not any(
                    secret in key.casefold() for secret in ("token", "key", "email")
                )
            }
            await novelai_image_cmd.finish(str(safe)[:2_000])
            return True
        segment = args.get("image")
        if not isinstance(segment, UniImage):
            raise ValueError("image is required")
        image_bytes = await _read_uniseg_image(segment, config=config)
        if selected_path == "tool":
            tool = DirectorTool(str(args["tool_name"]))
            output = await client.director(
                tool,
                image_bytes,
                prompt=str(args.get("tool_prompt", "")),
                defry=int(args.get("defry", 0)),
                emotion=Emotion(str(args["emotion"])) if args.get("emotion") else None,
                emotion_level=EmotionLevel(int(args.get("emotion_level", 0))),
            )
        elif selected_path == "upscale":
            output = await client.upscale(
                image_bytes, factor=int(args.get("factor", 4))
            )
        else:
            output = await client.annotate(
                image_bytes,
                ControlNetModel(str(args.get("controlnet_model", "fake_scribble"))),
            )
        await novelai_image_cmd.finish(image_message(output.data))
    except (NovelAIError, ValueError, OSError) as exc:
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
    if await run_novelai_api_action(result):
        return
    await run_novelai_image(
        prompt,
        overrides=generation_overrides_from_args(result.all_matched_args),
    )
