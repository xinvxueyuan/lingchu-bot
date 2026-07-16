from __future__ import annotations

import inspect
from pathlib import Path
from types import MappingProxyType
from typing import cast
from unittest.mock import patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.runtime_config import RuntimeConfig
from src.plugins.nonebot_plugin_lingchu_bot.services.llm import config as module
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    LiteLLMRouterConfig,
    LLMObservabilityConfig,
    LLMProfileConfig,
    LLMRuntimeConfig,
    ensure_llm_config_file_async,
    load_llm_runtime_config,
    resolve_profile,
)


@pytest.mark.parametrize(
    "payload",
    ["bad\x00text", "bad\x7ftext", "bad\x80text", "bad\u2028text", "bad\u202etext"],
)
def test_json_extensions_reject_unicode_control_and_bidi(payload: str) -> None:
    with pytest.raises(ValueError, match="invalid LLM mapping"):
        module._json_value({"key": payload})


@pytest.fixture
def legacy() -> RuntimeConfig:
    return RuntimeConfig(ai_model="legacy-model", ai_api_key="legacy-key")


async def test_missing_file_creates_minimal_template(tmp_path: Path) -> None:
    with patch.object(
        module, "get_llm_config_file", return_value=tmp_path / "llm.toml"
    ):
        path = await ensure_llm_config_file_async()
    assert path.read_text() == 'default_profile = "default"\n[profiles]\n'


def test_empty_profiles_uses_legacy(legacy: RuntimeConfig, tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text("[profiles]\n")
    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config(legacy=legacy)
    resolved = resolve_profile(config, legacy=legacy)
    assert resolved.model == "legacy-model"
    assert resolved.api_key == "legacy-key"


def test_explicit_profile_without_api_key_env_does_not_inherit_legacy_key(
    legacy: RuntimeConfig, tmp_path: Path
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text('[profiles.main]\nmodel = "new"\n')
    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config(legacy=legacy)

    assert resolve_profile(config, legacy=legacy, name="main").api_key is None


def test_explicit_custom_url_opt_in_does_not_inherit_legacy_key(
    legacy: RuntimeConfig, tmp_path: Path
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[profiles.main]\nmodel = "new"\nbase_url = "https://custom.example/v1"\n'
        "allow_credentials_to_custom_base_url = true\n"
    )
    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config(legacy=legacy)

    assert resolve_profile(config, legacy=legacy, name="main").api_key is None


def test_explicit_profile_and_unknown_field(
    legacy: RuntimeConfig, tmp_path: Path
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[profiles.main]\nmodel = "new"\napi_key_env = "LLM_KEY"\nextra = true\n'
    )
    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config(legacy=legacy)


def test_api_key_env_resolves_only_at_runtime(
    legacy: RuntimeConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text('[profiles.main]\nmodel = "new"\napi_key_env = "LLM_KEY"\n')
    monkeypatch.setenv("LLM_KEY", "secret")
    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config(legacy=legacy)
    assert "secret" not in repr(config)
    assert resolve_profile(config, legacy=legacy, name="main").api_key == "secret"


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com",
        "https://user:pass@example.com",
        "http://127.0.0.1",
        "https://example.com/\u202e",
    ],
)
def test_hostile_urls_rejected(legacy: RuntimeConfig, tmp_path: Path, url: str) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(f'[profiles.main]\nmodel = "new"\nbase_url = "{url}"\n')
    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError),
    ):
        load_llm_runtime_config(legacy=legacy)


def test_existing_invalid_file_is_not_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text("not = [valid")
    before = path.read_text()
    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError),
    ):
        load_llm_runtime_config(legacy=RuntimeConfig())
    assert path.read_text() == before


