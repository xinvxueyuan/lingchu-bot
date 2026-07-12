"""NovelAI V4.5 wire payload mapping."""

from typing import Any

from .models import NovelAIGenerationPlan


def _caption(
    text: str,
    *,
    char_captions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {"caption": {"base_caption": text, "char_captions": char_captions or []}}


def build_payload(
    plan: NovelAIGenerationPlan,
    *,
    model: str,
) -> dict[str, Any]:
    """Map an already-resolved plan to NovelAI's V4.5 request shape."""
    return {
        "action": "generate",
        "input": plan.prompt,
        "model": model,
        "parameters": {
            "width": plan.width,
            "height": plan.height,
            "steps": plan.steps,
            "scale": plan.scale,
            "sampler": plan.sampler,
            "seed": plan.seed,
            "n_samples": 1,
            "negative_prompt": plan.negative_prompt,
            "qualityToggle": True,
            "ucPreset": 0,
            "params_version": 3,
            "stream": "msgpack",
            "v4_prompt": _caption(
                plan.base_caption,
                char_captions=list(plan.char_captions),
            )
            | {"use_coords": plan.use_coords, "use_order": True},
            "v4_negative_prompt": _caption(plan.negative_prompt) | {"legacy_uc": False},
            "characterPrompts": list(plan.character_prompts),
            "add_original_image": True,
            "autoSmea": False,
            "cfg_rescale": 0,
            "controlnet_strength": 1,
            "dynamic_thresholding": False,
            "image_format": "png",
            "legacy": False,
            "legacy_uc": False,
            "legacy_v3_extend": False,
            "noise_schedule": "karras",
            "normalize_reference_strength_multiple": True,
            "prefer_brownian": True,
            "use_coords": plan.use_coords,
        },
    }
