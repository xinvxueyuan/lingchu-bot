from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.novelai_image import config


def test_novelai_config_defaults() -> None:
    value = config.NovelAIConfig()

    assert value.model == "nai-diffusion-4-5-full"
    assert (value.width, value.height, value.steps, value.scale) == (832, 1216, 28, 5)
    assert {
        key: getattr(value, key)
        for key in config.NovelAIConfig.model_fields
        if key.startswith("tipo_")
    } == {
        "tipo_enabled": True,
        "tipo_base_url": "http://127.0.0.1:8081/v1",
        "tipo_model": "tipo-500m-ft",
        "tipo_api_key": None,
        "tipo_timeout": 30.0,
        "tipo_max_tokens": 512,
        "tipo_temperature": 0.5,
        "tipo_top_p": 0.95,
        "tipo_top_k": 40,
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"timeout": 0},
        {"width": 32},
        {"steps": 0},
        {"tipo_timeout": 0},
        {"tipo_max_tokens": 0},
        {"tipo_temperature": 2.1},
        {"tipo_top_p": -0.1},
        {"tipo_top_k": 0},
    ],
)
def test_novelai_config_rejects_invalid_values(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        config.NovelAIConfig.model_validate(kwargs)


def test_novelai_environment_overrides_json_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINGCHU_NOVELAI_WIDTH", "1024")
    monkeypatch.setenv("LINGCHU_NOVELAI_TOKEN", "env-token")
    monkeypatch.setenv("LINGCHU_NOVELAI_TIPO_BASE_URL", "https://tipo.test/v1")
    monkeypatch.setattr(config, "load_subplugin_config", lambda _: {})

    value = config.get_novelai_config()

    assert value.width == 1024
    assert value.token == "env-token"
    assert value.tipo_base_url == "https://tipo.test/v1"


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

    assert not any(key.startswith("prompt_llm_") for key in properties)
    assert not any(
        key.startswith("prompt_llm_") for key in config.novelai_config_defaults()
    )
    assert "tipo_model" in properties
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


def test_old_prompt_llm_keys_are_ignored() -> None:
    value = config.NovelAIConfig.model_validate(
        {
            "prompt_llm_provider": "openai",
            "prompt_llm_model": "legacy-model",
        }
    )

    assert not any(key.startswith("prompt_llm_") for key in value.model_fields_set)
