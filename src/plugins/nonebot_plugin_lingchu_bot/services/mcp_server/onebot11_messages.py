"""OneBot V11 ordered text/image message provider."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Protocol, cast
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import httpx
from nonebot.adapters.onebot.v11 import (
    ActionFailed,
    Bot,
    Message,
    MessageSegment,
    NetworkError,
)

from ...core import http_security
from ...core.http_security import UnsafeDownloadURLError
from .contracts import (
    ErrorCode,
    ImageSegment,
    OperationStatus,
    SendMessageRequest,
    SendMessageResult,
    TextSegment,
)

_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_MAX_REDIRECTS = 3
_DOWNLOAD_TIMEOUT_SECONDS = 15.0
_HTTP_ERROR_STATUS = 400
_DEFAULT_MAX_IMAGE_BYTES = 10 * 1024 * 1024
_DEFAULT_MAX_IMAGE_COUNT = 10
_DEFAULT_MAX_TOTAL_IMAGE_BYTES = 20 * 1024 * 1024
_IPV6_VERSION = 6


class _HttpsRequiredError(UnsafeDownloadURLError):
    pass


class _HostRequiredError(UnsafeDownloadURLError):
    pass


class _DnsChangedError(UnsafeDownloadURLError):
    pass


class _DownloadFailedError(UnsafeDownloadURLError):
    pass


class _DownloadTimeoutError(UnsafeDownloadURLError):
    pass


class _TooManyRedirectsError(UnsafeDownloadURLError):
    pass


class _MissingLocationError(UnsafeDownloadURLError):
    pass


class _InvalidContentLengthError(UnsafeDownloadURLError):
    pass


class _ImageTooLargeError(UnsafeDownloadURLError):
    pass


class _InvalidImageLimitsError(ValueError):
    pass


type HttpClientFactory = Callable[[], AbstractAsyncContextManager[httpx.AsyncClient]]
type OperationIdFactory = Callable[[], str]


class ImageFetcher(Protocol):
    async def __call__(self, url: str, *, max_bytes: int) -> bytes: ...


class UncertaintySink(Protocol):
    """Record that a platform call may have taken effect."""

    async def record_uncertain(
        self,
        operation_id: str,
        error_code: ErrorCode,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class ProviderLimits:
    """One platform provider's media boundaries."""

    max_image_bytes: int = _DEFAULT_MAX_IMAGE_BYTES
    max_image_count: int = _DEFAULT_MAX_IMAGE_COUNT
    max_total_image_bytes: int = _DEFAULT_MAX_TOTAL_IMAGE_BYTES

    def __post_init__(self) -> None:
        if (
            min(self.max_image_bytes, self.max_image_count, self.max_total_image_bytes)
            < 1
        ):
            raise _InvalidImageLimitsError


class _NullUncertaintySink:
    async def record_uncertain(
        self,
        operation_id: str,
        error_code: ErrorCode,
    ) -> None:
        pass


def _default_client() -> AbstractAsyncContextManager[httpx.AsyncClient]:
    return httpx.AsyncClient(follow_redirects=False, trust_env=False)


async def _validate_https(url: str) -> tuple[str, ...]:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise _HttpsRequiredError
    await http_security.validate_public_http_url(url)
    if parsed.hostname is None:
        raise _HostRequiredError
    return await http_security.resolve_host_addresses(
        parsed.hostname, parsed.port or 443
    )


def _pinned_request(url: str, address: str) -> tuple[str, str, str]:
    parsed = urlparse(url)
    if parsed.hostname is None:
        raise _HostRequiredError
    pinned_host = (
        f"[{address}]" if ip_address(address).version == _IPV6_VERSION else address
    )
    if parsed.port is not None:
        pinned_host = f"{pinned_host}:{parsed.port}"
    connect_url = parsed._replace(netloc=pinned_host).geturl()
    host_header = parsed.hostname
    if parsed.port is not None:
        host_header = f"{host_header}:{parsed.port}"
    return connect_url, host_header, parsed.hostname


