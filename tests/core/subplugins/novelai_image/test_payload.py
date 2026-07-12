from typing import Any

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.models import (
    NovelAIGenerationPlan,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.payload import (
    build_payload,
)


def plan(**changes: object) -> NovelAIGenerationPlan:
    values: dict[str, Any] = {
        "prompt": "A cat, cat, hat",
        "negative_prompt": "text",
        "width": 832,
        "height": 1216,
        "steps": 28,
        "scale": 5.0,
        "sampler": "k_euler_ancestral",
        "seed": 42,
        "base_caption": "A cat",
        "char_captions": (),
        "character_prompts": (),
        "use_coords": False,
    }
    values.update(changes)
    return NovelAIGenerationPlan(**values)


def test_build_payload_contains_minimal_v45_shape() -> None:
    payload = build_payload(plan(), model="nai-diffusion-4-5-full")

    parameters = payload["parameters"]
    assert payload["action"] == "generate"
    assert payload["input"] == "A cat, cat, hat"
    assert payload["model"] == "nai-diffusion-4-5-full"
    assert parameters["stream"] == "msgpack"
    assert parameters["v4_prompt"]["caption"]["base_caption"] == "A cat"
    assert parameters["characterPrompts"] == []
    assert parameters["seed"] == 42
    assert parameters["image_format"] == "png"
    assert parameters["noise_schedule"] == "karras"
    assert not parameters["use_coords"]
    assert not parameters["v4_prompt"]["use_coords"]
    assert "image" not in parameters


def test_build_payload_preserves_v4_character_and_coordinate_shape() -> None:
    char_caption = {
        "char_caption": "1girl, silver hair",
        "centers": [{"x": 0.3, "y": 0.5}],
    }
    char_prompt = {
        "prompt": "1girl, silver hair",
        "uc": "bad hands",
        "center": {"x": 0.3, "y": 0.5},
        "enabled": True,
    }
    payload = build_payload(
        plan(
            prompt="A girl standing alone, 1girl, silver hair",
            negative_prompt="lowres, text",
            seed=99,
            base_caption="A girl standing alone",
            char_captions=(char_caption,),
            character_prompts=(char_prompt,),
            use_coords=True,
        ),
        model="nai-diffusion-4-5-full",
    )

    parameters = payload["parameters"]
    assert parameters["v4_prompt"]["caption"] == {
        "base_caption": "A girl standing alone",
        "char_captions": [char_caption],
    }
    assert parameters["v4_prompt"]["use_coords"] is True
    assert parameters["use_coords"] is True
    assert parameters["characterPrompts"] == [char_prompt]
    assert parameters["v4_negative_prompt"]["caption"]["base_caption"] == (
        "lowres, text"
    )
