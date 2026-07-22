import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services import llm


def test_llm_public_facade_lazy_loads_export() -> None:
    value = llm.__getattr__("LLMUsage")

    assert value is llm.LLMUsage


def test_llm_public_facade_rejects_unknown_export() -> None:
    with pytest.raises(AttributeError, match="old_compat_export"):
        llm.__getattr__("old_compat_export")
