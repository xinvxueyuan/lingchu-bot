"""Strict localstore-backed configuration for the LLM service."""

from __future__ import annotations

from dataclasses import dataclass, field
import ipaddress
import os
import tomllib
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal, Self, cast
from urllib.parse import urlparse

from nonebot import require
from nonebot_plugin_localstore import get_plugin_config_file
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from .security import (
    contains_control_plane_key,
    contains_sensitive_mapping_entry,
    freeze_value,
)
from .types import LLMBackendName, LLMProfile

if TYPE_CHECKING:
    from collections.abc import Mapping

require("nonebot_plugin_localstore")

if TYPE_CHECKING:
    from pathlib import Path

LLM_CONFIG_FILENAME = "llm.toml"
MAX_JSON_DEPTH = 8
MAX_MAPPING_ITEMS = 100
CONTROL_CHAR_MIN = 32
CONTROL_CHAR_MAX = 127
CONTROL_CHAR_C1_MAX = 0x9F
LINE_SEPARATOR = 0x2028
PARAGRAPH_SEPARATOR = 0x2029
BIDI_OVERRIDE_START = 0x202A
BIDI_OVERRIDE_END = 0x202E
BIDI_ISOLATE_START = 0x2066
BIDI_ISOLATE_END = 0x2069
HTTP_PORT = 80
HTTPS_PORT = 443
MAX_MCP_SERVER_NAME_LENGTH = 64


class _LLMConfigError(ValueError):
    """Raised when the local LLM configuration is invalid."""


INVALID_MAPPING = _LLMConfigError("invalid LLM mapping")
INVALID_HEADERS = _LLMConfigError("invalid headers")
INVALID_BASE_URL = _LLMConfigError("invalid base_url")
PRIVATE_BASE_URL = _LLMConfigError("private base_url is not allowed")
MISSING_API_KEY = _LLMConfigError("configured API key environment variable is missing")
MISSING_DEFAULT_PROFILE = _LLMConfigError("default_profile does not exist")
INVALID_PROFILE = _LLMConfigError("invalid LLM profile")
INVALID_CONFIGURATION = _LLMConfigError("invalid LLM configuration")


def _safe_text(value: str) -> str:
    """Reject control, separator, and bidi override characters in config text."""
    if any(
        ord(char) < CONTROL_CHAR_MIN
        or CONTROL_CHAR_MAX <= ord(char) <= CONTROL_CHAR_C1_MAX
        or ord(char) in {LINE_SEPARATOR, PARAGRAPH_SEPARATOR}
        or BIDI_OVERRIDE_START <= ord(char) <= BIDI_OVERRIDE_END
        or BIDI_ISOLATE_START <= ord(char) <= BIDI_ISOLATE_END
        for char in value
    ):
        raise INVALID_MAPPING
    return value


def _json_value(value: object, depth: int = 0) -> object:
    if depth > MAX_JSON_DEPTH or isinstance(value, (bytes, bytearray, set)):
        raise INVALID_MAPPING
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        return _safe_text(value)
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        if len(value) > MAX_MAPPING_ITEMS:
            raise INVALID_MAPPING
        return {
            _safe_text(cast("str", k)): _json_value(v, depth + 1)
            for k, v in value.items()
        }
    if isinstance(value, list):
        if len(value) > MAX_MAPPING_ITEMS:
            raise INVALID_MAPPING
        return [_json_value(v, depth + 1) for v in value]
    raise INVALID_MAPPING


