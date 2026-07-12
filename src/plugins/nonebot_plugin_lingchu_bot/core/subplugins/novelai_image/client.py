"""Clean-room minimal NovelAI V4.5 HTTP client."""

# ruff: noqa: TRY003

from __future__ import annotations

import base64
import struct
from typing import TYPE_CHECKING

import msgpack
from nonebot import get_driver
from nonebot.drivers import Request

from .payload import build_payload

if TYPE_CHECKING:
    from .config import NovelAIConfig
    from .models import NovelAIGenerationPlan

HTTP_BAD_REQUEST = 400


class NovelAIError(RuntimeError):
    pass


class MissingNovelAITokenError(NovelAIError):
    pass


class NovelAIProviderError(NovelAIError):
    pass


class NovelAITransportError(NovelAIError):
    pass


class NovelAIResponseError(NovelAIError):
    pass


def extract_final_image(content: bytes) -> bytes:
    offset = 0
    final: bytes | None = None
    try:
        while offset + 4 <= len(content):
            length = struct.unpack(">I", content[offset : offset + 4])[0]
            start, end = offset + 4, offset + 4 + length
            if end > len(content):
                raise NovelAIResponseError("Truncated msgpack frame")
            event = msgpack.unpackb(content[start:end], raw=False)
            if isinstance(event, dict) and event.get("event_type") == "final":
                image = event.get("image")
                if isinstance(image, bytes):
                    final = image
                elif isinstance(image, str):
                    final = base64.b64decode(image, validate=True)
                else:
                    raise NovelAIResponseError("Invalid final image value")
            offset = end
    except (TypeError, ValueError, msgpack.UnpackException) as exc:
        raise NovelAIResponseError("Invalid msgpack image stream") from exc
    if final is None:
        raise NovelAIResponseError("No final image in stream")
    return final


async def generate_image(
    plan: NovelAIGenerationPlan,
    *,
    config: NovelAIConfig,
) -> bytes:
    if not config.token:
        raise MissingNovelAITokenError("NovelAI token is not configured")
    http_request = Request(
        "POST",
        f"{config.base_url.rstrip('/')}/ai/generate-image-stream",
        headers={
            "Authorization": f"Bearer {config.token}",
            "Accept": "application/x-msgpack",
            "Content-Type": "application/json",
        },
        json=build_payload(plan, model=config.model),
        timeout=config.timeout,
    )
    get_session = getattr(get_driver(), "get_session", None)
    if get_session is None:
        raise NovelAIError("NoneBot HTTP client is unavailable")
    try:
        async with get_session() as session:
            response = await session.request(http_request)
    except Exception as exc:
        raise NovelAITransportError("NovelAI request transport failed") from exc
    if response.status_code >= HTTP_BAD_REQUEST:
        raise NovelAIProviderError(f"NovelAI returned HTTP {response.status_code}")
    content = response.content
    if isinstance(content, str):
        content = content.encode()
    if not isinstance(content, bytes):
        raise NovelAIResponseError("NovelAI response has no binary content")
    return extract_final_image(content)
