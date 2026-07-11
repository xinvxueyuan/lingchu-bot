from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image import config


def test_novelai_config_defaults() -> None:
    value = config.NovelAIConfig()

    assert value.model == "nai-diffusion-4-5-full"
    assert (value.width, value.height, value.steps, value.scale) == (832, 1216, 28, 5)
    assert value.prompt_llm_provider is None


def test_prompt_llm_options_fall_back_per_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        config,
        "resolve_default_llm_options",
        lambda: config.LLMOptions(
            provider="litellm",
            model="parent-model",
            base_url="https://parent.test/v1",
            api_key="parent-key",
            timeout=60.0,
        ),
    )
    value = config.NovelAIConfig(
        prompt_llm_provider="openai",
        prompt_llm_model=None,
        prompt_llm_base_url="https://child.test/v1",
        prompt_llm_api_key=None,
        prompt_llm_timeout=9.0,
    )

    assert config.resolve_prompt_llm_options(value) == config.LLMOptions(
        provider="openai",
        model="parent-model",
        base_url="https://child.test/v1",
        api_key="parent-key",
        timeout=9.0,
    )


@pytest.mark.parametrize(
    "kwargs",
    [{"timeout": 0}, {"width": 32}, {"steps": 0}, {"prompt_llm_timeout": -1}],
)
def test_novelai_config_rejects_invalid_values(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        config.NovelAIConfig.model_validate(kwargs)


def test_novelai_environment_overrides_json_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINGCHU_NOVELAI_WIDTH", "1024")
    monkeypatch.setenv("LINGCHU_NOVELAI_TOKEN", "env-token")
    monkeypatch.setattr(config, "load_subplugin_config", lambda _: {})

    value = config.get_novelai_config()

    assert value.width == 1024
    assert value.token == "env-token"


def test_novelai_config_reads_nonebot_dotenv_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LINGCHU_NOVELAI_TOKEN", raising=False)
    monkeypatch.setattr(config, "load_subplugin_config", lambda _: {})
    monkeypatch.setattr(
        config,
        "get_driver",
        lambda: SimpleNamespace(
            config=SimpleNamespace(
                lingchu_novelai_token="dotenv-token",
                lingchu_novelai_width=1024,
            )
        ),
    )

    value = config.get_novelai_config()

    assert value.token == "dotenv-token"
    assert value.width == 1024


def test_schema_contains_child_fields_only() -> None:
    schema = config.novelai_config_schema()
    properties = schema["properties"]

    assert "prompt_llm_model" in properties
    assert "token" in properties
    assert "ai_model" not in properties

    def contains_null_type(value: object) -> bool:
        if isinstance(value, dict):
            return value.get("type") == "null" or any(
                contains_null_type(item) for item in value.values()
            )
        if isinstance(value, list):
            return any(contains_null_type(item) for item in value)
        return False

    assert contains_null_type(schema) is False
