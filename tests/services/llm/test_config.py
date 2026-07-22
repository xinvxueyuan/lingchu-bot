from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from types import MappingProxyType
from typing import cast
from unittest.mock import patch

import pytest

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


def test_missing_file_creates_minimal_template(tmp_path: Path) -> None:
    with patch.object(
        module, "get_llm_config_file", return_value=tmp_path / "llm.toml"
    ):
        path = asyncio.run(ensure_llm_config_file_async())
    assert path.read_text() == 'default_profile = "default"\n[profiles]\n'


def test_empty_profiles_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text("[profiles]\n")
    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


def test_mcp_configuration_loads_named_servers(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        'default_profile = "default"\n'
        '[profiles.default]\nmodel = "gpt"\n'
        '[mcp]\nenabled = true\nreview_profile = "default"\n'
        '[[mcp.servers]]\nname = "local-tools"\ntransport = "stdio"\n'
        'command = "uvx"\nargs = ["example-server"]\n'
        '[[mcp.servers]]\nname = "remote_docs"\n'
        'transport = "streamable_http"\nurl = "https://mcp.example/rpc"\n'
        'headers_env = "MCP_HEADERS"\n'
    )

    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()

    assert config.mcp.enabled is True
    assert config.mcp.review_profile == "default"
    assert [server.name for server in config.mcp.servers] == [
        "local-tools",
        "remote_docs",
    ]
    assert config.mcp.servers[0].args == ("example-server",)
    assert config.mcp.servers[1].headers_env == "MCP_HEADERS"


@pytest.mark.parametrize(
    "server_config",
    [
        'name = "local"\ntransport = "stdio"\n',
        'name = "local"\ntransport = "stdio"\ncommand = "uvx"\n'
        'url = "https://mcp.example/rpc"\n',
        'name = "remote"\ntransport = "streamable_http"\n',
        'name = "remote"\ntransport = "streamable_http"\n'
        'url = "http://127.0.0.1/rpc"\n',
        'name = "remote"\ntransport = "streamable_http"\n'
        'url = "https://mcp.example/rpc"\ncommand = "bad"\n',
        'name = "Dotted.Name"\ntransport = "stdio"\ncommand = "uvx"\n',
    ],
)
def test_mcp_server_transport_configuration_is_strict(
    tmp_path: Path, server_config: str
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[profiles.default]\nmodel = "gpt"\n'
        '[mcp]\nenabled = true\nreview_profile = "default"\n'
        "[[mcp.servers]]\n" + server_config
    )

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


def test_mcp_server_names_are_unique(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[profiles.default]\nmodel = "gpt"\n'
        '[mcp]\nenabled = true\nreview_profile = "default"\n'
        '[[mcp.servers]]\nname = "same"\ntransport = "stdio"\ncommand = "one"\n'
        '[[mcp.servers]]\nname = "same"\ntransport = "stdio"\ncommand = "two"\n'
    )

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


def test_mcp_server_name_length_is_bounded(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[profiles.default]\nmodel = "gpt"\n'
        '[mcp]\nenabled = true\nreview_profile = "default"\n'
        f'[[mcp.servers]]\nname = "{"s" * 65}"\n'
        'transport = "stdio"\ncommand = "server"\n'
    )

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


def test_mcp_defaults_are_bounded(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[profiles.reviewer]\nmodel = "gpt"\n'
        '[mcp]\nenabled = true\nreview_profile = "reviewer"\n'
    )

    with patch.object(module, "get_llm_config_file", return_value=path):
        mcp = load_llm_runtime_config().mcp

    assert mcp.max_tool_rounds == 5
    assert mcp.max_parallel_tools == 4
    assert mcp.tool_timeout == 15.0
    assert mcp.result_limit_bytes == 65536
    assert mcp.request_timeout == 90.0


@pytest.mark.parametrize(
    "setting",
    ["max_tool_rounds = 6", "max_parallel_tools = 5"],
)
def test_mcp_hard_limits_cannot_be_raised(tmp_path: Path, setting: str) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[profiles.reviewer]\nmodel = "gpt"\n'
        '[mcp]\nenabled = true\nreview_profile = "reviewer"\n'
        f"{setting}\n"
    )

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


@pytest.mark.parametrize("review_profile", [None, "missing"])
def test_enabled_mcp_requires_existing_review_profile(
    tmp_path: Path,
    review_profile: str | None,
) -> None:
    path = tmp_path / "llm.toml"
    review_line = (
        f'review_profile = "{review_profile}"\n' if review_profile is not None else ""
    )
    path.write_text(
        '[profiles.default]\nmodel = "gpt"\n[mcp]\nenabled = true\n' + review_line
    )

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


