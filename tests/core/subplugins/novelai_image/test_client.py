import struct
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import msgpack
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client import (
    MissingNovelAITokenError,
    NovelAIProviderError,
    NovelAIResponseError,
    NovelAITransportError,
    extract_final_image,
    generate_image,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.config import (
    NovelAIConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.models import (
    NovelAIGenerationPlan,
)


def frame(value: object) -> bytes:
    payload = cast("bytes", msgpack.packb(value))
    return struct.pack(">I", len(payload)) + payload


def test_extract_final_image_uses_last_final_event() -> None:
    content = frame({"event_type": "intermediate", "image": b"x"}) + frame({
        "event_type": "final",
        "image": b"png",
    })

    assert extract_final_image(content) == b"png"


def test_extract_final_image_rejects_truncated_stream() -> None:
    with pytest.raises(NovelAIResponseError):
        extract_final_image(struct.pack(">I", 5) + b"x")


def test_extract_final_image_raises_on_error_event() -> None:
    content = frame({"event_type": "error", "code": 500, "message": "internal error"})
    with pytest.raises(NovelAIResponseError) as exc_info:
        extract_final_image(content)
    assert "500" in str(exc_info.value)
    assert "internal error" in str(exc_info.value)


def test_extract_final_image_error_event_before_final() -> None:
    content = frame({"event_type": "error", "code": 402, "message": "cost"}) + frame({
        "event_type": "final",
        "image": b"png",
    })
    with pytest.raises(NovelAIResponseError) as exc_info:
        extract_final_image(content)
    assert "402" in str(exc_info.value)
    assert "cost" in str(exc_info.value)


def test_extract_final_image_skips_retry_event() -> None:
    content = frame({"event_type": "retry", "message": "transient"}) + frame({
        "event_type": "final",
        "image": b"png",
    })

    assert extract_final_image(content) == b"png"


def request() -> NovelAIGenerationPlan:
    return NovelAIGenerationPlan(
        prompt="A cat, cat",
        negative_prompt="text",
        width=832,
        height=1216,
        steps=28,
        scale=5,
        sampler="k_euler_ancestral",
        seed=42,
        base_caption="A cat",
        char_captions=(),
        character_prompts=(),
        use_coords=False,
    )


async def test_generate_image_requires_token() -> None:
    with pytest.raises(MissingNovelAITokenError):
        await generate_image(request(), config=NovelAIConfig())


async def test_generate_image_sends_stream_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = SimpleNamespace(
        status_code=200,
        content=frame({"event_type": "final", "image": b"png"}),
    )
    request_call = AsyncMock(return_value=response)

    class SessionContext:
        async def __aenter__(self) -> Any:
            return SimpleNamespace(request=request_call)

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client.get_driver",
        lambda: SimpleNamespace(get_session=SessionContext),
    )

    result = await generate_image(
        request(),
        config=NovelAIConfig(token="token", timeout=9),
    )

    assert result == b"png"
    assert request_call.await_args is not None
    sent = request_call.await_args.args[0]
    assert str(sent.url).endswith("/ai/generate-image-stream")
    assert sent.headers["Authorization"] == "Bearer token"
    assert sent.timeout == 9


async def test_generate_image_rejects_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_call = AsyncMock(return_value=SimpleNamespace(status_code=401, content=b""))

    class SessionContext:
        async def __aenter__(self) -> Any:
            return SimpleNamespace(request=request_call)

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client.get_driver",
        lambda: SimpleNamespace(get_session=SessionContext),
    )

    with pytest.raises(NovelAIProviderError):
        await generate_image(request(), config=NovelAIConfig(token="token"))


async def test_generate_image_wraps_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_call = AsyncMock(side_effect=OSError("connection failed"))

    class SessionContext:
        async def __aenter__(self) -> Any:
            return SimpleNamespace(request=request_call)

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image.client.get_driver",
        lambda: SimpleNamespace(get_session=SessionContext),
    )

    with pytest.raises(NovelAITransportError) as exc_info:
        await generate_image(request(), config=NovelAIConfig(token="token"))

    assert isinstance(exc_info.value.__cause__, OSError)
