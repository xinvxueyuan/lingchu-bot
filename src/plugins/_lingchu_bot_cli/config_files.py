"""Pure file operations for Lingchu runtime settings and their JSON Schema."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from _lingchu_bot_contracts import (
    MutableRuntimeSettings,
)
from pydantic import ValidationError
import rtoml

if TYPE_CHECKING:
    from pathlib import Path

CONFIG_FILENAME = "runtime-overrides.toml"
CONFIG_SCHEMA_FILENAME = "runtime-overrides.schema.json"
LLM_CONFIG_FILENAME = "llm.toml"
_SCHEMA_DIRECTIVE = "#:schema ./runtime-overrides.schema.json\n"
_LLM_TEMPLATE = (
    'default_profile = "default"\n'
    "\n"
    "# Uncomment and edit the profile below to enable AI features.\n"
    "# See: lingchu config init (with LINGCHU_AI_* env vars for auto-seeding)\n"
    "# [profiles.default]\n"
    '# backend = "litellm"\n'
    '# model = "gpt-4o"\n'
    '# api_key_env = "OPENAI_API_KEY"\n'
    "# timeout = 60.0\n"
)


class ConfigFileError(RuntimeError):
    """Report an expected configuration file failure to CLI callers."""


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def initialize_config(path: Path, *, force: bool = False) -> bool:
    """Create validated runtime defaults and return whether a file was written."""
    if path.exists() and not force:
        return False
    defaults = {
        key: value
        for key, value in MutableRuntimeSettings().model_dump(mode="json").items()
        if value is not None
    }
    _atomic_write(path, _SCHEMA_DIRECTIVE + rtoml.dumps(defaults))
    return True


def _seed_llm_profile_from_env() -> str | None:
    """Build a loadable ``llm.toml`` from ``LINGCHU_AI_*`` environment variables.

    Seeds a single ``[profiles.default]`` section when ``LINGCHU_AI_MODEL`` is
    present and non-empty. Other ``LINGCHU_AI_*`` variables are optional and
    mapped as follows:

    - ``LINGCHU_AI_PROVIDER``: ``openai`` → ``backend = "openai"``; any other
      value → ``backend = "litellm"``. Omitted when absent.
    - ``LINGCHU_AI_MODEL``: written verbatim as ``model`` (required for seeding).
    - ``LINGCHU_AI_BASE_URL``: written verbatim as ``base_url``.
    - ``LINGCHU_AI_API_KEY``: writes the env var *name*
      ``"LINGCHU_AI_API_KEY"`` to ``api_key_env`` (never the secret value).
    - ``LINGCHU_AI_TIMEOUT``: parsed as float and written to ``timeout`` when
      positive; ignored on parse failure.

    Returns:
        The full TOML document text including the ``default_profile`` header
        and ``[profiles.default]`` section, or ``None`` when seeding is not
        possible (``LINGCHU_AI_MODEL`` missing or empty).
    """
    model = os.environ.get("LINGCHU_AI_MODEL", "").strip()
    if not model:
        return None

    profile: dict[str, Any] = {}

    provider = os.environ.get("LINGCHU_AI_PROVIDER", "").strip()
    if provider:
        profile["backend"] = "openai" if provider == "openai" else "litellm"

    profile["model"] = model

    base_url = os.environ.get("LINGCHU_AI_BASE_URL", "").strip()
    if base_url:
        profile["base_url"] = base_url

    if os.environ.get("LINGCHU_AI_API_KEY", "").strip():
        profile["api_key_env"] = "LINGCHU_AI_API_KEY"

    timeout_raw = os.environ.get("LINGCHU_AI_TIMEOUT", "").strip()
    if timeout_raw:
        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = 0.0
        if timeout > 0:
            profile["timeout"] = timeout

    root: dict[str, Any] = {
        "default_profile": "default",
        "profiles": {"default": profile},
    }
    result = rtoml.dumps(root)
    return result if result.endswith("\n") else f"{result}\n"


def initialize_llm_config(path: Path) -> bool:
    """Create the default LLM profile template without overwriting any file.

    When ``LINGCHU_AI_*`` environment variables are present (and
    ``LINGCHU_AI_MODEL`` is non-empty), the file is seeded with a loadable
    ``[profiles.default]`` section derived from those variables. Otherwise a
    commented example template is written so the user can edit it manually.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    content = _seed_llm_profile_from_env() or _LLM_TEMPLATE
    try:
        with path.open("x", encoding="utf-8") as file:
            file.write(content)
    except FileExistsError:
        return False
    return True


def _load_raw_config(
    path: Path,
    *,
    allowed_fields: frozenset[str] = frozenset(MutableRuntimeSettings.model_fields),
) -> dict[str, object]:
    if not path.is_file():
        raise ConfigFileError(f"missing configuration file: {path}")
    try:
        raw = rtoml.load(path)
    except (OSError, rtoml.TomlParsingError) as exc:
        raise ConfigFileError(f"invalid configuration file {path}: {exc}") from exc
    unknown = sorted(set(raw) - allowed_fields)
    if unknown:
        raise ConfigFileError(f"unknown configuration fields: {', '.join(unknown)}")
    return raw


def validate_config(path: Path) -> MutableRuntimeSettings:
    """Validate one on-disk TOML file without environment overrides or writes."""
    raw = _load_raw_config(path)
    try:
        return MutableRuntimeSettings.model_validate(raw)
    except ValidationError as exc:
        raise ConfigFileError(f"invalid configuration file {path}: {exc}") from exc


def install_config_schema(config_dir: Path) -> Path:
    """Install the JSON Schema generated by the shared runtime settings model."""
    target = config_dir / CONFIG_SCHEMA_FILENAME
    content = json.dumps(
        MutableRuntimeSettings.model_json_schema(mode="serialization"),
        ensure_ascii=False,
        indent=2,
    )
    _atomic_write(target, f"{content}\n")
    return target
