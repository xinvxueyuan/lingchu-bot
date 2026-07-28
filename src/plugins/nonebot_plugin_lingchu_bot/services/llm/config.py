"""Strict localstore-backed configuration for the LLM service.

The Python bot uses the in-process Pydantic AI agent to drive LLM calls.
Configuration lives in ``llm.toml`` under the ``[pydantic-ai]`` section.
Legacy ``[profiles]``, ``[router]``, and ``[eve]`` sections are ignored
with a deprecation warning so operators can migrate incrementally.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import tomllib
from typing import TYPE_CHECKING, Literal

from nonebot import logger, require
from nonebot_plugin_localstore import get_plugin_config_file
from pydantic import BaseModel, ConfigDict, Field, ValidationError

require("nonebot_plugin_localstore")

if TYPE_CHECKING:
    from pathlib import Path

LLM_CONFIG_FILENAME = "llm.toml"


class _LLMConfigError(ValueError):
    """Raised when the local LLM configuration is invalid."""


INVALID_MAPPING = _LLMConfigError("invalid LLM mapping")
INVALID_HEADERS = _LLMConfigError("invalid headers")
INVALID_CONFIGURATION = _LLMConfigError("invalid LLM configuration")


class PydanticAIConfig(BaseModel):
    """Configuration for the in-process Pydantic AI agent."""

    model_config = ConfigDict(extra="forbid")
    model: str = Field(..., pattern=r"^[\w.-]+:[\w./-]+$")
    api_key_env: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    base_url: str | None = None
    timeout: float = Field(default=60.0, gt=0)


class MCPServerDef(BaseModel):
    """One MCP server definition consumed by the Pydantic AI MCPToolset."""

    model_config = ConfigDict(extra="forbid")
    transport: Literal["stdio", "streamable_http"]
    command: str | None = None
    args: tuple[str, ...] = ()
    url: str | None = None
    headers_env: str | None = None
    allow_private_network: bool = False


class MCPConfig(BaseModel):
    """MCP Agent runtime toggles consumed by the Pydantic AI MCP capability."""

    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    review_profile: str = "default"
    max_tool_rounds: int = Field(default=5, ge=1, le=5)
    servers: dict[str, MCPServerDef] = Field(default_factory=dict)


class ObservabilityConfig(BaseModel):
    """Safe allowlisted stable-call logging."""

    model_config = ConfigDict(extra="forbid")
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class LLMRuntimeConfig:
    """Runtime LLM configuration backed by the Pydantic AI agent."""

    pydantic_ai: PydanticAIConfig
    mcp: MCPConfig = field(default_factory=MCPConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)


def get_llm_config_file() -> Path:
    return get_plugin_config_file(LLM_CONFIG_FILENAME)


async def ensure_llm_config_file_async() -> Path:
    """Return the localstore-owned ``llm.toml`` path without creating the file.

    Only the parent directory is ensured so callers can resolve the path
    before the file exists; the configuration file itself is never written
    at startup. When ``llm.toml`` is missing, ``load_llm_runtime_config()``
    falls through to an empty mapping and raises ``INVALID_CONFIGURATION``.
    """
    path = get_llm_config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_llm_runtime_config() -> LLMRuntimeConfig:
    """Load and validate the Pydantic AI LLM configuration from ``llm.toml``.

    Reads the ``[pydantic-ai]`` section for the in-process Pydantic AI agent,
    the ``[mcp]`` section for MCP Agent runtime toggles (including the
    ``[mcp.servers]`` subtable consumed by the Pydantic AI MCPToolset), and
    the ``[observability]`` section for structured call logging. Deprecated
    ``[profiles]``, ``[router]``, and ``[eve]`` sections are ignored with a
    WARNING.

    Raises:
        _LLMConfigError: When the file is unreadable, the TOML is invalid,
            a section fails pydantic validation, or ``[pydantic-ai] model``
            is missing or empty.
    """
    # Sync I/O: startup-time API called once before the event loop is in use.
    path = get_llm_config_file()
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, tomllib.TOMLDecodeError):
        raise INVALID_CONFIGURATION from None

    if "profiles" in raw or "router" in raw:
        logger.warning(
            "profiles/router sections are deprecated, use [pydantic-ai] "
            "section to configure Pydantic AI agent"
        )

    if "eve" in raw:
        logger.warning(
            "[eve] section is deprecated, use [pydantic-ai] section to "
            "configure Pydantic AI agent"
        )

    try:
        pydantic_ai = PydanticAIConfig.model_validate(raw.get("pydantic-ai", {}))
        mcp_config = MCPConfig.model_validate(raw.get("mcp", {}))
        observability = ObservabilityConfig.model_validate(raw.get("observability", {}))
    except ValidationError:
        raise INVALID_CONFIGURATION from None

    if not pydantic_ai.model:
        raise INVALID_CONFIGURATION

    return LLMRuntimeConfig(
        pydantic_ai=pydantic_ai, mcp=mcp_config, observability=observability
    )


def resolve_profile(config: LLMRuntimeConfig, *, name: str | None = None) -> None:
    """Deprecated: LLM profile resolution moved to the Pydantic AI agent.

    Retained as a no-op so ``services/llm/runtime.py`` can continue to import
    it during the migration. It will be removed once ``runtime.py`` is updated.

    Args:
        config: Unused; kept for signature compatibility.
        name: Unused; kept for signature compatibility.
    """
    _ = (config, name)
