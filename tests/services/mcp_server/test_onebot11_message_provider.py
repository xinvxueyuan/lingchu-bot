from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import override
from unittest.mock import AsyncMock

import httpx
from nonebot.adapters.onebot.v11 import ActionFailed, Message, NetworkError
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.http_security import (
    UnsafeDownloadURLError,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.contracts import (
    BotAddress,
    ConversationAddress,
    ErrorCode,
    ImageSegment,
    OperationStatus,
    SendMessageRequest,
    TextSegment,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.onebot11_messages import (
    OneBotV11MessageProvider,
    ProviderLimits,
    PublicHttpsImageFetcher,
)


def request(
    conversation_type: str = "group",
    conversation_id: str = "20001",
) -> SendMessageRequest:
    return SendMessageRequest(
        BotAddress("qq", "~onebot.v11", "default", "10001"),
        ConversationAddress(conversation_type, conversation_id),
        (
            TextSegment("before"),
            ImageSegment("https://images.example/a.png"),
            TextSegment("after"),
        ),
        "key-1",
    )


def image_request(count: int) -> SendMessageRequest:
    return SendMessageRequest(
        BotAddress("qq", "~onebot.v11", "default", "10001"),
        ConversationAddress("group", "20001"),
        tuple(
            ImageSegment(f"https://images.example/{index}.png")
            for index in range(count)
        ),
        "key-images",
    )


@pytest.mark.asyncio
async def test_provider_preserves_order_and_sends_one_group_message() -> None:
    bot = AsyncMock()
    bot.send_group_msg.return_value = {"message_id": 42}
    fetch = AsyncMock(return_value=b"image")
    provider = OneBotV11MessageProvider(fetch_image=fetch, operation_id=lambda: "op-1")

    result = await provider.send_message(bot, request())

    sent = bot.send_group_msg.await_args.kwargs
    assert sent["group_id"] == 20001
    assert isinstance(sent["message"], Message)
    assert [segment.type for segment in sent["message"]] == ["text", "image", "text"]
    assert sent["message"][0].data["text"] == "before"
    assert sent["message"][2].data["text"] == "after"
    bot.send_group_msg.assert_awaited_once()
    bot.send_private_msg.assert_not_called()
    assert result.operation_id == "op-1"
    assert result.status is OperationStatus.SUCCEEDED
    assert result.platform_message_id == "42"
    fetch.assert_awaited_once_with(
        "https://images.example/a.png",
        max_bytes=10 * 1024 * 1024,
    )


@pytest.mark.asyncio
async def test_provider_sends_private_message_to_exact_user() -> None:
    bot = AsyncMock()
    bot.send_private_msg.return_value = {"message_id": "43"}
    provider = OneBotV11MessageProvider(
        fetch_image=AsyncMock(return_value=b"image"),
        operation_id=lambda: "op-2",
    )

    result = await provider.send_message(bot, request("private", "30001"))

    assert bot.send_private_msg.await_args.kwargs["user_id"] == 30001
    bot.send_group_msg.assert_not_called()
    assert result.platform_message_id == "43"


@pytest.mark.asyncio
async def test_provider_rejects_unsupported_conversation_without_partial_send() -> None:
    bot = AsyncMock()
    provider = OneBotV11MessageProvider(
        fetch_image=AsyncMock(return_value=b"image"),
        operation_id=lambda: "op-3",
    )

    result = await provider.send_message(bot, request("channel", "40001"))

    assert result.status is OperationStatus.REJECTED
    assert result.error_code is ErrorCode.UNSUPPORTED_MESSAGE
    bot.send_group_msg.assert_not_called()
    bot.send_private_msg.assert_not_called()


@pytest.mark.asyncio
async def test_provider_rejects_image_count_before_fetching_or_sending() -> None:
    bot = AsyncMock()
    fetch = AsyncMock(return_value=b"image")
    provider = OneBotV11MessageProvider(
        fetch_image=fetch,
        limits=ProviderLimits(max_image_count=2),
        operation_id=lambda: "op-count",
    )

    result = await provider.send_message(bot, image_request(3))

    assert result.status is OperationStatus.REJECTED
    assert result.error_code is ErrorCode.PLATFORM_REJECTED
    fetch.assert_not_awaited()
    bot.send_group_msg.assert_not_called()


@pytest.mark.asyncio
async def test_provider_rejects_total_image_bytes_after_fetching() -> None:
    bot = AsyncMock()
    fetch = AsyncMock(side_effect=[b"123", b"456"])
    provider = OneBotV11MessageProvider(
        fetch_image=fetch,
        limits=ProviderLimits(max_total_image_bytes=5),
        operation_id=lambda: "op-total",
    )

    result = await provider.send_message(bot, image_request(2))

    assert result.status is OperationStatus.REJECTED
    assert result.error_code is ErrorCode.PLATFORM_REJECTED
    assert fetch.await_count == 2
    bot.send_group_msg.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", [httpx.DecodingError("bad image"), httpx.ReadError("offline")]
)
async def test_provider_rejects_image_request_errors_before_platform_call(
    failure: Exception,
) -> None:
    bot = AsyncMock()
    provider = OneBotV11MessageProvider(
        fetch_image=AsyncMock(side_effect=failure),
        operation_id=lambda: "op-fetch-error",
    )

    result = await provider.send_message(bot, request())

    assert result.status is OperationStatus.REJECTED
    assert result.error_code is ErrorCode.PLATFORM_REJECTED
    bot.send_group_msg.assert_not_called()


@pytest.mark.asyncio
async def test_provider_maps_platform_rejection_and_uncertain_timeout() -> None:
    rejected_bot = AsyncMock()
    rejected_bot.send_group_msg.side_effect = ActionFailed(
        status="failed", retcode=100, message="bad message"
    )
    provider = OneBotV11MessageProvider(
        fetch_image=AsyncMock(return_value=b"image"),
        operation_id=lambda: "op-4",
    )

    rejected = await provider.send_message(rejected_bot, request())

    assert rejected.status is OperationStatus.REJECTED
    assert rejected.error_code is ErrorCode.PLATFORM_REJECTED

    timeout_bot = AsyncMock()
    timeout_bot.send_group_msg.side_effect = TimeoutError
    uncertain = await provider.send_message(timeout_bot, request())
    assert uncertain.status is OperationStatus.UNCERTAIN
    assert uncertain.error_code is ErrorCode.PLATFORM_FAILED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        NetworkError("connection lost"),
        httpx.ReadError("connection lost"),
        httpx.RemoteProtocolError("invalid response"),
    ],
)
async def test_provider_maps_network_failures_after_send_to_uncertain(
    failure: Exception,
) -> None:
    bot = AsyncMock()
    bot.send_group_msg.side_effect = failure
    provider = OneBotV11MessageProvider(
        fetch_image=AsyncMock(return_value=b"image"),
        operation_id=lambda: "op-network",
    )

    result = await provider.send_message(bot, request())

    assert result.status is OperationStatus.UNCERTAIN
    assert result.error_code is ErrorCode.PLATFORM_FAILED


