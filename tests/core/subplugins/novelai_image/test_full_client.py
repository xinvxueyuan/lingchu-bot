import json
import struct
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import msgpack
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.auth import (
    NovelAICredentials,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client import (
    NovelAIClient,
    _content,
    _first_image,
    _json_object,
    _process_event,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.config import (
    NovelAIConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.constants import (
    ControlNetModel,
    DirectorTool,
    Emotion,
    EmotionLevel,
    Model,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.exceptions import (
    NovelAIAuthenticationError,
    NovelAIResponseError,
    NovelAITimeoutError,
    NovelAITransportError,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.models import (
    GenerationRequest,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.service import (
    create_novelai_client,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + struct.pack(">II", 3, 5) + b"data"


def frame(value: object) -> bytes:
    packed = cast("bytes", msgpack.packb(value))
    return struct.pack(">I", len(packed)) + packed


def driver_with(*responses: object) -> tuple[SimpleNamespace, AsyncMock]:
    request = AsyncMock(side_effect=responses)

    class SessionContext:
        async def __aenter__(self) -> Any:
            return SimpleNamespace(request=request)

        async def __aexit__(self, *args: object) -> None:
            return None

    return SimpleNamespace(get_session=SessionContext), request


def test_client_response_helpers_cover_json_zip_and_compatibility_events() -> None:
    assert _content(SimpleNamespace(content="text")) == b"text"
    with pytest.raises(NovelAIResponseError):
        _content(SimpleNamespace(content=object()))
    with pytest.raises(NovelAIResponseError):
        _json_object(b"invalid")
    with pytest.raises(NovelAIResponseError):
        _json_object(b"[]")

    import io
    import zipfile

    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, "w") as archive:
        archive.writestr("image.png", PNG)
    assert _first_image(zipped.getvalue(), filename="renamed.png").filename == (
        "renamed.png"
    )
    assert _process_event("retry") == ("str", None, None)
    assert _process_event({"event_type": "final", "image": PNG})[1] == PNG
    assert _process_event({"event_type": "final", "image": "cG5n"})[1] == b"png"
    assert _process_event({"event_type": "final", "image": "!"})[2]
    assert _process_event({"event_type": "final", "image": 1})[2]
    assert _process_event({"event_type": "error", "code": 500})[2]
    assert _process_event({"event_type": "retry"}) == ("retry", None, None)


def test_service_constructs_configured_client_and_rejects_missing_credentials() -> None:
    with pytest.raises(NovelAIAuthenticationError):
        create_novelai_client(NovelAIConfig())
    client = create_novelai_client(
        NovelAIConfig(
            token="token",
            base_url="https://image.example/",
            account_base_url="https://account.example/",
            timeout=9,
            vibe_cache_entries=3,
        )
    )
    assert client.image_base_url == "https://image.example"
    assert client.account_base_url == "https://account.example"
    assert client.timeout == 9
    assert client.vibe_cache_entries == 3


async def test_client_generates_v4_batch_and_v3_zip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    v4 = SimpleNamespace(
        status_code=200,
        content=frame({
            "event_type": "final",
            "samp_ix": 0,
            "gen_id": "g",
            "image": PNG,
        }),
    )
    import io
    import zipfile

    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, "w") as archive:
        archive.writestr("image.png", PNG)
    driver, call = driver_with(
        v4, SimpleNamespace(status_code=200, content=zipped.getvalue())
    )
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client.get_driver",
        lambda: driver,
    )
    client = NovelAIClient(NovelAICredentials(token="token"))
    assert len(await client.generate(GenerationRequest(prompt="cat"))) == 1
    assert (
        len(await client.generate(GenerationRequest(prompt="cat", model=Model.V3))) == 1
    )
    assert call.await_args_list[0].args[0].url.path.endswith("generate-image-stream")
    assert call.await_args_list[1].args[0].url.path.endswith("generate-image")


@pytest.mark.parametrize(
    ("operation", "endpoint"),
    [
        ("director", "/ai/augment-image"),
        ("upscale", "/ai/upscale"),
        ("annotate", "/ai/annotate-image"),
        ("tags", "/ai/generate-image/suggest-tags"),
        ("subscription", "/user/subscription"),
        ("user", "/user/data"),
    ],
)
async def test_client_exposes_every_non_generation_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    endpoint: str,
) -> None:
    content = (
        json.dumps({"tags": [{"tag": "cat"}]}).encode() if operation == "tags" else PNG
    )
    if operation in {"subscription", "user"}:
        content = b'{"ok":true}'
    driver, call = driver_with(SimpleNamespace(status_code=200, content=content))
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client.get_driver",
        lambda: driver,
    )
    client = NovelAIClient(NovelAICredentials(token="token"))
    if operation == "director":
        await client.director(DirectorTool.LINE_ART, PNG)
    elif operation == "upscale":
        await client.upscale(PNG, factor=2)
    elif operation == "annotate":
        await client.annotate(PNG, ControlNetModel.SCRIBBLER)
    elif operation == "tags":
        assert await client.suggest_tags("ca") == ({"tag": "cat"},)
    elif operation == "subscription":
        assert await client.get_subscription() == {"ok": True}
    else:
        assert await client.get_user_data() == {"ok": True}
    await_args = call.await_args
    assert await_args is not None
    assert await_args.args[0].url.path.endswith(endpoint)


async def test_director_emotion_builds_native_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver, call = driver_with(SimpleNamespace(status_code=200, content=PNG))
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client.get_driver",
        lambda: driver,
    )
    client = NovelAIClient(NovelAICredentials(token="token"))
    await client.director(
        DirectorTool.EMOTION,
        PNG,
        prompt="freckles",
        emotion=Emotion.HAPPY,
        emotion_level=EmotionLevel.WEAK,
    )
    await_args = call.await_args
    assert await_args is not None
    payload = await_args.args[0].json
    assert payload["prompt"] == "happy;;freckles,"
    assert payload["defry"] == 2


async def test_v4_vibe_references_are_encoded_once_and_cached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    encoded = SimpleNamespace(status_code=200, content=b"vibe-token")
    generated = SimpleNamespace(
        status_code=200,
        content=frame({
            "event_type": "final",
            "samp_ix": 0,
            "gen_id": "g",
            "image": PNG,
        }),
    )
    driver, call = driver_with(encoded, generated, generated)
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client.get_driver",
        lambda: driver,
    )
    client = NovelAIClient(NovelAICredentials(token="token"))
    request = GenerationRequest(prompt="cat", references=("raw-reference",))
    await client.generate(request)
    await client.generate(request)
    urls = [str(item.args[0].url) for item in call.await_args_list]
    assert sum(url.endswith("/ai/encode-vibe") for url in urls) == 1


