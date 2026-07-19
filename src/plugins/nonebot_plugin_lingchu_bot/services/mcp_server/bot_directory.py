"""Exact connected-bot lookup for inbound MCP platform providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import (
    BotAddress,
    ConnectedBotSummary,
    ContractError,
    ErrorCode,
)


@dataclass(frozen=True, slots=True)
class _ConnectedBot:
    bot: object
    summary: ConnectedBotSummary


class BotAddressResolver(Protocol):
    """Derive a trusted platform-neutral address from a live bot object."""

    def __call__(self, bot: object, /) -> BotAddress: ...


class BotDirectory:
    """Track connected bots by their complete, platform-neutral address."""

    def __init__(self, resolve_address: BotAddressResolver) -> None:
        self._resolve_address = resolve_address
        self._connected: dict[BotAddress, _ConnectedBot] = {}

    def connect(
        self,
        address: BotAddress,
        bot: object,
        *,
        display_name: str,
    ) -> ConnectedBotSummary:
        """Register one connection under its exact address."""
        if self._resolve_address(bot) != address:
            raise ContractError(
                ErrorCode.INVALID_IDENTIFIER,
                "connected bot address does not match the claimed address",
            )
        summary = ConnectedBotSummary(
            address=address,
            display_name=display_name,
            connected=True,
        )
        self._connected[address] = _ConnectedBot(bot=bot, summary=summary)
        return summary

    def resolve(self, address: BotAddress) -> object:
        """Return the bot at ``address`` without falling back to another bot."""
        connected = self._connected.get(address)
        if connected is None:
            raise ContractError(ErrorCode.BOT_NOT_FOUND, "connected bot not found")
        return connected.bot

    def disconnect(self, address: BotAddress, bot: object) -> bool:
        """Remove ``bot`` only if it is still the active connection at ``address``."""
        connected = self._connected.get(address)
        if connected is None or connected.bot is not bot:
            return False
        del self._connected[address]
        return True