def test_explicit_profile_without_api_key_env_does_not_inherit_legacy_key(
    tmp_path: Path,
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text('[profiles.main]\nmodel = "new"\n')
    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()

    assert resolve_profile(config, name="main").api_key is None


def test_explicit_custom_url_opt_in_does_not_inherit_legacy_key(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[profiles.main]\nmodel = "new"\nbase_url = "https://custom.example/v1"\n'
        "allow_credentials_to_custom_base_url = true\n"
    )
    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()

    assert resolve_profile(config, name="main").api_key is None


def test_explicit_profile_and_unknown_field(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[profiles.main]\nmodel = "new"\napi_key_env = "LLM_KEY"\nextra = true\n'
    )
    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


def test_api_key_env_resolves_only_at_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text('[profiles.main]\nmodel = "new"\napi_key_env = "LLM_KEY"\n')
    monkeypatch.setenv("LLM_KEY", "secret")
    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()
    assert "secret" not in repr(config)
    assert resolve_profile(config, name="main").api_key == "secret"


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com",
        "https://user:pass@example.com",
        "http://127.0.0.1",
        "https://example.com/\u202e",
    ],
)
def test_hostile_urls_rejected(tmp_path: Path, url: str) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(f'[profiles.main]\nmodel = "new"\nbase_url = "{url}"\n')
    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError),
    ):
        load_llm_runtime_config()


def test_existing_invalid_file_is_not_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text("not = [valid")
    before = path.read_text()
    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError),
    ):
        load_llm_runtime_config()
    assert path.read_text() == before


def test_missing_or_empty_api_key_environment_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text('[profiles.main]\nmodel = "new"\napi_key_env = "LLM_KEY"\n')
    monkeypatch.setenv("LLM_KEY", "")
    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()
        with pytest.raises(ValueError, match="API key"):
            resolve_profile(config, name="main")


@pytest.mark.parametrize(
    "field, value",
    [("litellm_generation", "invalid"), ("default_headers", '{"X\\u0000": "v"}')],
)
def test_profile_security_fields_are_validated(
    tmp_path: Path, field: str, value: str
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(f'[profiles.main]\nmodel = "new"\n{field} = {value}\n')
    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


@pytest.mark.parametrize("section", ["router", "observability"])
def test_router_and_observability_reject_unknown_fields(
    tmp_path: Path, section: str
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(f"[{section}]\nunknown = true\n")
    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


def test_custom_base_url_requires_explicit_credential_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[profiles.main]\nmodel = "new"\nbase_url = "https://custom.example/v1/"\n'
        'api_key_env = "LLM_KEY"\n'
    )
    monkeypatch.setenv("LLM_KEY", "secret")
    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()
        assert resolve_profile(config, name="main").api_key is None
    path.write_text(
        '[profiles.main]\nmodel = "new"\nbase_url = "https://custom.example/v1"\n'
        'api_key_env = "LLM_KEY"\nallow_credentials_to_custom_base_url = true\n'
    )
    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()
        assert resolve_profile(config, name="main").api_key == "secret"


def test_explicit_profile_matching_custom_url_still_requires_credential_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[profiles.main]\nmodel = "new"\nbase_url = "https://custom.example/v1/"\n'
        'api_key_env = "LLM_KEY"\n'
    )
    monkeypatch.setenv("LLM_KEY", "secret")

    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()

    assert resolve_profile(config, name="main").api_key is None


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
    tmp_path: Path, content: str
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(content)

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM"),
    ):
        load_llm_runtime_config()


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
    tmp_path: Path, option: str
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        f'[profiles.main]\nmodel = "gpt"\n[profiles.main.provider_options]\n{option}\n'
    )

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM"),
    ):
        load_llm_runtime_config()


@pytest.mark.parametrize(
    "extra",
    [
        '[profiles.main.default_headers]\nAuthorization = "Bearer secret"\n',
        '[profiles.main.default_query]\napi_key = "secret"\n',
        '[profiles.main.default_query]\nsafe = { api_key = "secret" }\n',
    ],
)
def test_custom_url_rejects_credential_headers_and_query_without_opt_in(
    tmp_path: Path, extra: str
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[profiles.main]\nmodel = "gpt"\nbase_url = "https://custom.example/v1"\n'
        + extra
    )
    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()
        with pytest.raises(ValueError, match="invalid LLM profile"):
            resolve_profile(config)


def test_empty_config_has_no_implicit_default_profile(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text("[profiles]\n")

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (None, None),
        ("", None),
        ("HTTPS://Example.TEST:443/v1/", "https://example.test/v1"),
        ("http://Example.TEST:80/api//", "http://example.test/api"),
        ("https://Example.TEST:8443/v1/", "https://example.test:8443/v1"),
    ],
)
def test_normalize_url_canonicalizes_optional_base_url(
    url: str | None, expected: str | None
) -> None:
    assert module._normalize_url(url) == expected


def test_ensure_llm_config_file_async_uses_direct_filesystem_io() -> None:
    source = inspect.getsource(ensure_llm_config_file_async)
    assert "aiofiles" not in source
    assert "asyncio.to_thread" not in source
