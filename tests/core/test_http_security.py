from collections.abc import AsyncIterator
import socket
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import http_security
from src.plugins.nonebot_plugin_lingchu_bot.core.http_security import (
    UnsafeDownloadURLError,
    _header_value,
    _is_forbidden_address,
    _parse_http_url,
    _read_response_content,
    _redirect_url,
    _request_one_hop,
    _response_content_bytes,
    _response_peer_host,
    _validate_declared_response_size,
    _validate_peer_host,
    download_public_http_bytes,
    validate_public_http_url,
)


@pytest.mark.asyncio
async def test_validate_public_http_url_rejects_private_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        http_security,
        "resolve_host_addresses",
        AsyncMock(return_value=("127.0.0.1",)),
    )

    with pytest.raises(UnsafeDownloadURLError):
        await validate_public_http_url("http://example.com/image.png")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    (
        "ftp://example.com/image.png",
        "http://user:password@example.com/image.png",
        "http://example.com:not-a-port/image.png",
    ),
)
async def test_validate_public_http_url_rejects_invalid_urls(url: str) -> None:
    with pytest.raises(UnsafeDownloadURLError):
        await validate_public_http_url(url)


@pytest.mark.asyncio
async def test_validate_public_http_url_rejects_unresolved_or_mixed_addresses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolve = AsyncMock(return_value=())
    monkeypatch.setattr(http_security, "resolve_host_addresses", resolve)

    with pytest.raises(UnsafeDownloadURLError):
        await validate_public_http_url("https://example.com/image.png")

    resolve.return_value = ("93.184.216.34", "127.0.0.1")
    with pytest.raises(UnsafeDownloadURLError):
        await validate_public_http_url("https://example.com/image.png")


@pytest.mark.asyncio
async def test_validate_public_http_url_wraps_dns_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        http_security.asyncio,
        "to_thread",
        AsyncMock(side_effect=socket.gaierror("no such host")),
    )

    with pytest.raises(UnsafeDownloadURLError):
        await validate_public_http_url("https://example.com/image.png")


def test_http_response_helpers_validate_binary_content_headers_and_size() -> None:
    assert _is_forbidden_address("127.0.0.1") is True
    assert _is_forbidden_address("not-an-ip") is True
    assert _is_forbidden_address("93.184.216.34") is False

    assert _parse_http_url("https://example.com/image.png")[1] == 443
    assert _response_content_bytes(b"png") == b"png"
    assert _response_content_bytes(bytearray(b"png")) == b"png"
    assert _response_content_bytes(memoryview(b"png")) == b"png"
    assert _response_content_bytes("png") == b"png"
    with pytest.raises(UnsafeDownloadURLError):
        _response_content_bytes(object())

    assert _header_value({"content-length": "3"}, "content-length") == "3"
    assert _header_value({"Content-Length": [b"3"]}, "content-length") == "3"
    assert _header_value({"content-length": []}, "content-length") is None
    assert _header_value(None, "content-length") is None

    class ItemsOnly:
        def items(self) -> tuple[tuple[str, str], ...]:
            return (("X-Test", "yes"),)

    assert _header_value(ItemsOnly(), "x-test") == "yes"

    class BrokenHeaders:
        def get(self, _name: str) -> None:
            raise AttributeError

        def items(self) -> None:
            raise AttributeError

    assert _header_value(BrokenHeaders(), "x-test") is None

    _validate_declared_response_size({"content-length": "3"}, 3)
    with pytest.raises(UnsafeDownloadURLError):
        _validate_declared_response_size({"content-length": "nope"}, 3)
    with pytest.raises(UnsafeDownloadURLError):
        _validate_declared_response_size({"content-length": "-1"}, 3)
    with pytest.raises(UnsafeDownloadURLError):
        _validate_declared_response_size({"content-length": "4"}, 3)