def test_missing_or_empty_api_key_environment_is_rejected(
    legacy: RuntimeConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text('[profiles.main]\nmodel = "new"\napi_key_env = "LLM_KEY"\n')
    monkeypatch.setenv("LLM_KEY", "")
    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config(legacy=legacy)
        with pytest.raises(ValueError, match="API key"):
            resolve_profile(config, legacy=legacy, name="main")


@pytest.mark.parametrize(
    "field, value",
    [("litellm_generation", "invalid"), ("default_headers", '{"X\\u0000": "v"}')],
)
def test_profile_security_fields_are_validated(
    legacy: RuntimeConfig, tmp_path: Path, field: str, value: str
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(f'[profiles.main]\nmodel = "new"\n{field} = {value}\n')
    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config(legacy=legacy)


@pytest.mark.parametrize("section", ["router", "observability"])
def test_router_and_observability_reject_unknown_fields(
    legacy: RuntimeConfig, tmp_path: Path, section: str
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(f"[{section}]\nunknown = true\n")
    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config(legacy=legacy)


def test_custom_base_url_requires_explicit_credential_opt_in(
    legacy: RuntimeConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[profiles.main]\nmodel = "new"\nbase_url = "https://custom.example/v1/"\n'
        'api_key_env = "LLM_KEY"\n'
    )
    monkeypatch.setenv("LLM_KEY", "secret")
    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config(legacy=legacy)
        assert resolve_profile(config, legacy=legacy, name="main").api_key is None
    path.write_text(
        '[profiles.main]\nmodel = "new"\nbase_url = "https://custom.example/v1"\n'
        'api_key_env = "LLM_KEY"\nallow_credentials_to_custom_base_url = true\n'
    )
    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config(legacy=legacy)
        assert resolve_profile(config, legacy=legacy, name="main").api_key == "secret"


def test_explicit_profile_matching_legacy_url_still_requires_credential_opt_in(
    legacy: RuntimeConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    legacy = legacy.model_copy(update={"ai_base_url": "https://custom.example/v1"})
    path = tmp_path / "llm.toml"
    path.write_text(
        '[profiles.main]\nmodel = "new"\nbase_url = "https://custom.example/v1/"\n'
        'api_key_env = "LLM_KEY"\n'
    )
    monkeypatch.setenv("LLM_KEY", "secret")

    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config(legacy=legacy)

    assert resolve_profile(config, legacy=legacy, name="main").api_key is None


def test_runtime_config_copies_and_freezes_profile_mapping() -> None:
    profile = LLMProfileConfig(name="main", backend="openai", model="gpt")
    source = {"main": profile}
    config = LLMRuntimeConfig(
        default_profile="main",
        profiles=source,
        router=LiteLLMRouterConfig(),
        observability=LLMObservabilityConfig(),
    )

    source["other"] = profile

    assert isinstance(config.profiles, MappingProxyType)
    assert tuple(config.profiles) == ("main",)
    mutable_view = cast("dict[str, LLMProfileConfig]", config.profiles)
    with pytest.raises(TypeError):
        mutable_view["other"] = profile


@pytest.mark.parametrize(
    "content",
    [
        '[profiles.""]\nmodel = "gpt"\n',
        '[profiles.main]\nmodel = ""\n',
        '[profiles.main]\nmodel = "   "\n',
        '[profiles.main]\nmodel = "gpt"\napi_key_env = "BAD-NAME"\n',
        '[profiles.main]\nmodel = "gpt"\napi_key_env = "BAD\\u0000NAME"\n',
    ],
)
def test_profile_identity_and_environment_names_are_strict(
    legacy: RuntimeConfig, tmp_path: Path, content: str
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(content)

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM"),
    ):
        load_llm_runtime_config(legacy=legacy)


@pytest.mark.parametrize(
    "option",
    [
        'api_key = "secret"',
        'api_base = "https://evil.example"',
        'nested = { callbacks = ["capture"] }',
        "nested = { retry_config = { attempts = 9 } }",
    ],
)
def test_provider_options_reject_managed_control_plane_keys(
    legacy: RuntimeConfig, tmp_path: Path, option: str
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        f'[profiles.main]\nmodel = "gpt"\n[profiles.main.provider_options]\n{option}\n'
    )

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM"),
    ):
        load_llm_runtime_config(legacy=legacy)


@pytest.mark.parametrize(
    "extra",
    [
        '[profiles.main.default_headers]\nAuthorization = "Bearer secret"\n',
        '[profiles.main.default_query]\napi_key = "secret"\n',
        '[profiles.main.default_query]\nsafe = { api_key = "secret" }\n',
    ],
)
def test_custom_url_rejects_credential_headers_and_query_without_opt_in(
    legacy: RuntimeConfig, tmp_path: Path, extra: str
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[profiles.main]\nmodel = "gpt"\nbase_url = "https://custom.example/v1"\n'
        + extra
    )
    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config(legacy=legacy)
        with pytest.raises(ValueError, match="invalid LLM profile"):
            resolve_profile(config, legacy=legacy)


def test_implicit_legacy_profile_treats_existing_url_and_key_as_legacy_opt_in(
    tmp_path: Path,
) -> None:
    legacy = RuntimeConfig(
        ai_model="legacy",
        ai_base_url="https://legacy.example/v1",
        ai_api_key="legacy-key",
    )
    path = tmp_path / "llm.toml"
    path.write_text("[profiles]\n")

    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config(legacy=legacy)
        resolved = resolve_profile(config, legacy=legacy)

    assert resolved.api_key == "legacy-key"


async def test_ensure_llm_config_file_async_uses_aiofiles_not_to_thread() -> None:
    source = inspect.getsource(ensure_llm_config_file_async)
    assert "asyncio.to_thread" not in source
    assert "aiofiles" in source
