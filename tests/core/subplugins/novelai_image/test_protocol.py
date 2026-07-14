import io
import struct
from typing import cast
import zipfile

import msgpack
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.auth import (
    NovelAICredentials,
    derive_access_key,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.constants import (
    Action,
    Model,
    is_v4_model,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.exceptions import (
    NovelAIAuthenticationError,
    NovelAIConcurrencyError,
    NovelAIImageError,
    NovelAIInsufficientCreditsError,
    NovelAIValidationError,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.imaging import (
    parse_image,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.models import (
    CharacterPrompt,
    GenerationRequest,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.payload import (
    build_generation_payload,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.response import (
    MessagePackStreamParser,
    check_status,
    parse_messagepack_images,
    parse_zip_images,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + struct.pack(">II", 3, 5) + b"data"


def frame(value: object) -> bytes:
    packed = cast("bytes", msgpack.packb(value))
    return struct.pack(">I", len(packed)) + packed


def test_protocol_models_cover_v3_v4_and_inpainting() -> None:
    assert Model.V3.value == "nai-diffusion-3"
    assert Model.V4_5_INPAINT.value == "nai-diffusion-4-5-full-inpainting"
    assert is_v4_model(Model.V4_5)
    assert not is_v4_model(Model.FURRY)
    assert Action.INPAINT.value == "infill"


def test_credentials_require_token_or_complete_login_pair() -> None:
    assert NovelAICredentials(token="secret").token == "secret"
    assert NovelAICredentials(username="u", password="p").username == "u"
    with pytest.raises(ValueError):
        NovelAICredentials(username="u")


def test_access_key_derivation_is_deterministic() -> None:
    credentials = NovelAICredentials(username="user", password="password")

    assert derive_access_key(credentials) == (
        "e7gHYjiZwmxI-C-vH7ldhScjTstSBBB-OopFAqY2bGTeqGGfjrX_ifhAbVoPkIMG"
    )


def test_parse_png_image_returns_dimensions_and_base64() -> None:
    image = parse_image(PNG)
    assert (image.width, image.height) == (3, 5)
    assert image.data == PNG
    assert image.base64


def test_parse_jpeg_and_reject_malformed_images() -> None:
    jpeg = b"\xff\xd8\xff\xc0\x00\x07\x08\x00\x05\x00\x03"
    assert (parse_image(jpeg).width, parse_image(jpeg).height) == (3, 5)
    with pytest.raises(NovelAIImageError):
        parse_image(b"not-an-image")
    with pytest.raises(NovelAIImageError):
        parse_image(b"\x89PNG\r\n\x1a\n")
    with pytest.raises(NovelAIImageError):
        parse_image(b"\xff\xd8\xff\xd9")
    with pytest.raises(NovelAIImageError):
        parse_image(b"\x89PNG\r\n\x1a\n" + b"\0" * 16)


def test_parse_zip_images_returns_every_non_directory_entry() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("a.png", PNG)
        archive.writestr("nested/b.png", PNG + b"2")
    assert [image.filename for image in parse_zip_images(buffer.getvalue())] == [
        "a.png",
        "nested/b.png",
    ]


def test_messagepack_parser_handles_split_frames_and_batch_finals() -> None:
    content = frame({
        "event_type": "final",
        "samp_ix": 0,
        "gen_id": "g",
        "image": PNG,
    }) + frame({
        "event_type": "final",
        "samp_ix": 1,
        "gen_id": "g",
        "image": PNG + b"2",
    })
    parser = MessagePackStreamParser()
    assert parser.feed(content[:7]) == ()
    events = parser.feed(content[7:])
    assert [event.sample_index for event in events] == [0, 1]
    assert len(parse_messagepack_images(content)) == 2


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (400, NovelAIValidationError),
        (401, NovelAIAuthenticationError),
        (402, NovelAIInsufficientCreditsError),
        (429, NovelAIConcurrencyError),
    ],
)
def test_status_mapping(status: int, error_type: type[Exception]) -> None:
    with pytest.raises(error_type):
        check_status(status, b'{"message":"no"}')


def test_complete_v4_generation_payload_contains_all_conditioning_modes() -> None:
    request = GenerationRequest(
        prompt="two people",
        model=Model.V4_5,
        width=1216,
        height=832,
        n_samples=2,
        image="base64-image",
        mask="base64-mask",
        strength=0.6,
        noise=0.1,
        references=("vibe-token",),
        reference_strengths=(0.7,),
        character_prompts=(CharacterPrompt("red hair", "bad hands", x=0.3, y=0.5),),
    )
    payload = build_generation_payload(request)
    parameters = payload["parameters"]
    assert payload["model"] == Model.V4_5.value
    assert parameters["n_samples"] == 2
    assert parameters["image"] == "base64-image"
    assert parameters["mask"] == "base64-mask"
    assert parameters["reference_image_multiple"] == ["vibe-token"]
    assert parameters["reference_strength_multiple"] == [0.7]
    assert parameters["v4_prompt"]["caption"]["char_captions"][0]["centers"] == [
        {"x": 0.3, "y": 0.5}
    ]


def test_generation_request_validates_action_inputs_and_batch_size() -> None:
    with pytest.raises(ValueError):
        GenerationRequest(prompt="x", action=Action.IMG2IMG)
    with pytest.raises(ValueError):
        GenerationRequest(prompt="x", n_samples=9)
    with pytest.raises(ValueError):
        GenerationRequest(
            prompt="x",
            model=Model.V4_5,
            references=("one", "two"),
            reference_strengths=(0.5,),
        )


def test_generation_request_normalizes_resolution_and_validates_strengths() -> None:
    request = GenerationRequest(prompt="x", width=801, height=1201)
    assert (request.width, request.height) == (832, 1216)
    with pytest.raises(ValueError):
        GenerationRequest(prompt="x", controlnet_strength=2.1)
    with pytest.raises(ValueError):
        GenerationRequest(
            prompt="x",
            model=Model.V3,
            references=("image",),
            reference_information=(0.0,),
        )


def test_generation_request_reports_resolution_limit_and_anlas_cost() -> None:
    request = GenerationRequest(prompt="x", width=832, height=1216, steps=28)
    assert request.max_samples == 4
    assert request.estimate_anlas_cost(opus=True) == 0
    assert request.estimate_anlas_cost(opus=False) >= 2


@pytest.mark.parametrize(
    ("dimensions", "maximum"),
    [
        ((512, 704), 8),
        ((640, 640), 6),
        ((1024, 1280), 4),
        ((1024, 1536), 2),
        ((1024, 1600), 1),
    ],
)
def test_generation_request_batch_limit_depends_on_resolution(
    dimensions: tuple[int, int],
    maximum: int,
) -> None:
    width, height = dimensions
    assert (
        GenerationRequest(
            prompt="x",
            width=width,
            height=height,
            n_samples=maximum,
        ).max_samples
        == maximum
    )
    with pytest.raises(ValueError):
        GenerationRequest(
            prompt="x",
            width=width,
            height=height,
            n_samples=maximum + 1,
        )


def test_v3_payload_omits_v4_only_fields() -> None:
    parameters = build_generation_payload(
        GenerationRequest(prompt="x", model=Model.V3)
    )["parameters"]
    assert parameters["sm"] is False
    assert parameters["sm_dyn"] is False
    for field in (
        "autoSmea",
        "use_coords",
        "legacy_uc",
        "prefer_brownian",
        "deliberate_euler_ancestral_bug",
        "normalize_reference_strength_multiple",
        "inpaintImg2ImgStrength",
        "v4_prompt",
        "v4_negative_prompt",
        "stream",
    ):
        assert field not in parameters


def test_conditioned_generation_applies_provider_defaults() -> None:
    img2img = build_generation_payload(
        GenerationRequest(
            prompt="x",
            model=Model.V4_5,
            action=Action.IMG2IMG,
            image="image",
        )
    )["parameters"]
    assert img2img["strength"] == 0.3
    assert img2img["noise"] == 0
    assert isinstance(img2img["extra_noise_seed"], int)
    assert img2img["inpaintImg2ImgStrength"] == 1


def test_quality_and_uc_presets_are_expanded_into_wire_prompts() -> None:
    payload = build_generation_payload(
        GenerationRequest(
            prompt="1girl",
            base_caption="solo girl",
            negative_prompt="bad hands",
            model=Model.V4_5,
            quality=True,
            uc_preset=0,
        )
    )

    assert "very aesthetic" in payload["input"]
    base_caption = payload["parameters"]["v4_prompt"]["caption"]["base_caption"]
    assert base_caption.startswith("solo girl")
    assert "no text" in base_caption
    negative = payload["parameters"]["negative_prompt"]
    assert negative.startswith("nsfw, lowres")
    assert negative.endswith("bad hands")
