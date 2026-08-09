"""HTTP helpers for user-supplied media downloads."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from ipaddress import ip_address
import socket
from typing import TYPE_CHECKING, Any
from urllib.parse import ParseResult, urljoin, urlparse

from nonebot import get_driver
from nonebot.drivers import Request

if TYPE_CHECKING:
    from collections.abc import AsyncIterable

_HTTP_SCHEMES = frozenset({"http", "https"})
_HTTP_ERROR_STATUS = 400
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_MAX_REDIRECTS = 3


class UnsafeDownloadURLError(ValueError):
    """Raised when a user-supplied download URL is not safe to request."""


async def resolve_host_addresses(hostname: str, port: int) -> tuple[str, ...]:
    """Resolve a host for egress validation before the shared HTTP client runs."""
    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        msg = "download host could not be resolved"
        raise UnsafeDownloadURLError(msg) from exc
    addresses: set[str] = set()
    for info in infos:
        sockaddr = info[4]
        if isinstance(sockaddr, tuple) and sockaddr and isinstance(sockaddr[0], str):
            addresses.add(sockaddr[0])
    return tuple(addresses)


def _is_forbidden_address(address: str) -> bool:
    try:
        parsed = ip_address(address)
    except ValueError:
        return True
    return not parsed.is_global


def _parse_http_url(url: str) -> tuple[ParseResult, int]:
    parsed = urlparse(url)
    if parsed.scheme not in _HTTP_SCHEMES or parsed.hostname is None:
        msg = "image URL must be HTTP(S)"
        raise UnsafeDownloadURLError(msg)
    if parsed.username is not None or parsed.password is not None:
        msg = "image URL must not contain credentials"
        raise UnsafeDownloadURLError(msg)
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        msg = "image URL contains an invalid port"
        raise UnsafeDownloadURLError(msg) from exc
    return parsed, port


async def _validate_and_resolve_http_url(
    url: str,
) -> tuple[ParseResult, tuple[str, ...]]:
    parsed, port = _parse_http_url(url)
    addresses = await resolve_host_addresses(parsed.hostname or "", port)
    if not addresses or any(_is_forbidden_address(address) for address in addresses):
        msg = "image URL resolves to a blocked network"
        raise UnsafeDownloadURLError(msg)
    return parsed, addresses


async def validate_public_http_url(url: str) -> None:
    """Reject non-HTTP or private-network destinations before downloading."""
    await _validate_and_resolve_http_url(url)


def _response_content_bytes(content: Any) -> bytes:
    if isinstance(content, (bytes, bytearray, memoryview)):
        return bytes(content)
    if isinstance(content, str):
        return content.encode()
    msg = "downloaded image response is not binary"
    raise UnsafeDownloadURLError(msg)


@dataclass(frozen=True, slots=True)
class _SingleHopResponse:
    status_code: int
    headers: Any
    content: bytes


def _header_value(headers: Any, name: str) -> str | None:
    value = None
    if headers is not None:
        try:
            value = headers.get(name)
        except AttributeError:
            value = None
        if value is None:
            try:
                value = next(
                    (
                        item_value
                        for item_name, item_value in headers.items()
                        if str(item_name).lower() == name.lower()
                    ),
                    None,
                )
            except AttributeError:
                value = None
    if value is None:
        return None
    if isinstance(value, (tuple, list)):
        value = value[0] if value else None
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("latin-1")
    return str(value)


def _validate_declared_response_size(headers: Any, max_bytes: int) -> None:
    value = _header_value(headers, "content-length")
    if value is None:
        return
    try:
        content_length = int(value)
    except ValueError as exc:
        msg = "download response contains an invalid content length"
        raise UnsafeDownloadURLError(msg) from exc
    if content_length < 0:
        msg = "download response contains an invalid content length"
        raise UnsafeDownloadURLError(msg)
    if content_length > max_bytes:
        msg = "downloaded image is too large"
        raise UnsafeDownloadURLError(msg)


async def _read_limited_chunks(
    chunks: AsyncIterable[Any],
    max_bytes: int,
) -> bytes:
    data = bytearray()
    async for chunk in chunks:
        chunk_bytes = _response_content_bytes(chunk)
        if len(data) + len(chunk_bytes) > max_bytes:
            msg = "downloaded image is too large"
            raise UnsafeDownloadURLError(msg)
        data.extend(chunk_bytes)
    return bytes(data)


async def _read_response_content(content: Any, max_bytes: int) -> bytes:
    if hasattr(content, "__aiter__"):
        return await _read_limited_chunks(content, max_bytes)
    data = _response_content_bytes(content)
    if len(data) > max_bytes:
        msg = "downloaded image is too large"
        raise UnsafeDownloadURLError(msg)
    return data


def _peer_host(value: Any) -> str | None:
    if isinstance(value, tuple):
        value = value[0] if value else None
    if isinstance(value, str):
        return value
    return None


def _response_peer_host(response: Any) -> str | None:
    for attribute in ("peer_address", "peername"):
        peer = _peer_host(getattr(response, attribute, None))
        if peer is not None:
            return peer

    extensions = getattr(response, "extensions", None)
    network_stream = (
        extensions.get("network_stream") if isinstance(extensions, dict) else None
    )
    get_extra_info = getattr(network_stream, "get_extra_info", None)
    if callable(get_extra_info):
        for name in ("server_addr", "peername", "remote_addr"):
            peer = _peer_host(get_extra_info(name))
            if peer is not None:
                return peer

    connection = getattr(response, "connection", None)
    transport = getattr(connection, "transport", None)
    get_extra_info = getattr(transport, "get_extra_info", None)
    if callable(get_extra_info):
        peer = _peer_host(get_extra_info("peername"))
        if peer is not None:
            return peer
    return None


def _validate_peer_host(
    peer_host: str | None,
    allowed_addresses: tuple[str, ...],
    *,
    required: bool,
) -> None:
    if peer_host is None:
        if required:
            msg = "download connection address could not be verified"
            raise UnsafeDownloadURLError(msg)
        return
    try:
        peer_address = ip_address(peer_host)
        allowed = {ip_address(address) for address in allowed_addresses}
    except ValueError as exc:
        msg = "download connection address could not be verified"
        raise UnsafeDownloadURLError(msg) from exc
    if peer_address not in allowed or _is_forbidden_address(peer_host):
        msg = "download connection address does not match DNS validation"
        raise UnsafeDownloadURLError(msg)


def _request_method(request: Request) -> str:
    method = request.method
    return method.decode() if isinstance(method, bytes) else str(method)


def _request_timeout(session: Any, request: Request) -> Any:
    converter = getattr(session, "_get_timeout", None)
    if callable(converter):
        return converter(request.timeout)
    return request.timeout


def _session_client(session: Any) -> Any | None:
    try:
        return session.client
    except (AttributeError, RuntimeError):
        return None


async def _request_one_hop_httpx(
    client: Any,
    session: Any,
    request: Request,
    *,
    max_bytes: int,
    allowed_addresses: tuple[str, ...],
) -> _SingleHopResponse:
    cookies = getattr(getattr(request, "cookies", None), "jar", None)
    async with client.stream(
        _request_method(request),
        str(request.url),
        content=request.content,
        data=request.data,
        files=request.files,
        json=request.json,
        headers=tuple(request.headers.items()),
        cookies=cookies,
        timeout=_request_timeout(session, request),
        follow_redirects=False,
    ) as response:
        headers = response.headers
        _validate_declared_response_size(headers, max_bytes)
        _validate_peer_host(
            _response_peer_host(response),
            allowed_addresses,
            required=True,
        )
        status_code = response.status_code
        if status_code >= _HTTP_ERROR_STATUS or status_code in _REDIRECT_STATUSES:
            return _SingleHopResponse(status_code, headers, b"")
        content = await _read_limited_chunks(response.aiter_bytes(), max_bytes)
    return _SingleHopResponse(status_code, headers, content)


async def _request_one_hop_aiohttp(
    client: Any,
    session: Any,
    request: Request,
    *,
    max_bytes: int,
    allowed_addresses: tuple[str, ...],
) -> _SingleHopResponse:
    async with client.request(
        _request_method(request),
        str(request.url),
        data=request.content or request.data,
        json=request.json,
        headers=request.headers,
        timeout=_request_timeout(session, request),
        allow_redirects=False,
    ) as response:
        headers = response.headers
        _validate_declared_response_size(headers, max_bytes)
        _validate_peer_host(
            _response_peer_host(response),
            allowed_addresses,
            required=True,
        )
        status_code = response.status
        if status_code >= _HTTP_ERROR_STATUS or status_code in _REDIRECT_STATUSES:
            return _SingleHopResponse(status_code, headers, b"")
        content = await _read_limited_chunks(
            response.content.iter_chunked(8192),
            max_bytes,
        )
    return _SingleHopResponse(status_code, headers, content)


async def _request_one_hop_generic(
    session: Any,
    request: Request,
    *,
    max_bytes: int,
    allowed_addresses: tuple[str, ...],
) -> _SingleHopResponse:
    response = await session.request(request)
    headers = getattr(response, "headers", None)
    _validate_declared_response_size(headers, max_bytes)
    _validate_peer_host(
        _response_peer_host(response),
        allowed_addresses,
        required=False,
    )
    status_code = getattr(response, "status_code", 200)
    if status_code >= _HTTP_ERROR_STATUS or status_code in _REDIRECT_STATUSES:
        return _SingleHopResponse(status_code, headers, b"")
    content = await _read_response_content(
        getattr(response, "content", b""),
        max_bytes,
    )
    return _SingleHopResponse(status_code, headers, content)


async def _request_one_hop(
    session: Any,
    request: Request,
    *,
    max_bytes: int,
    allowed_addresses: tuple[str, ...],
) -> _SingleHopResponse:
    client = _session_client(session)
    if client is not None and callable(getattr(client, "stream", None)):
        return await _request_one_hop_httpx(
            client,
            session,
            request,
            max_bytes=max_bytes,
            allowed_addresses=allowed_addresses,
        )
    if client is not None and callable(getattr(client, "request", None)):
        return await _request_one_hop_aiohttp(
            client,
            session,
            request,
            max_bytes=max_bytes,
            allowed_addresses=allowed_addresses,
        )
    return await _request_one_hop_generic(
        session,
        request,
        max_bytes=max_bytes,
        allowed_addresses=allowed_addresses,
    )


def _redirect_url(current_url: str, headers: Any) -> str:
    location = _header_value(headers, "location")
    if not location:
        msg = "download response contains an invalid redirect"
        raise UnsafeDownloadURLError(msg)
    next_url = urljoin(current_url, location)
    current_scheme = urlparse(current_url).scheme
    next_scheme = urlparse(next_url).scheme
    if current_scheme == "https" and next_scheme != "https":
        msg = "insecure redirect is not allowed"
        raise UnsafeDownloadURLError(msg)
    return next_url


async def download_public_http_bytes(
    url: str,
    *,
    max_bytes: int,
    request_timeout: float | None = None,
) -> bytes | None:
    """Download bytes from a public HTTP(S) URL with size and status checks."""
    if max_bytes < 0:
        msg = "download size limit must not be negative"
        raise UnsafeDownloadURLError(msg)
    get_session = getattr(get_driver(), "get_session", None)
    if get_session is None:
        return None
    async with get_session() as session:
        current_url = url
        for redirect_count in range(_MAX_REDIRECTS + 1):
            _, allowed_addresses = await _validate_and_resolve_http_url(current_url)
            request = Request("GET", current_url, timeout=request_timeout)
            response = await _request_one_hop(
                session,
                request,
                max_bytes=max_bytes,
                allowed_addresses=allowed_addresses,
            )
            if response.status_code in _REDIRECT_STATUSES:
                if redirect_count >= _MAX_REDIRECTS:
                    msg = "too many redirects while downloading image"
                    raise UnsafeDownloadURLError(msg)
                current_url = _redirect_url(current_url, response.headers)
                continue
            if response.status_code >= _HTTP_ERROR_STATUS:
                msg = "image download failed"
                raise UnsafeDownloadURLError(msg)
            return response.content
    return None
