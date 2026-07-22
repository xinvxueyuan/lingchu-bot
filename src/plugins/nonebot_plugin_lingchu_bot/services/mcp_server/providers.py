"""Platform-provider resolution for inbound MCP messaging."""

from __future__ import annotations

from typing import Protocol

from .contracts import BotAddress, ContractError, ErrorCode


class PlatformProvider(Protocol):
    """Describe the exact platform addresses implemented by one provider."""

    @property
    def platform_id(self) -> str: ...

    @property
    def adapter_id(self) -> str: ...

    @property
    def protocol_ids(self) -> frozenset[str]: ...


type ProviderKey = tuple[str, str, str]


class ProviderConflictError(ValueError):
    """Reject two providers claiming the same exact platform address."""

    def __init__(self, key: ProviderKey) -> None:
        super().__init__(f"provider already registered for {key!r}")


class ProviderDefinitionError(ValueError):
    """Reject an invalid provider declaration before mutating the registry."""

    def __init__(self) -> None:
        super().__init__("provider protocol ids must be non-blank strings")


class ProviderRegistry:
    """Resolve providers by platform, adapter, and protocol without fallback."""

    def __init__(self, providers: tuple[PlatformProvider, ...] = ()) -> None:
        self._providers: dict[ProviderKey, PlatformProvider] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: PlatformProvider) -> None:
        """Register every protocol explicitly declared by ``provider``."""
        protocol_ids = tuple(provider.protocol_ids)
        if not protocol_ids or any(
            not protocol_id.strip() for protocol_id in protocol_ids
        ):
            raise ProviderDefinitionError
        keys = tuple(
            (provider.platform_id, provider.adapter_id, protocol_id)
            for protocol_id in protocol_ids
        )
        for key in keys:
            if key in self._providers:
                raise ProviderConflictError(key)
        self._providers.update(dict.fromkeys(keys, provider))

    def resolve(self, address: BotAddress) -> PlatformProvider:
        """Resolve only the exact provider named by ``address``."""
        key = (address.platform_id, address.adapter_id, address.protocol_id)
        provider = self._providers.get(key)
        if provider is None:
            raise ContractError(
                ErrorCode.UNSUPPORTED_PLATFORM,
                "no platform provider supports the requested bot address",
            )
        return provider
