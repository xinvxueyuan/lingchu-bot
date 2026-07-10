from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.payload import (
    NovelAIImageRequest,
    build_payload,
)


def test_build_payload_contains_minimal_v45_shape() -> None:
    payload = build_payload(
        NovelAIImageRequest(
            prompt="A cat, cat, hat",
            negative_prompt="text",
            model="nai-diffusion-4-5-full",
            width=832,
            height=1216,
            steps=28,
            scale=5,
            sampler="k_euler_ancestral",
            seed=42,
        )
    )

    parameters = payload["parameters"]
    assert payload["action"] == "generate"
    assert payload["model"] == "nai-diffusion-4-5-full"
    assert parameters["stream"] == "msgpack"
    assert parameters["v4_prompt"]["caption"]["base_caption"] == "A cat, cat, hat"
    assert parameters["characterPrompts"] == []
    assert parameters["seed"] == 42
    assert parameters["image_format"] == "png"
    assert parameters["noise_schedule"] == "karras"
    assert "image" not in parameters