async def test_vibe_cache_survives_client_recreation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    encoded = SimpleNamespace(status_code=200, content=b"shared-token")
    generated = SimpleNamespace(
        status_code=200,
        content=frame({
            "event_type": "final",
            "samp_ix": 0,
            "gen_id": "g",
            "image": PNG,
        }),
    )
    driver, call = driver_with(encoded, generated, generated)
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client.get_driver",
        lambda: driver,
    )
    request = GenerationRequest(prompt="cat", references=("new-raw-reference",))
    await NovelAIClient(NovelAICredentials(token="token")).generate(request)
    await NovelAIClient(NovelAICredentials(token="token")).generate(request)

    urls = [str(item.args[0].url) for item in call.await_args_list]
    assert sum(url.endswith("/ai/encode-vibe") for url in urls) == 1


async def test_username_password_login_uses_account_host_and_tracking_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver, call = driver_with(
        SimpleNamespace(status_code=200, content=b'{"accessToken":"derived-token"}'),
        SimpleNamespace(status_code=200, content=b'{"ok":true}'),
    )
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client.get_driver",
        lambda: driver,
    )
    client = NovelAIClient(
        NovelAICredentials(username="user", password="password"),
        account_base_url="https://account.example",
    )

    assert await client.get_user_data() == {"ok": True}
    login_request = call.await_args_list[0].args[0]
    account_request = call.await_args_list[1].args[0]
    assert str(login_request.url) == "https://account.example/user/login"
    assert len(login_request.json["key"]) == 64
    assert account_request.headers["Authorization"] == "Bearer derived-token"
    assert len(account_request.headers["x-correlation-id"]) == 6
    assert account_request.headers["x-initiated-at"].endswith("Z")


async def test_client_maps_transport_timeout_to_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver, _ = driver_with(TimeoutError("slow"))
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client.get_driver",
        lambda: driver,
    )
    client = NovelAIClient(NovelAICredentials(token="token"))

    with pytest.raises(NovelAITimeoutError):
        await client.get_user_data()


async def test_stream_generation_yields_split_messagepack_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = frame({
        "event_type": "final",
        "samp_ix": 0,
        "gen_id": "g",
        "image": PNG,
    })

    class SessionContext:
        async def __aenter__(self) -> Any:
            async def stream_request(_: object) -> Any:
                yield SimpleNamespace(status_code=200, content=content[:5])
                yield SimpleNamespace(status_code=200, content=content[5:])

            return SimpleNamespace(stream_request=stream_request)

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client.get_driver",
        lambda: SimpleNamespace(get_session=SessionContext),
    )
    client = NovelAIClient(NovelAICredentials(token="token"))

    events = [
        event
        async for event in client.stream_generation(GenerationRequest(prompt="cat"))
    ]

    assert len(events) == 1
    assert events[0].event_type == "final"
    assert events[0].image.data == PNG


async def test_stream_generation_falls_back_to_non_streaming_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = SimpleNamespace(
        status_code=200,
        content=frame({"event_type": "final", "image": PNG}),
    )
    driver, _ = driver_with(response)
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client.get_driver",
        lambda: driver,
    )
    client = NovelAIClient(NovelAICredentials(token="token"))

    events = [
        event
        async for event in client.stream_generation(GenerationRequest(prompt="cat"))
    ]

    assert len(events) == 1


async def test_client_validates_stream_tools_and_malformed_responses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = NovelAIClient(NovelAICredentials(token="token"))
    with pytest.raises(ValueError):
        _ = [
            event
            async for event in client.stream_generation(
                GenerationRequest(prompt="cat", model=Model.V3)
            )
        ]
    with pytest.raises(ValueError):
        await client.director(DirectorTool.EMOTION, PNG)
    with pytest.raises(ValueError):
        await client.upscale(PNG, factor=3)

    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client.get_driver",
        Mock(return_value=SimpleNamespace()),
    )
    with pytest.raises(NovelAITransportError):
        await client.get_user_data()


async def test_client_rejects_missing_login_token_and_invalid_tags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    driver, _ = driver_with(
        SimpleNamespace(status_code=200, content=b"{}"),
        SimpleNamespace(status_code=200, content=b'{"tags":"invalid"}'),
    )
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client.get_driver",
        lambda: driver,
    )
    with pytest.raises(NovelAIResponseError):
        await NovelAIClient(
            NovelAICredentials(username="u", password="p")
        ).get_access_token()
    with pytest.raises(NovelAIResponseError):
        await NovelAIClient(NovelAICredentials(token="token")).suggest_tags("ca")