class _ProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    backend: str = "litellm"
    model: str = Field(min_length=1)
    base_url: str | None = None
    api_key_env: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    organization: str | None = None
    project: str | None = None
    timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=2, ge=0, le=20)
    default_headers: dict[str, str] = Field(default_factory=dict)
    default_query: dict[str, object] = Field(default_factory=dict)
    provider_options: dict[str, Any] = Field(default_factory=dict)
    litellm_generation: str = "responses"
    allow_private_network: bool = False
    allow_credentials_to_custom_base_url: bool = False

    @field_validator("default_query")
    @classmethod
    def validate_mapping(cls, value: dict[str, object]) -> dict[str, object]:
        validated = _json_value(value)
        if not isinstance(validated, dict):
            raise INVALID_MAPPING
        validated_dict = cast("dict[str, object]", validated)
        return dict(validated_dict)

    @field_validator("provider_options")
    @classmethod
    def validate_provider_options(cls, value: dict[str, object]) -> dict[str, object]:
        validated = cls.validate_mapping(value)
        if contains_control_plane_key(validated):
            raise INVALID_MAPPING
        return validated

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        if not value.strip():
            raise INVALID_PROFILE
        return _safe_text(value)

    @field_validator("default_headers")
    @classmethod
    def validate_headers(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > MAX_MAPPING_ITEMS or any(
            any(ord(c) < CONTROL_CHAR_MIN or ord(c) == CONTROL_CHAR_MAX for c in k + v)
            for k, v in value.items()
        ):
            raise INVALID_HEADERS
        return value


class _RouterModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    strategy: str | None = None
    num_retries: int = Field(default=0, ge=0, le=20)
    timeout: float | None = Field(default=None, gt=0)
    extensions: dict[str, Any] = Field(default_factory=dict)


class _ObservabilityModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True


class _MCPServerModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(
        max_length=MAX_MCP_SERVER_NAME_LENGTH,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    )
    transport: Literal["stdio", "streamable_http"]
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    headers_env: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    allow_private_network: bool = False

    @model_validator(mode="after")
    def validate_transport(self) -> Self:
        if self.transport == "stdio":
            if not self.command or self.url or self.headers_env:
                raise INVALID_CONFIGURATION
            _safe_text(self.command)
            for arg in self.args:
                _safe_text(arg)
        elif self.command or self.args or not self.url:
            raise INVALID_CONFIGURATION
        else:
            _check_url(self.url, allow_private=self.allow_private_network)
        return self


class _MCPModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    review_profile: str | None = None
    servers: list[_MCPServerModel] = Field(default_factory=list)
    max_tool_rounds: int = Field(default=5, ge=1, le=5)
    max_parallel_tools: int = Field(default=4, ge=1, le=4)
    tool_timeout: float = Field(default=15.0, gt=0, le=300)
    result_limit_bytes: int = Field(default=65536, ge=1024, le=1048576)
    request_timeout: float = Field(default=90.0, gt=0, le=900)


class _RootModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_profile: str | None = None
    profiles: dict[str, _ProfileModel] = Field(default_factory=dict)
    router: _RouterModel = Field(default_factory=_RouterModel)
    observability: _ObservabilityModel = Field(default_factory=_ObservabilityModel)
    mcp: _MCPModel = Field(default_factory=_MCPModel)

    @model_validator(mode="after")
    def validate_mcp(self) -> Self:
        server_names = [server.name for server in self.mcp.servers]
        if len(server_names) != len(set(server_names)):
            raise INVALID_CONFIGURATION
        return self


@dataclass(frozen=True, slots=True)
class LLMProfileConfig:
    name: str
    backend: LLMBackendName
    model: str
    base_url: str | None = None
    api_key_env: str | None = None
    organization: str | None = None
    project: str | None = None
    timeout: float = 60.0
    max_retries: int = 2
    default_headers: Mapping[str, str] = field(default_factory=dict)
    default_query: Mapping[str, object] = field(default_factory=dict)
    provider_options: Mapping[str, Any] = field(default_factory=dict)
    litellm_generation: Literal["responses", "chat"] = "responses"
    allow_private_network: bool = False
    allow_credentials_to_custom_base_url: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "default_headers", freeze_value(self.default_headers))
        object.__setattr__(self, "default_query", freeze_value(self.default_query))
        object.__setattr__(
            self, "provider_options", freeze_value(self.provider_options)
        )


@dataclass(frozen=True, slots=True)
class LiteLLMRouterConfig:
    values: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", freeze_value(self.values))


@dataclass(frozen=True, slots=True)
class LLMObservabilityConfig:
    values: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", freeze_value(self.values))


@dataclass(frozen=True, slots=True)
class MCPServerConfig:
    name: str
    transport: Literal["stdio", "streamable_http"]
    command: str | None = None
    args: tuple[str, ...] = ()
    url: str | None = None
    headers_env: str | None = None
    allow_private_network: bool = False


@dataclass(frozen=True, slots=True)
class MCPRuntimeConfig:
    enabled: bool = False
    review_profile: str | None = None
    servers: tuple[MCPServerConfig, ...] = ()
    max_tool_rounds: int = 5
    max_parallel_tools: int = 4
    tool_timeout: float = 15.0
    result_limit_bytes: int = 65536
    request_timeout: float = 90.0


@dataclass(frozen=True, slots=True)
class LLMRuntimeConfig:
    default_profile: str
    profiles: Mapping[str, LLMProfileConfig]
    router: LiteLLMRouterConfig
    observability: LLMObservabilityConfig
    mcp: MCPRuntimeConfig = field(default_factory=MCPRuntimeConfig)

    def __post_init__(self) -> None:
        object.__setattr__(self, "profiles", MappingProxyType(dict(self.profiles)))