@pytest.mark.asyncio
async def test_provider_treats_invalid_response_after_send_as_uncertain() -> None:
    bot = AsyncMock()
    bot.send_group_msg.return_value = "invalid"
    provider = OneBotV11MessageProvider(
        fetch_image=AsyncMock(return_value=b"image"),
        operation_id=lambda: "op-invalid",
    )

    result = await provider.send_message(bot, request())

    assert result.status is OperationStatus.UNCERTAIN
    assert result.error_code is ErrorCode.PLATFORM_FAILED


@pytest.mark.asyncio
async def test_provider_propagates_cancellation() -> None:
    bot = AsyncMock()
    bot.send_group_msg.side_effect = asyncio.CancelledError
    sink = AsyncMock()
    provider = OneBotV11MessageProvider(
        fetch_image=AsyncMock(return_value=b"image"),
        operation_id=lambda: "op-5",
        uncertainty_sink=sink,
    )

    with pytest.raises(asyncio.CancelledError):
        await provider.send_message(bot, request())
    sink.record_uncertain.assert_awaited_once_with(
        "op-5",
        ErrorCode.PLATFORM_FAILED,
    )


@dataclass(slots=True)
class RecordingTransport(httpx.AsyncBaseTransport):
    responses: list[httpx.Response]
    requests: list[httpx.Request] = field(default_factory=list[httpx.Request])

    @override
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        response = self.responses.pop(0)
        response.request = request
        return response


