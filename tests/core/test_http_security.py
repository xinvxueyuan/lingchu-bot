from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import http_security
from src.plugins.nonebot_plugin_lingchu_bot.core.http_security import (
    UnsafeDownloadURLError,
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
