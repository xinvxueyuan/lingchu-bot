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


def _caption(text: str) -> dict[str, Any]:
    return {"caption": {"base_caption": text, "char_captions": []}}


def build_payload(request: NovelAIImageRequest) -> dict[str, Any]:
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
            "v4_prompt": _caption(request.prompt)
            | {"use_coords": False, "use_order": True},
            "v4_negative_prompt": _caption(request.negative_prompt)
            | {"legacy_uc": False},
            "characterPrompts": [],
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
            "use_coords": False,
        },
    }