class ChunkStream(httpx.AsyncByteStream):
    @override
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"12"
        yield b"345"


@pytest.mark.asyncio
async def test_image_fetcher_requires_https_and_revalidates_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = RecordingTransport([
        httpx.Response(302, headers={"location": "https://cdn.example/a.png"}),
        httpx.Response(200, content=b"image"),
    ])
    resolutions = {
        "images.example": ("8.8.8.8",),
        "cdn.example": ("1.1.1.1",),
    }

    async def resolve(hostname: str, port: int) -> tuple[str, ...]:
        assert port == 443
        return resolutions[hostname]

    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.http_security.resolve_host_addresses",
        resolve,
    )
    async with httpx.AsyncClient(transport=transport) as client:
        fetcher = PublicHttpsImageFetcher(client=client)
        assert await fetcher("https://images.example/a.png", max_bytes=100) == b"image"

    assert [str(item.url) for item in transport.requests] == [
        "https://8.8.8.8/a.png",
        "https://1.1.1.1/a.png",
    ]
    assert [item.headers["host"] for item in transport.requests] == [
        "images.example",
        "cdn.example",
    ]
    assert [item.extensions["sni_hostname"] for item in transport.requests] == [
        "images.example",
        "cdn.example",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "http://images.example/a.png",
        # Use a non-platform-specific host in the ``file://`` scheme so the
        # assertion does not depend on the OS temp directory layout. The path
        # itself is irrelevant — only the scheme is checked.
        "file://images.example/a.png",
        "https://user:pass@images.example/a.png",
    ],
)
async def test_image_fetcher_rejects_unsafe_url_before_request(url: str) -> None:
    transport = RecordingTransport([])
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(UnsafeDownloadURLError):
            await PublicHttpsImageFetcher(client=client)(url, max_bytes=100)
    assert transport.requests == []


@pytest.mark.asyncio
async def test_image_fetcher_rejects_dns_rebinding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = RecordingTransport([httpx.Response(200, content=b"image")])
    answers = iter((("8.8.8.8",), ("127.0.0.1",)))

    async def resolve(hostname: str, port: int) -> tuple[str, ...]:
        assert hostname == "images.example"
        assert port == 443
        return next(answers)

    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.http_security.resolve_host_addresses",
        resolve,
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(UnsafeDownloadURLError):
            await PublicHttpsImageFetcher(client=client)(
                "https://images.example/a.png",
                max_bytes=100,
            )


@pytest.mark.asyncio
async def test_image_fetcher_maps_download_timeout_to_unsafe_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def resolve(hostname: str, port: int) -> tuple[str, ...]:
        assert hostname == "images.example"
        assert port == 443
        return ("8.8.8.8",)

    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.http_security.resolve_host_addresses",
        resolve,
    )

    async def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(UnsafeDownloadURLError):
            await PublicHttpsImageFetcher(client=client)(
                "https://images.example/a.png",
                max_bytes=100,
            )


@pytest.mark.asyncio
async def test_image_fetcher_rejects_declared_oversize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def resolve(hostname: str, port: int) -> tuple[str, ...]:
        assert hostname == "images.example"
        assert port == 443
        return ("8.8.8.8",)

    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.http_security.resolve_host_addresses",
        resolve,
    )
    transport = RecordingTransport([
        httpx.Response(200, headers={"content-length": "5"}, content=b"12345")
    ])
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(UnsafeDownloadURLError):
            await PublicHttpsImageFetcher(client=client)(
                "https://images.example/a.png",
                max_bytes=4,
            )


@pytest.mark.asyncio
async def test_image_fetcher_stops_when_streamed_bytes_exceed_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def resolve(hostname: str, port: int) -> tuple[str, ...]:
        assert hostname == "images.example"
        assert port == 443
        return ("8.8.8.8",)

    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.http_security.resolve_host_addresses",
        resolve,
    )
    transport = RecordingTransport([httpx.Response(200, stream=ChunkStream())])
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(UnsafeDownloadURLError):
            await PublicHttpsImageFetcher(client=client)(
                "https://images.example/a.png",
                max_bytes=4,
            )
