from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.llm import config as module
from src.plugins.nonebot_plugin_lingchu_bot.services.llm.config import (
    LLMRuntimeConfig,
    MCPConfig,
    ObservabilityConfig,
    PydanticAIConfig,
    ensure_llm_config_file_async,
    load_llm_runtime_config,
    resolve_profile,
)


async def test_missing_file_is_not_created_during_startup(tmp_path: Path) -> None:
    config_file = tmp_path / "llm.toml"
    with patch.object(module, "get_llm_config_file", return_value=config_file):
        path = await ensure_llm_config_file_async()

    assert path == config_file
    assert not config_file.exists()


def test_missing_pydantic_ai_section_raises_invalid_configuration(
    tmp_path: Path,
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text("[observability]\nenabled = true\n")

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


def test_missing_pydantic_ai_model_raises_invalid_configuration(
    tmp_path: Path,
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text('[pydantic-ai]\nbase_url = "http://localhost:3900"\n')

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


def test_missing_file_raises_invalid_configuration(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


def test_valid_pydantic_ai_config_loads_successfully(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[pydantic-ai]\nmodel = "openai:gpt-5.2"\ntimeout = 30.0\n'
        'api_key_env = "LINGCHU_AI_API_KEY"\n'
    )

    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()

    assert isinstance(config, LLMRuntimeConfig)
    assert config.pydantic_ai.model == "openai:gpt-5.2"
    assert config.pydantic_ai.timeout == 30.0
    assert config.pydantic_ai.api_key_env == "LINGCHU_AI_API_KEY"


def test_pydantic_ai_config_defaults_timeout_and_api_key_env(
    tmp_path: Path,
) -> None:
    path = tmp_path / "llm.toml"
    path.write_text('[pydantic-ai]\nmodel = "openai:gpt-5.2"\n')

    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()

    assert config.pydantic_ai.timeout == 60.0
    assert config.pydantic_ai.api_key_env is None


def test_mcp_config_loads_with_defaults(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[pydantic-ai]\nmodel = "openai:gpt-5.2"\n'
        '[mcp]\nenabled = true\nreview_profile = "reviewer"\nmax_tool_rounds = 3\n'
    )

    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()

    assert config.mcp.enabled is True
    assert config.mcp.review_profile == "reviewer"
    assert config.mcp.max_tool_rounds == 3


def test_mcp_config_defaults_when_section_absent(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text('[pydantic-ai]\nmodel = "openai:gpt-5.2"\n')

    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()

    assert config.mcp.enabled is False
    assert config.mcp.review_profile == "default"
    assert config.mcp.max_tool_rounds == 5


@pytest.mark.parametrize("rounds", [0, 6])
def test_mcp_max_tool_rounds_out_of_range_rejected(tmp_path: Path, rounds: int) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[pydantic-ai]\nmodel = "openai:gpt-5.2"\n'
        f"[mcp]\nenabled = true\nmax_tool_rounds = {rounds}\n"
    )

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


def test_observability_config_loads(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[pydantic-ai]\nmodel = "openai:gpt-5.2"\n[observability]\nenabled = false\n'
    )

    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()

    assert config.observability.enabled is False


def test_observability_defaults_to_enabled(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text('[pydantic-ai]\nmodel = "openai:gpt-5.2"\n')

    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()

    assert config.observability.enabled is True


def test_profiles_section_logs_deprecation_warning(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[pydantic-ai]\nmodel = "openai:gpt-5.2"\n'
        '[profiles.default]\nmodel = "gpt-4o"\n'
    )

    with (
        patch.object(module, "logger") as mock_logger,
        patch.object(module, "get_llm_config_file", return_value=path),
    ):
        config = load_llm_runtime_config()

    assert config.pydantic_ai.model == "openai:gpt-5.2"
    mock_logger.warning.assert_called_once()
    assert (
        "profiles/router sections are deprecated"
        in mock_logger.warning.call_args.args[0]
    )


def test_router_section_logs_deprecation_warning(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[pydantic-ai]\nmodel = "openai:gpt-5.2"\n[router]\nenabled = true\n'
    )

    with (
        patch.object(module, "logger") as mock_logger,
        patch.object(module, "get_llm_config_file", return_value=path),
    ):
        config = load_llm_runtime_config()

    assert config.pydantic_ai.model == "openai:gpt-5.2"
    mock_logger.warning.assert_called_once()
    assert (
        "profiles/router sections are deprecated"
        in mock_logger.warning.call_args.args[0]
    )


def test_eve_section_logs_deprecation_warning(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[pydantic-ai]\nmodel = "openai:gpt-5.2"\n'
        '[eve]\nbase_url = "http://localhost:3900"\n'
    )

    with (
        patch.object(module, "logger") as mock_logger,
        patch.object(module, "get_llm_config_file", return_value=path),
    ):
        config = load_llm_runtime_config()

    assert config.pydantic_ai.model == "openai:gpt-5.2"
    mock_logger.warning.assert_called_once()
    assert "[eve] section is deprecated" in mock_logger.warning.call_args.args[0]


def test_no_deprecation_warning_when_profiles_router_absent(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text('[pydantic-ai]\nmodel = "openai:gpt-5.2"\n')

    with (
        patch.object(module, "logger") as mock_logger,
        patch.object(module, "get_llm_config_file", return_value=path),
    ):
        load_llm_runtime_config()

    mock_logger.warning.assert_not_called()


def test_invalid_api_key_env_pattern_rejected(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[pydantic-ai]\nmodel = "openai:gpt-5.2"\napi_key_env = "BAD-NAME"\n'
    )

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


def test_invalid_timeout_rejected(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text('[pydantic-ai]\nmodel = "openai:gpt-5.2"\ntimeout = -1.0\n')

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


def test_pydantic_ai_section_rejects_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text('[pydantic-ai]\nmodel = "openai:gpt-5.2"\nunknown_field = true\n')

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
    ):
        load_llm_runtime_config()


def test_mcp_section_rejects_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text(
        '[pydantic-ai]\nmodel = "openai:gpt-5.2"\n[mcp]\nunknown_field = true\n'
    )

    with (
        patch.object(module, "get_llm_config_file", return_value=path),
        pytest.raises(ValueError, match="invalid LLM configuration"),
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


def test_resolve_profile_is_deprecated_noop(tmp_path: Path) -> None:
    path = tmp_path / "llm.toml"
    path.write_text('[pydantic-ai]\nmodel = "openai:gpt-5.2"\n')

    with patch.object(module, "get_llm_config_file", return_value=path):
        config = load_llm_runtime_config()

    assert resolve_profile(config) is None
    assert resolve_profile(config, name="any") is None


def test_llm_runtime_config_uses_defaults_for_optional_fields() -> None:
    pydantic_ai = PydanticAIConfig(model="openai:gpt-5.2")
    config = LLMRuntimeConfig(pydantic_ai=pydantic_ai)

    assert isinstance(config.mcp, MCPConfig)
    assert isinstance(config.observability, ObservabilityConfig)
    assert config.mcp.enabled is False
    assert config.observability.enabled is True


def test_ensure_llm_config_file_async_uses_direct_filesystem_io() -> None:
    source = inspect.getsource(ensure_llm_config_file_async)
    assert "aiofiles" not in source
    assert "asyncio.to_thread" not in source


async def test_ensure_llm_config_file_async_creates_parent_directory(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "nested" / "deep" / "llm.toml"
    assert not config_file.parent.exists()

    with patch.object(module, "get_llm_config_file", return_value=config_file):
        path = await ensure_llm_config_file_async()

    assert path == config_file
    assert config_file.parent.exists()
    assert not config_file.exists()