def _addresses_are_public(addresses: tuple[str, ...]) -> bool:
    return bool(addresses) and all(
        not (
            (parsed := ip_address(address)).is_private
            or parsed.is_loopback
            or parsed.is_link_local
            or parsed.is_multicast
            or parsed.is_reserved
            or parsed.is_unspecified
        )
        for address in addresses
    )


class PublicHttpsImageFetcher:
    """Fetch public HTTPS bytes with explicit, revalidated redirect hops."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        client_factory: HttpClientFactory = _default_client,
        timeout: float = _DOWNLOAD_TIMEOUT_SECONDS,
    ) -> None:
        self._client = client
        self._client_factory = client_factory
        self._timeout = timeout

    async def __call__(self, url: str, *, max_bytes: int) -> bytes:
        """Download one image without imposing platform media constraints."""
        if max_bytes < 1:
            raise _ImageTooLargeError
        if self._client is not None:
            return await self._fetch(self._client, url, max_bytes=max_bytes)
        async with self._client_factory() as client:
            return await self._fetch(client, url, max_bytes=max_bytes)

    async def _fetch(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        max_bytes: int,
    ) -> bytes:
        current = url
        for redirect_count in range(_MAX_REDIRECTS + 1):
            addresses = await _validate_https(current)
            if not _addresses_are_public(addresses):
                raise _DnsChangedError
            connect_url, host_header, sni_hostname = _pinned_request(
                current, sorted(addresses)[0]
            )
            try:
                async with client.stream(
                    "GET",
                    connect_url,
                    headers={"Host": host_header},
                    extensions={"sni_hostname": sni_hostname},
                    timeout=self._timeout,
                ) as response:
                    if response.status_code in _REDIRECT_STATUSES:
                        if redirect_count == _MAX_REDIRECTS:
                            raise _TooManyRedirectsError
                        location = response.headers.get("location")
                        if not location:
                            raise _MissingLocationError
                        current = urljoin(current, location)
                        continue
                    if response.status_code >= _HTTP_ERROR_STATUS:
                        raise _DownloadFailedError
                    self._check_content_length(response, max_bytes)
                    return await self._read_limited(response, max_bytes)
            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.ProtocolError,
                httpx.DecodingError,
                httpx.RequestError,
            ) as exc:
                raise _DownloadTimeoutError from exc
        raise AssertionError

    @staticmethod
    def _check_content_length(response: httpx.Response, max_bytes: int) -> None:
        content_length = response.headers.get("content-length")
        if content_length is None:
            return
        try:
            declared_size = int(content_length)
        except ValueError as exc:
            raise _InvalidContentLengthError from exc
        if declared_size < 0:
            raise _InvalidContentLengthError
        if declared_size > max_bytes:
            raise _ImageTooLargeError

    @staticmethod
    async def _read_limited(response: httpx.Response, max_bytes: int) -> bytes:
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > max_bytes:
                raise _ImageTooLargeError
            chunks.append(chunk)
        return b"".join(chunks)


class OneBotV11MessageProvider:
    """Send one complete ordered message through the default OneBot V11 API."""

    platform_id = "qq"
    adapter_id = "~onebot.v11"
    protocol_ids = frozenset({"default"})

    def __init__(
        self,
        *,
        fetch_image: ImageFetcher | None = None,
        operation_id: OperationIdFactory | None = None,
        uncertainty_sink: UncertaintySink | None = None,
        limits: ProviderLimits | None = None,
    ) -> None:
        self._fetch_image = fetch_image or PublicHttpsImageFetcher()
        self._operation_id = operation_id or (lambda: str(uuid4()))
        self._uncertainty_sink = uncertainty_sink or _NullUncertaintySink()
        provider_limits = limits or ProviderLimits()
        self._max_image_bytes = provider_limits.max_image_bytes
        self._max_image_count = provider_limits.max_image_count
        self._max_total_image_bytes = provider_limits.max_total_image_bytes

    async def send_message(
        self,
        bot: Bot,
        request: SendMessageRequest,
    ) -> SendMessageResult:
        """Validate and send a group or private message without splitting it."""
        operation_id = self._operation_id()
        target = self._target(request)
        if target is None:
            return SendMessageResult(
                operation_id,
                OperationStatus.REJECTED,
                error_code=ErrorCode.UNSUPPORTED_MESSAGE,
            )
        image_count = sum(
            isinstance(segment, ImageSegment) for segment in request.segments
        )
        if image_count > self._max_image_count:
            return SendMessageResult(
                operation_id,
                OperationStatus.REJECTED,
                error_code=ErrorCode.PLATFORM_REJECTED,
            )
        try:
            message = await self._build_message(request)
        except (UnsafeDownloadURLError, httpx.DecodingError, httpx.RequestError):
            return SendMessageResult(
                operation_id,
                OperationStatus.REJECTED,
                error_code=ErrorCode.PLATFORM_REJECTED,
            )

        return await self._execute_send(bot, target, message, operation_id)

    async def _execute_send(
        self,
        bot: Bot,
        target: tuple[str, int],
        message: Message,
        operation_id: str,
    ) -> SendMessageResult:
        try:
            response = await self._send(bot, target, message)
        except asyncio.CancelledError:
            await asyncio.shield(
                self._uncertainty_sink.record_uncertain(
                    operation_id,
                    ErrorCode.PLATFORM_FAILED,
                )
            )
            raise
        except ActionFailed:
            return SendMessageResult(
                operation_id,
                OperationStatus.REJECTED,
                error_code=ErrorCode.PLATFORM_REJECTED,
            )
        except (TimeoutError, NetworkError, httpx.NetworkError, httpx.ProtocolError):
            return await self._uncertain(operation_id)
        if not isinstance(response, dict):
            return await self._uncertain(operation_id)
        response_mapping = cast("dict[str, object]", response)
        message_id = response_mapping.get("message_id")
        if isinstance(message_id, bool) or not isinstance(message_id, (int, str)):
            return await self._uncertain(operation_id)
        return SendMessageResult(
            operation_id,
            OperationStatus.SUCCEEDED,
            str(message_id),
        )

    @staticmethod
    def _target(request: SendMessageRequest) -> tuple[str, int] | None:
        if request.conversation.conversation_type not in {"group", "private"}:
            return None
        try:
            identifier = int(request.conversation.conversation_id)
        except ValueError:
            return None
        if identifier <= 0:
            return None
        return request.conversation.conversation_type, identifier

    async def _build_message(self, request: SendMessageRequest) -> Message:
        segments: list[MessageSegment] = []
        total_image_bytes = 0
        for segment in request.segments:
            if isinstance(segment, TextSegment):
                segments.append(MessageSegment.text(segment.text))
            else:
                image_bytes = await self._fetch_image(
                    segment.url,
                    max_bytes=self._max_image_bytes,
                )
                total_image_bytes += len(image_bytes)
                if total_image_bytes > self._max_total_image_bytes:
                    raise UnsafeDownloadURLError
                segments.append(MessageSegment.image(image_bytes))
        return Message(segments)

    async def _uncertain(self, operation_id: str) -> SendMessageResult:
        await self._uncertainty_sink.record_uncertain(
            operation_id,
            ErrorCode.PLATFORM_FAILED,
        )
        return SendMessageResult(
            operation_id,
            OperationStatus.UNCERTAIN,
            error_code=ErrorCode.PLATFORM_FAILED,
        )

    @staticmethod
    async def _send(
        bot: Bot,
        target: tuple[str, int],
        message: Message,
    ) -> object:
        conversation_type, identifier = target
        if conversation_type == "group":
            result = await bot.send_group_msg(group_id=identifier, message=message)
        else:
            result = await bot.send_private_msg(user_id=identifier, message=message)
        return result