@pytest.mark.asyncio
async def test_response_content_and_peer_validation_cover_stream_and_fallback_paths() -> (
    None
):
    async def chunks() -> AsyncIterator[Any]:
        yield bytearray(b"12")
        yield memoryview(b"3")

    assert await _read_response_content(chunks(), 3) == b"123"
    with pytest.raises(UnsafeDownloadURLError):
        await _read_response_content(b"1234", 3)

    async def oversized_chunks() -> AsyncIterator[bytes]:
        yield b"12"
        yield b"34"

    with pytest.raises(UnsafeDownloadURLError):
        await _read_response_content(oversized_chunks(), 3)

    assert (
        _response_peer_host(SimpleNamespace(peer_address=("93.184.216.34", 443)))
        == "93.184.216.34"
    )
    stream = SimpleNamespace(
        get_extra_info=lambda name: "93.184.216.34" if name == "peername" else None
    )
    assert (
        _response_peer_host(SimpleNamespace(extensions={"network_stream": stream}))
        == "93.184.216.34"
    )
    transport = SimpleNamespace(get_extra_info=lambda _name: ("93.184.216.34", 443))
    assert (
        _response_peer_host(
            SimpleNamespace(connection=SimpleNamespace(transport=transport))
        )
        == "93.184.216.34"
    )
    assert _response_peer_host(SimpleNamespace()) is None

    allowed = ("93.184.216.34",)
    _validate_peer_host("93.184.216.34", allowed, required=True)
    _validate_peer_host(None, allowed, required=False)
    with pytest.raises(UnsafeDownloadURLError):
        _validate_peer_host(None, allowed, required=True)
    with pytest.raises(UnsafeDownloadURLError):
        _validate_peer_host("not-an-ip", allowed, required=True)
    with pytest.raises(UnsafeDownloadURLError):
        _validate_peer_host("1.1.1.1", allowed, required=True)


@pytest.mark.asyncio
async def test_request_one_hop_supports_httpx_and_aiohttp_clients() -> None:
    request = cast(
        "Any",
        SimpleNamespace(
            method=b"GET",
            url="https://example.com/image.png",
            content=None,
            data=None,
            files=None,
            json=None,
            headers={},
            cookies=None,
            timeout=1.0,
        ),
    )
    allowed = ("93.184.216.34",)

    async def httpx_body() -> AsyncIterator[bytes]:
        yield b"ok"

    class HttpxContext:
        async def __aenter__(self) -> Any:
            return SimpleNamespace(
                status_code=200,
                headers={"Content-Length": "2"},
                peer_address="93.184.216.34",
                aiter_bytes=httpx_body,
            )

        async def __aexit__(self, *args: object) -> None:
            del args

    class HttpxClient:
        def stream(self, *args: object, **kwargs: object) -> HttpxContext:
            del args, kwargs
            return HttpxContext()

    httpx_client = HttpxClient()
    httpx_response = await _request_one_hop(
        SimpleNamespace(client=httpx_client),
        request,
        max_bytes=2,
        allowed_addresses=allowed,
    )
    assert httpx_response.content == b"ok"

    async def aiohttp_body() -> AsyncIterator[bytes]:
        yield b"ok"

    class AiohttpContent:
        def iter_chunked(self, _size: int) -> AsyncIterator[bytes]:
            return aiohttp_body()

    class AiohttpContext:
        async def __aenter__(self) -> Any:
            return SimpleNamespace(
                status=200,
                headers={},
                peername=("93.184.216.34", 443),
                content=AiohttpContent(),
            )

        async def __aexit__(self, *args: object) -> None:
            del args

    class AiohttpClient:
        def request(self, *args: object, **kwargs: object) -> AiohttpContext:
            del args, kwargs
            return AiohttpContext()

    aiohttp_client = AiohttpClient()
    aiohttp_response = await _request_one_hop(
        SimpleNamespace(client=aiohttp_client),
        request,
        max_bytes=2,
        allowed_addresses=allowed,
    )
    assert aiohttp_response.content == b"ok"


@pytest.mark.asyncio
async def test_request_one_hop_uses_generic_client_when_no_native_client() -> None:
    request = cast(
        "Any",
        SimpleNamespace(
            method="GET",
            url="https://example.com/image.png",
            content=None,
            data=None,
            files=None,
            json=None,
            headers={},
            cookies=None,
            timeout=1.0,
        ),
    )

    class GenericSession:
        request = AsyncMock(
            return_value=SimpleNamespace(status_code=200, content=b"ok")
        )

        @property
        def client(self) -> None:
            raise RuntimeError

    response = await _request_one_hop(
        GenericSession(),
        request,
        max_bytes=2,
        allowed_addresses=("93.184.216.34",),
    )
    assert response.content == b"ok"


def test_redirect_and_request_helpers_reject_invalid_inputs() -> None:
    with pytest.raises(UnsafeDownloadURLError):
        _redirect_url("https://example.com/image.png", {})
    with pytest.raises(UnsafeDownloadURLError):
        _redirect_url(
            "https://example.com/image.png",
            {"Location": "http://example.com/other.png"},
        )


