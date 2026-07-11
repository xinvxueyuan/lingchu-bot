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
    assert not parameters["use_coords"]
    assert not parameters["v4_prompt"]["use_coords"]
    assert "image" not in parameters


def test_build_payload_simple_scene_base_caption_equals_prompt() -> None:
    request = NovelAIImageRequest(
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
    payload = build_payload(request)

    assert (
        payload["parameters"]["v4_prompt"]["caption"]["base_caption"]
        == "A cat, cat, hat"
    )
    assert payload["parameters"]["v4_prompt"]["caption"]["char_captions"] == []
    assert payload["parameters"]["characterPrompts"] == []


def test_build_payload_complex_scene_uses_v4_structured_fields() -> None:
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
    request = NovelAIImageRequest(
        prompt="A girl standing alone, 1girl, silver hair",
        negative_prompt="lowres, text",
        model="nai-diffusion-4-5-full",
        width=832,
        height=1216,
        steps=28,
        scale=5,
        sampler="k_euler_ancestral",
        seed=99,
        v4_base_caption="A girl standing alone",
        v4_char_captions=(char_caption,),
        v4_character_prompts=(char_prompt,),
        use_coords=True,
    )
    payload = build_payload(request)

    parameters = payload["parameters"]
    assert parameters["v4_prompt"]["caption"]["base_caption"] == "A girl standing alone"
    assert parameters["v4_prompt"]["caption"]["char_captions"] == [char_caption]
    assert parameters["v4_prompt"]["use_coords"] is True
    assert parameters["use_coords"] is True
    assert parameters["characterPrompts"] == [char_prompt]
    assert payload["input"] == "A girl standing alone, 1girl, silver hair"


def test_build_payload_char_captions_structure() -> None:
    char_caption = {
        "char_caption": "1boy, black hair, red eyes",
        "centers": [{"x": 0.7, "y": 0.4}],
    }
    request = NovelAIImageRequest(
        prompt="Two characters, 1girl, 1boy",
        negative_prompt="text",
        model="nai-diffusion-4-5-full",
        width=832,
        height=1216,
        steps=28,
        scale=5,
        sampler="k_euler_ancestral",
        seed=7,
        v4_base_caption="Two characters talking",
        v4_char_captions=(char_caption,),
        use_coords=True,
    )
    payload = build_payload(request)

    captions = payload["parameters"]["v4_prompt"]["caption"]["char_captions"]
    assert len(captions) == 1
    assert captions[0]["char_caption"] == "1boy, black hair, red eyes"
    assert captions[0]["centers"][0]["x"] == 0.7
    assert captions[0]["centers"][0]["y"] == 0.4
