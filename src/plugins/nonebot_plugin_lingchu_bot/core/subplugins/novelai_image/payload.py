"""Minimal NovelAI V4.5 request payload."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class NovelAIImageRequest:
    prompt: str
    negative_prompt: str
    model: str
    width: int
    height: int
    steps: int
    scale: float
    sampler: str
    seed: int
    v4_base_caption: str | None = None
    v4_char_captions: tuple[dict[str, Any], ...] = ()
    v4_character_prompts: tuple[dict[str, Any], ...] = ()
    use_coords: bool = False


def _caption(
    text: str,
    *,
    char_captions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {"caption": {"base_caption": text, "char_captions": char_captions or []}}


def build_payload(request: NovelAIImageRequest) -> dict[str, Any]:
    base_cap = (
        request.v4_base_caption
        if request.v4_base_caption is not None
        else request.prompt
    )
    return {
        "action": "generate",
        "input": request.prompt,
        "model": request.model,
        "parameters": {
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "scale": request.scale,
            "sampler": request.sampler,
            "seed": request.seed,
            "n_samples": 1,
            "negative_prompt": request.negative_prompt,
            "qualityToggle": True,
            "ucPreset": 0,
            "params_version": 3,
            "stream": "msgpack",
            "v4_prompt": _caption(
                base_cap,
                char_captions=list(request.v4_char_captions),
            )
            | {"use_coords": request.use_coords, "use_order": True},
            "v4_negative_prompt": _caption(request.negative_prompt)
            | {"legacy_uc": False},
            "characterPrompts": list(request.v4_character_prompts)
            if request.v4_character_prompts
            else [],
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
            "use_coords": request.use_coords,
        },
    }
