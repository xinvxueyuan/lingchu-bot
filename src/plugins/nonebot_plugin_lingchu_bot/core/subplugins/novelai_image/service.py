"""High-level NovelAI service construction for subplugin and Python consumers."""

from __future__ import annotations

from .auth import NovelAICredentials
from .client import MissingNovelAITokenError, NovelAIClient
from .config import NovelAIConfig, get_novelai_config


def create_novelai_client(config: NovelAIConfig | None = None) -> NovelAIClient:
    """Create a complete client from child-owned configuration."""
    selected = config or get_novelai_config()
    if not selected.token and not (selected.username and selected.password):
        raise MissingNovelAITokenError("NovelAI credentials are not configured")
    return NovelAIClient(
        NovelAICredentials(
            token=selected.token,
            username=selected.username,
            password=selected.password,
        ),
        image_base_url=selected.base_url,
        account_base_url=selected.account_base_url,
        timeout=selected.timeout,
        vibe_cache_entries=selected.vibe_cache_entries,
    )


__all__ = ["create_novelai_client"]