@pytest.mark.asyncio
async def test_download_public_http_bytes_checks_status_and_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        http_security,
        "resolve_host_addresses",
        AsyncMock(return_value=("93.184.216.34",)),
    )
    request = AsyncMock(return_value=SimpleNamespace(status_code=200, content=b"png"))

    class SessionContext:
        async def __aenter__(self) -> Any:
            return SimpleNamespace(request=request)

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        http_security,
        "get_driver",
        lambda: SimpleNamespace(get_session=SessionContext),
    )

    assert (
        await download_public_http_bytes("https://example.com/image.png", max_bytes=3)
        == b"png"
    )
    with pytest.raises(UnsafeDownloadURLError):
        await download_public_http_bytes("https://example.com/image.png", max_bytes=2)


@pytest.mark.asyncio
async def test_download_public_http_bytes_revalidates_each_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolve = AsyncMock(
        side_effect=[("93.184.216.34",), ("1.1.1.1",)],
    )
    monkeypatch.setattr(http_security, "resolve_host_addresses", resolve)
    request = AsyncMock(
        side_effect=[
            SimpleNamespace(
                status_code=302,
                headers={"Location": "/image.png"},
                content=b"",
            ),
            SimpleNamespace(
                status_code=200,
                headers={"Content-Length": "3"},
                content=b"png",
            ),
        ]
    )

    class SessionContext:
        async def __aenter__(self) -> Any:
            return SimpleNamespace(request=request)

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        http_security,
        "get_driver",
        lambda: SimpleNamespace(get_session=SessionContext),
    )

    assert (
        await download_public_http_bytes("https://example.com/image.png", max_bytes=3)
        == b"png"
    )
    assert request.await_count == 2
    assert resolve.await_count == 2
    assert (
        str(request.await_args_list[1].args[0].url) == "https://example.com/image.png"
    )


@pytest.mark.asyncio
async def test_download_public_http_bytes_rejects_private_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        http_security,
        "resolve_host_addresses",
        AsyncMock(side_effect=[("93.184.216.34",), ("127.0.0.1",)]),
    )
    request = AsyncMock(
        return_value=SimpleNamespace(
            status_code=302,
            headers={"Location": "http://internal.example/image.png"},
            content=b"",
        )
    )

    class SessionContext:
        async def __aenter__(self) -> Any:
            return SimpleNamespace(request=request)

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        http_security,
        "get_driver",
        lambda: SimpleNamespace(get_session=SessionContext),
    )

    with pytest.raises(UnsafeDownloadURLError):
        await download_public_http_bytes("https://example.com/image.png", max_bytes=3)
    request.assert_awaited_once()


@pytest.mark.asyncio
async def test_download_public_http_bytes_rejects_https_downgrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        http_security,
        "resolve_host_addresses",
        AsyncMock(return_value=("93.184.216.34",)),
    )
    request = AsyncMock(
        return_value=SimpleNamespace(
            status_code=302,
            headers={"Location": "http://example.com/image.png"},
            content=b"",
        )
    )

    class SessionContext:
        async def __aenter__(self) -> Any:
            return SimpleNamespace(request=request)

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        http_security,
        "get_driver",
        lambda: SimpleNamespace(get_session=SessionContext),
    )

    with pytest.raises(UnsafeDownloadURLError):
        await download_public_http_bytes("https://example.com/image.png", max_bytes=3)


@pytest.mark.asyncio
async def test_download_public_http_bytes_rejects_connection_address_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        http_security,
        "resolve_host_addresses",
        AsyncMock(return_value=("93.184.216.34",)),
    )
    request = AsyncMock(
        return_value=SimpleNamespace(
            status_code=200,
            headers={"Content-Length": "3"},
            content=b"png",
            peer_address=("10.0.0.1", 80),
        )
    )

    class SessionContext:
        async def __aenter__(self) -> Any:
            return SimpleNamespace(request=request)

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        http_security,
        "get_driver",
        lambda: SimpleNamespace(get_session=SessionContext),
    )

    with pytest.raises(UnsafeDownloadURLError):
        await download_public_http_bytes("https://example.com/image.png", max_bytes=3)


@pytest.mark.asyncio
async def test_download_public_http_bytes_limits_streamed_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        http_security,
        "resolve_host_addresses",
        AsyncMock(return_value=("93.184.216.34",)),
    )

    async def body() -> Any:
        yield b"12"
        yield b"345"

    request = AsyncMock(
        return_value=SimpleNamespace(
            status_code=200,
            headers={},
            content=body(),
        )
    )

    class SessionContext:
        async def __aenter__(self) -> Any:
            return SimpleNamespace(request=request)

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        http_security,
        "get_driver",
        lambda: SimpleNamespace(get_session=SessionContext),
    )

    with pytest.raises(UnsafeDownloadURLError):
        await download_public_http_bytes("https://example.com/image.png", max_bytes=4)
