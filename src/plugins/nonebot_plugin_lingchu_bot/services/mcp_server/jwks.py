"""Fixed-algorithm JWKS signature verification for inbound OAuth tokens."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Final

from .auth import SignedTokenVerificationError

if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_JWT_ALGORITHMS: Final = ("RS256", "ES256")


class PyJWTJWKSDecoder:
    """Verify JWT signatures against one configured JWKS endpoint."""

    def __init__(
        self,
        jwks_url: str,
        *,
        algorithms: Sequence[str] = DEFAULT_JWT_ALGORITHMS,
    ) -> None:
        if not jwks_url.startswith("https://") or not algorithms:
            raise ValueError
        self._jwks_url = jwks_url
        self._algorithms = tuple(algorithms)

    async def decode_and_verify(self, token: str) -> dict[str, Any]:
        """Return verified claims or a transport-neutral verification error."""
        try:
            return await asyncio.to_thread(self._decode, token)
        except SignedTokenVerificationError:
            raise
        except (OSError, RuntimeError, ValueError):
            raise SignedTokenVerificationError from None

    def _decode(self, token: str) -> dict[str, Any]:
        import jwt

        try:
            client = jwt.PyJWKClient(self._jwks_url)
            key = client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=list(self._algorithms),
                options={
                    "verify_aud": False,
                    "verify_exp": False,
                    "verify_iat": False,
                    "verify_iss": False,
                    "verify_jti": False,
                    "verify_nbf": False,
                    "verify_sub": False,
                },
            )
        except jwt.PyJWTError:
            raise SignedTokenVerificationError from None
        if not isinstance(claims, dict):
            raise SignedTokenVerificationError
        return claims


__all__ = ["DEFAULT_JWT_ALGORITHMS", "PyJWTJWKSDecoder"]
