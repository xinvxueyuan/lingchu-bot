from __future__ import annotations

import os

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm.backends import (
    LiteLLMBackend,
    OpenAIBackend,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    LiteLLMRouterConfig,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.types import LLMProfile

pytestmark = pytest.mark.llm_live


def _require_live_opt_in() -> None:
    if os.environ.get("LINGCHU_LLM_LIVE_TESTS") != "1":
        pytest.skip("set LINGCHU_LLM_LIVE_TESTS=1 to enable billed live calls")


def _require_credential(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"set {name} to run this live contract")
    return value


@pytest.mark.asyncio
async def test_live_openai_responses_contract() -> None:
    _require_live_opt_in()
    api_key = _require_credential("OPENAI_API_KEY")
    backend = OpenAIBackend(
        LLMProfile(
            name="live-openai",
            backend="openai",
            model=os.environ.get("LINGCHU_LLM_LIVE_OPENAI_MODEL", "gpt-4o-mini"),
            api_key=api_key,
        )
    )

    try:
        response = await backend.client.responses.create(
            model=backend.profile.model,
            input="Reply with one short word.",
            max_output_tokens=8,
        )
        assert response is not None
        assert response.id
    finally:
        await backend.close()


@pytest.mark.asyncio
async def test_live_litellm_responses_contract() -> None:
    _require_live_opt_in()
    api_key = _require_credential("LINGCHU_LLM_LIVE_LITELLM_API_KEY")
    backend = LiteLLMBackend(
        LLMProfile(
            name="live-litellm",
            backend="litellm",
            model=os.environ.get(
                "LINGCHU_LLM_LIVE_LITELLM_MODEL", "openai/gpt-4o-mini"
            ),
            api_key=api_key,
        ),
        LiteLLMRouterConfig(),
    )

    try:
        response = await backend.call(
            "aresponses",
            model=backend.profile.model,
            input="Reply with one short word.",
            max_output_tokens=8,
        )
        assert response is not None
    finally:
        await backend.close()
