"""Project-owned outbound message Action for inbound MCP requests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

if TYPE_CHECKING:
    from .bot_directory import BotDirectory
    from .contracts import SendMessageRequest, SendMessageResult
    from .providers import ProviderRegistry


class _SendProvider(Protocol):
    async def send_message(
        self,
        bot: object,
        request: SendMessageRequest,
    ) -> SendMessageResult: ...


class SendMessageAction:
    """Resolve exact platform resources before delegating one atomic send."""

    def __init__(self, providers: ProviderRegistry, bots: BotDirectory) -> None:
        self._providers = providers
        self._bots = bots

    async def send_message(self, request: SendMessageRequest) -> SendMessageResult:
        """Send through the exact provider and connected bot in ``request``."""
        provider = cast("_SendProvider", self._providers.resolve(request.bot))
        bot = self._bots.resolve(request.bot)
        return await provider.send_message(bot, request)
