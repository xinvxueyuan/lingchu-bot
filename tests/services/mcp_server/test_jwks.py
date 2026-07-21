from __future__ import annotations

from unittest.mock import MagicMock, patch

import jwt
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.auth import (
    SignedTokenVerificationError,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.jwks import (
    PyJWTJWKSDecoder,
)


@pytest.mark.asyncio
async def test_decoder_uses_fixed_algorithms_and_disables_duplicate_policy() -> None:
    signing_key = MagicMock()
    signing_key.key = object()
    client = MagicMock()
    client.get_signing_key_from_jwt.return_value = signing_key

    with (
        patch.object(jwt, "PyJWKClient", return_value=client),
        patch.object(jwt, "decode", return_value={"sub": "worker"}) as decode,
    ):
        claims = await PyJWTJWKSDecoder(
            "https://issuer.example/jwks.json", algorithms=("RS256",)
        ).decode_and_verify("token")

    assert claims == {"sub": "worker"}
    assert decode.call_args.kwargs["algorithms"] == ["RS256"]
    assert decode.call_args.kwargs["options"]["verify_exp"] is False


@pytest.mark.asyncio
async def test_decoder_hides_jwt_failures() -> None:
    with (
        patch.object(
            jwt.PyJWKClient,
            "get_signing_key_from_jwt",
            side_effect=jwt.InvalidTokenError("secret token details"),
        ),
        pytest.raises(SignedTokenVerificationError) as caught,
    ):
        await PyJWTJWKSDecoder("https://issuer.example/jwks.json").decode_and_verify(
            "token"
        )

    assert str(caught.value) == ""
