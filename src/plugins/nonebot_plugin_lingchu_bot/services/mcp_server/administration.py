from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .contracts import (
    BotAddress,
    ContractError,
    ConversationAddress,
    ErrorCode,
)


def _require_exact(value: str, field_name: str) -> None:
    if not value or value.isspace() or value == "*":
        raise ContractError(
            ErrorCode.INVALID_IDENTIFIER,
            f"{field_name} must be an exact non-wildcard identifier",
        )


class OAuthIdentityKind(StrEnum):
    """Explicit OAuth identity claim namespace."""

    SUBJECT = "subject"
    CLIENT_ID = "client_id"


@dataclass(frozen=True, slots=True)
class CreateServicePrincipalRequest:
    """Create one stable OAuth identity mapping."""

    principal_id: str
    issuer: str
    identity_kind: OAuthIdentityKind
    identity_value: str
    display_name: str

    def __post_init__(self) -> None:
        _require_exact(self.principal_id, "principal_id")
        _require_exact(self.issuer, "issuer")
        if not isinstance(self.identity_kind, OAuthIdentityKind):
            raise ContractError(
                ErrorCode.INVALID_IDENTIFIER,
                "identity_kind must be subject or client_id",
            )
        _require_exact(self.identity_value, "identity_value")
        _require_exact(self.display_name, "display_name")


@dataclass(frozen=True, slots=True)
class CreateResourceGrantRequest:
    """Grant one principal access to one exact conversation."""

    grant_id: str
    principal_id: str
    bot: BotAddress
    conversation: ConversationAddress

    def __post_init__(self) -> None:
        _require_exact(self.grant_id, "grant_id")
        _require_exact(self.principal_id, "principal_id")
        for field_name in ("platform_id", "adapter_id", "protocol_id", "bot_id"):
            _require_exact(getattr(self.bot, field_name), field_name)
        _require_exact(self.conversation.conversation_type, "conversation_type")
        _require_exact(self.conversation.conversation_id, "conversation_id")