def get_llm_config_file() -> Path:
    return get_plugin_config_file(LLM_CONFIG_FILENAME)


async def ensure_llm_config_file_async() -> Path:
    return get_llm_config_file()


def _check_url(url: str | None, *, allow_private: bool) -> None:
    if not url:
        return
    try:
        _safe_text(url)
    except _LLMConfigError:
        raise INVALID_BASE_URL from None
    parsed = urlparse(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise INVALID_BASE_URL
    host = parsed.hostname.casefold()
    try:
        addr = ipaddress.ip_address(host)
        private = addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        private = host in {
            "localhost",
            "metadata.google.internal",
            "metadata.google.internal.",
        } or host.endswith(".localhost")
    if private and not allow_private:
        raise PRIVATE_BASE_URL
    # Deliberately do not perform blocking DNS here.  The downstream HTTP
    # client/network policy must revalidate resolved addresses and redirects
    # against SSRF/private-network policy at connection time.


def _normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold()
    port = parsed.port
    default = (parsed.scheme == "http" and port == HTTP_PORT) or (
        parsed.scheme == "https" and port == HTTPS_PORT
    )
    netloc = host if not port or default else f"{host}:{port}"
    return f"{parsed.scheme.casefold()}://{netloc}{parsed.path.rstrip('/')}"


def load_llm_runtime_config() -> LLMRuntimeConfig:
    # Sync I/O: startup-time API called once before the event loop is in use.
    path = get_llm_config_file()
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        root = _RootModel.model_validate(raw)
    except (OSError, tomllib.TOMLDecodeError, ValidationError, ValueError):
        raise INVALID_CONFIGURATION from None
    source = root.profiles
    if not source:
        raise INVALID_CONFIGURATION
    default = root.default_profile or next(iter(source))
    if default not in source:
        raise MISSING_DEFAULT_PROFILE
    if root.mcp.enabled and root.mcp.review_profile not in source:
        raise INVALID_CONFIGURATION
    profiles: dict[str, LLMProfileConfig] = {}
    for name, p in source.items():
        if not name.strip():
            raise INVALID_PROFILE
        _safe_text(name)
        if p.backend not in {"litellm", "openai"} or p.litellm_generation not in {
            "responses",
            "chat",
        }:
            raise INVALID_PROFILE
        _check_url(p.base_url, allow_private=p.allow_private_network)
        values = p.model_dump()
        profiles[name] = LLMProfileConfig(
            name=name,
            backend=cast("LLMBackendName", values.pop("backend")),
            litellm_generation=cast(
                "Literal['responses', 'chat']", values.pop("litellm_generation")
            ),
            **values,
        )
    return LLMRuntimeConfig(
        default,
        profiles,
        LiteLLMRouterConfig(root.router.model_dump()),
        LLMObservabilityConfig(root.observability.model_dump()),
        MCPRuntimeConfig(
            enabled=root.mcp.enabled,
            review_profile=root.mcp.review_profile,
            max_tool_rounds=root.mcp.max_tool_rounds,
            max_parallel_tools=root.mcp.max_parallel_tools,
            tool_timeout=root.mcp.tool_timeout,
            result_limit_bytes=root.mcp.result_limit_bytes,
            request_timeout=root.mcp.request_timeout,
            servers=tuple(
                MCPServerConfig(
                    **server.model_dump(exclude={"args"}), args=tuple(server.args)
                )
                for server in root.mcp.servers
            ),
        ),
    )


def resolve_profile(config: LLMRuntimeConfig, *, name: str | None = None) -> LLMProfile:
    profile = config.profiles[name or config.default_profile]
    key = os.environ.get(profile.api_key_env) if profile.api_key_env else None
    if profile.api_key_env and not key:
        raise MISSING_API_KEY
    if profile.base_url and not profile.allow_credentials_to_custom_base_url:
        if contains_sensitive_mapping_entry(profile.default_headers) or (
            contains_sensitive_mapping_entry(profile.default_query)
        ):
            raise INVALID_PROFILE
        key = None
    return LLMProfile(
        name=profile.name,
        backend=profile.backend,
        model=profile.model,
        base_url=profile.base_url,
        api_key=key,
        organization=profile.organization,
        project=profile.project,
        timeout=profile.timeout,
        max_retries=profile.max_retries,
        default_headers=profile.default_headers,
        default_query=profile.default_query,
        provider_options=profile.provider_options,
        litellm_generation=profile.litellm_generation,
        allow_private_network=profile.allow_private_network,
        allow_credentials_to_custom_base_url=profile.allow_credentials_to_custom_base_url,
    )
