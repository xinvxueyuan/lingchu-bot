from __future__ import annotations

import asyncio
import inspect

import pytest


def test_installed_litellm_exposes_required_native_async_operations() -> None:
    litellm = pytest.importorskip("litellm")

    for name in (
        "acompletion",
        "aresponses",
        "aembedding",
        "aimage_generation",
        "aimage_edit",
        "aimage_variation",
        "aspeech",
        "atranscription",
        "amoderation",
        "arerank",
        "acreate_file",
        "afile_content",
    ):
        operation = getattr(litellm, name)
        assert callable(operation), name
        assert inspect.iscoroutinefunction(operation), name


def test_real_router_exposes_instance_bound_async_operations() -> None:
    litellm = pytest.importorskip("litellm")
    router = litellm.Router(
        model_list=[
            {
                "model_name": "sdk-contract-sentinel",
                "litellm_params": {
                    "model": "openai/gpt-4o-mini",
                    "api_key": "sdk-contract-placeholder",
                },
            }
        ]
    )

    for name in (
        "acompletion",
        "aresponses",
        "aembedding",
        "aimage_generation",
        "aspeech",
        "atranscription",
        "amoderation",
        "arerank",
    ):
        operation = getattr(router, name)
        assert operation is not None, name
        assert callable(operation), name
        assert inspect.iscoroutinefunction(operation), name
    assert getattr(router, "close", None) is None
    assert getattr(router, "aclose", None) is None


def test_installed_openai_client_exposes_required_native_resources() -> None:
    openai = pytest.importorskip("openai")
    client = openai.AsyncOpenAI(api_key="sdk-contract-placeholder")

    for name in (
        "responses",
        "chat",
        "embeddings",
        "images",
        "audio",
        "moderations",
        "files",
        "uploads",
        "batches",
        "vector_stores",
        "containers",
        "conversations",
        "realtime",
        "fine_tuning",
        "evals",
    ):
        assert getattr(client, name) is not None, name

    asyncio.run(client.close())
