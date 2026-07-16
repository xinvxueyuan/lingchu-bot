"""HTTP helpers for user-supplied media downloads."""

from __future__ import annotations

import asyncio
from ipaddress import ip_address
import socket
from typing import Any
from urllib.parse import urlparse

from nonebot import get_driver
from nonebot.drivers import Request

_HTTP_SCHEMES = frozenset({"http", "https"})
_HTTP_ERROR_STATUS = 400


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
    parsed = ip_address(address)
    return (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_link_local
        or parsed.is_multicast
        or parsed.is_reserved
        or parsed.is_unspecified
    )


async def validate_public_http_url(url: str) -> None:
    """Reject non-HTTP or private-network destinations before downloading."""
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

    addresses = await resolve_host_addresses(parsed.hostname, port)
    if not addresses or any(_is_forbidden_address(address) for address in addresses):
        msg = "image URL resolves to a blocked network"
        raise UnsafeDownloadURLError(msg)


def _response_content_bytes(content: Any) -> bytes:
    if isinstance(content, bytes):
        return content
    if isinstance(content, str):
        return content.encode()
    msg = "downloaded image response is not binary"
    raise UnsafeDownloadURLError(msg)


async def download_public_http_bytes(
    url: str,
    *,
    max_bytes: int,
    request_timeout: float | None = None,
) -> bytes | None:
    """Download bytes from a public HTTP(S) URL with size and status checks."""
    await validate_public_http_url(url)
    get_session = getattr(get_driver(), "get_session", None)
    if get_session is None:
        return None
    async with get_session() as session:
        request = Request("GET", url, timeout=request_timeout)
        response = await session.request(request)

    status_code = getattr(response, "status_code", 200)
    if status_code >= _HTTP_ERROR_STATUS:
        msg = "image download failed"
        raise UnsafeDownloadURLError(msg)
    data = _response_content_bytes(getattr(response, "content", b""))
    if len(data) > max_bytes:
        msg = "downloaded image is too large"
        raise UnsafeDownloadURLError(msg)
    return data
