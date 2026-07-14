# Full-Featured LLM Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` to execute this plan task by task.

**Goal:** Replace the thin text-only LLM service with a managed, non-lossy
LiteLLM/OpenAI runtime while preserving the current chat and NovelAI contracts.

**Architecture:** Convert `services/llm.py` into a lazy-imported package with
three access levels: stable Lingchu operations, typed backend handles, and
provider-native escape hatches. Profiles are loaded from localstore-owned
`llm.toml`; named profiles own cached clients, while compatibility calls use
short-lived ephemeral clients. Startup, reload, shutdown, redaction, SSRF
controls, streaming projection, capability probes, and error normalization are
owned by the runtime rather than by handlers.

**Current dependency baseline:** Python 3.13, Pydantic 2, NoneBot2,
nonebot-plugin-localstore, LiteLLM 1.92.0, OpenAI Python 2.45.0, pytest, Ruff,
Pyright, and ty.

## Execution Protocol

1. Work directly on `main`, as authorized by the user. Do not create a
   worktree or feature branch.
2. Use one fresh implementation subagent per task, followed by a fresh
   specification reviewer and a fresh code-quality/security reviewer. Fix all
   findings and repeat review before moving to the next task.
3. Execute tasks sequentially. Tasks share the same package and cannot safely
   be implemented in parallel.
4. Before editing any existing function, class, or method, run GitNexus
   upstream impact analysis and report its blast radius. Stop and warn before
   a HIGH or CRITICAL edit. `complete_chat` is already known to be HIGH risk.
5. For every task, follow red-green-refactor: add a failing test, run it and
   confirm the intended failure, make the smallest implementation, then rerun
   the targeted test and the task gates.
6. Do not commit, stage, push, or open a PR unless the user separately asks.
   Before any requested commit, run
   `detect_changes(scope="compare", base_ref="main")` and review all staged and
   unstaged diffs.
7. Preserve unrelated working-tree changes. At plan creation time Claude Code
   or the user had concurrent NovelAI and dependency-file edits; re-check the
   baseline before each task that touches an overlapping file.
8. The design and plan live under ignored `/docs`. Do not force-add them unless
   the user explicitly asks.

## Global Security And Product Invariants

- Stable `respond()` and `stream()` reject control-plane parameters including
  credentials, endpoint overrides, transports, callbacks, loggers, and retry
  clients. Trusted code that needs those features uses an explicit native
  handle.
- LiteLLM `call(operation)` accepts only a public, single-segment async callable
  name selected by trusted internal code. Reject empty names, leading
  underscores, dots, slashes, path syntax, non-callables, and synchronous
  callables without invoking them.
- `base_url` is operator-owned. Accept only HTTP(S), reject userinfo, fragments,
  control characters, link-local and metadata endpoints. Private and loopback
  networks require `allow_private_network = true`; credentials sent to a
  custom endpoint require `allow_credentials_to_custom_base_url = true`.
- Redaction is recursive and fail-closed for mappings, sequences, exception
  arguments, profile representations, provider options, headers, query values,
  malicious `repr()` implementations, and log-injection characters.
- No model output may automatically execute tools, MCP calls, URLs, files,
  paths, shell commands, or provider passthrough routes.
- Runtime state is `NEW`, `RUNNING`, `CLOSING`, or `CLOSED`. Close is
  cancellation-safe and idempotent, attempts every owned resource even after a
  failure, and forbids resource creation after closing begins.
- Reload validates a complete candidate before atomically swapping it in. An
  invalid reload leaves the old runtime active. Invalid first configuration
  disables LLM features but does not prevent non-AI bot startup.
- Missing optional dependencies disable only their backend. There is no
  implicit provider fallback and no provider-error fallback from Responses to
  Chat Completions.
- Router/profile inputs are deep-copied and frozen. Runtime code never mutates
  LiteLLM module globals and never calls `Router.reset()`.
- Configuration rejects unknown fields except documented extension mappings,
  bounds nesting and collection sizes, and validates headers and environment
  variable names.

## Task 1: Freeze Compatibility And Convert The Module To A Package

**Files:**

- Move: `src/plugins/nonebot_plugin_lingchu_bot/services/llm.py` to
  `src/plugins/nonebot_plugin_lingchu_bot/services/llm/compat.py`
- Create: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/__init__.py`
- Modify: `tests/services/test_llm.py`
- Modify: `pyproject.toml`

**Step 1: Establish the impact boundary**

Run GitNexus upstream impact for `complete_chat`, `complete_with_web_search`,
and `supports_web_search`. Record direct callers and affected flows. Because
`complete_chat` is HIGH risk, report that risk before editing and confirm that
the intended affected flows are LLM chat and NovelAI intent/search only.

**Step 2: Add import-contract tests**

Add tests that import every current public name from both
`nonebot_plugin_lingchu_bot.services.llm` and the subplugin contract surface.
Assert that importing the package does not import `openai` or `litellm`, read a
configuration file, or instantiate a client.

Run:

```bash
source ~/.zshrc
TMPDIR=/tmp uv run -m pytest -s tests/services/test_llm.py
```

Expected: the new package-import assertions fail before the move.

**Step 3: Perform the mechanical package conversion**

Use `git mv`, then create an inert package facade:

```python
from .compat import (
    ChatMessage,
    EmptyLLMContentError,
    LLMError,
    LLMOptions,
    LLMProviderError,
    MissingLLMContentError,
    WebSearchResult,
    complete_chat,
    complete_with_web_search,
    supports_web_search,
)

__all__ = [
    "ChatMessage",
    "EmptyLLMContentError",
    "LLMError",
    "LLMOptions",
    "LLMProviderError",
    "MissingLLMContentError",
    "WebSearchResult",
    "complete_chat",
    "complete_with_web_search",
    "supports_web_search",
]
```

Fix relative imports in `compat.py`. Update the Ruff per-file ignore from the
single old file to a justified package glob; do not add inline ignores.

**Step 4: Verify behavior is unchanged**

Run:

```bash
TMPDIR=/tmp uv run -m pytest -s \
  tests/services/test_llm.py \
  tests/core/subplugins/llm_chat \
  tests/core/subplugins/novelai_image/test_intent.py \
  tests/core/subplugins/novelai_image/test_search.py
uv run -m ruff check \
  src/plugins/nonebot_plugin_lingchu_bot/services/llm \
  tests/services/test_llm.py --output-format=github
```

Expected: all existing behavior and imports pass; neither SDK is imported at
package import time.

## Task 2: Add Project Types, Errors, Redaction, And Immutable Data

**Files:**

- Create: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/types.py`
- Create: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/errors.py`
- Create: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/security.py`
- Create: `tests/services/llm/test_types.py`
- Create: `tests/services/llm/test_errors.py`
- Create: `tests/services/llm/test_security.py`
- Modify: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/__init__.py`

**Step 1: Write failing contract and hostile-input tests**

Cover frozen/slotted `LLMProfile`, `LLMUsage`, `LLMResponse`, and `LLMEvent`;
error metadata; recursive freezing; safe thawing for SDK calls; and redaction of
keys matching token, key, authorization, secret, credential, cookie, password,
header, and query patterns. Include cyclic structures, deep nesting, malicious
`__repr__`, newline injection, exception arguments, and nested provider data.

Run:

```bash
TMPDIR=/tmp uv run -m pytest -s \
  tests/services/llm/test_types.py \
  tests/services/llm/test_errors.py \
  tests/services/llm/test_security.py
```

Expected: collection fails because the modules do not exist.

**Step 2: Implement the stable types and errors**

Define:

```python
type LLMBackendName = Literal["litellm", "openai"]
type CapabilitySupport = Literal["supported", "unsupported", "unknown"]

@dataclass(frozen=True, slots=True)
class LLMUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

@dataclass(frozen=True, slots=True)
class LLMResponse:
    text: str | None
    output: tuple[object, ...]
    usage: LLMUsage | None
    request_id: str | None
    model: str | None
    backend: LLMBackendName
    raw: object

class LLMError(RuntimeError):
    backend: LLMBackendName | None
    model: str | None
    request_id: str | None
    status_code: int | None
    retryable: bool
```

Keep the legacy exception names importable. Implement bounded recursive
freeze/thaw and redaction helpers without logging original hostile values.
Ensure dataclass `repr()` never reveals resolved API keys.

**Step 3: Verify**

Rerun the three tests, then:

```bash
uv run -m ruff check \
  src/plugins/nonebot_plugin_lingchu_bot/services/llm \
  tests/services/llm --output-format=github
uv run -m ruff format --check \
  src/plugins/nonebot_plugin_lingchu_bot/services/llm \
  tests/services/llm
```

Expected: all tests and static style checks pass.

## Task 3: Add Strict Localstore Configuration And Schema

**Files:**

- Create: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/config.py`
- Modify: `src/plugins/nonebot_plugin_lingchu_bot/core/schemas.py`
- Create: `tests/services/llm/test_config.py`
- Modify: `tests/core/test_schemas.py`

**Step 1: Run impact analysis**

Before modifying `install_schemas`, run its upstream impact and report startup
and test callers. Inspect the localstore patterns used by runtime configuration.

**Step 2: Write failing configuration tests**

Cover missing `llm.toml`, empty profiles, legacy implicit `default`, explicit
profile precedence, unknown fields, `api_key_env`, missing environment values,
invalid generation mode, invalid headers, excessive nesting/counts, hostile
URLs, credentials to custom URLs, private/link-local/metadata addresses,
malformed TOML, and an existing invalid file that must not be overwritten.

Use these public shapes:

```python
@dataclass(frozen=True, slots=True)
class LLMRuntimeConfig:
    default_profile: str
    profiles: Mapping[str, LLMProfileConfig]
    router: LiteLLMRouterConfig
    observability: LLMObservabilityConfig

def get_llm_config_file() -> Path: ...
async def ensure_llm_config_file_async() -> Path: ...
def load_llm_runtime_config(*, legacy: RuntimeConfig) -> LLMRuntimeConfig: ...
def resolve_profile(
    config: LLMRuntimeConfig,
    *,
    legacy: RuntimeConfig,
    name: str | None = None,
) -> LLMProfile: ...
```

`LLMProfileConfig` includes `backend`, `model`, `base_url`, `api_key_env`,
`organization`, `project`, `timeout`, `max_retries`, `default_headers`,
`default_query`, `provider_options`, `litellm_generation` (`responses` or
`chat`), `allow_private_network`, and
`allow_credentials_to_custom_base_url`.

Run:

```bash
TMPDIR=/tmp uv run -m pytest -s \
  tests/services/llm/test_config.py \
  tests/core/test_schemas.py
```

Expected: failures for missing config API and schema.

**Step 3: Implement configuration and schema installation**

Use `get_plugin_config_file("llm.toml")`; do not construct a mutable runtime
path with `Path`. Install `llm.schema.json` from an in-code
`LLM_SCHEMA_TEXT`. Models use `extra="forbid"`; only named extension mappings
accept provider-specific keys. Resolve `api_key_env` only into `LLMProfile`,
never into persisted configuration or diagnostics.

Precedence is call data > profile provider options > runtime-owned defaults,
but stable APIs reject call data for runtime-owned control-plane keys. An empty
profiles table produces a legacy implicit profile without rewriting the file.

**Step 4: Verify**

```bash
TMPDIR=/tmp uv run -m pytest -s \
  tests/services/llm/test_config.py \
  tests/core/test_schemas.py \
  tests/core/test_runtime_config_ai.py
uv run -m ruff check \
  src/plugins/nonebot_plugin_lingchu_bot/services/llm/config.py \
  src/plugins/nonebot_plugin_lingchu_bot/core/schemas.py \
  tests/services/llm/test_config.py tests/core/test_schemas.py \
  --output-format=github
```

Expected: schema and profile tests pass; no secret appears in failure output.

## Task 4: Implement The Managed OpenAI Backend

**Files:**

- Create: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/backends.py`
- Create: `tests/services/llm/test_openai_backend.py`

**Step 1: Write failing lifecycle and native-access tests**

Test lazy import, missing direct dependency, constructor arguments, one client
per named profile/generation, credential fingerprint rotation, `client`,
`with_options`, native resource access, native return identity, native exception
identity, idempotent close, concurrent acquisition, and rejection after close.
Distinguish a missing `openai` package from a transitive import error raised
inside an installed package.

Run:

```bash
TMPDIR=/tmp uv run -m pytest -s tests/services/llm/test_openai_backend.py
```

Expected: import failure for `OpenAIBackend`.

**Step 2: Implement the backend**

Expose:

```python
class OpenAIBackend:
    @property
    def client(self) -> AsyncOpenAI: ...

    def with_options(self, **options: object) -> AsyncOpenAI: ...

    async def close(self) -> None: ...
```

Construct `AsyncOpenAI` with the resolved `api_key`, `base_url`,
`organization`, `project`, `timeout`, `max_retries`, `default_headers`, and
`default_query`. `with_options()` delegates to the cached client and must not
create another HTTP client. Never normalize native exceptions in this layer.
Close every owned client once even if another close fails.

**Step 3: Verify**

```bash
TMPDIR=/tmp uv run -m pytest -s tests/services/llm/test_openai_backend.py
uv run -m ruff check \
  src/plugins/nonebot_plugin_lingchu_bot/services/llm/backends.py \
  tests/services/llm/test_openai_backend.py --output-format=github
```

Expected: backend tests and Ruff pass.

## Task 5: Implement LiteLLM Native Access And Router

**Files:**

- Modify: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/backends.py`
- Create: `tests/services/llm/test_litellm_backend.py`
- Create: `tests/services/llm/test_router.py`
- Create: `tests/services/llm/test_sdk_contract.py`

**Step 1: Write failing native-operation and Router tests**

Test `sdk`, lazy import, native return/exception identity, permitted public async
operations, and rejection of `_private`, `__dunder__`, dotted, slashed,
backslashed, missing, non-callable, and synchronous attributes before
invocation. Test parameter merge order and prove caller mappings are unchanged.

Instantiate a real 1.92.0 Router in a sentinel test and inspect instance-level
`aresponses` and `amoderation`, because those operations are dynamically bound
and may be `None` on the class. Assert Router config is copied, callbacks and
custom loggers are rejected, module globals are unchanged, and shutdown never
calls `Router.reset()`.

Run:

```bash
TMPDIR=/tmp uv run -m pytest -s \
  tests/services/llm/test_litellm_backend.py \
  tests/services/llm/test_router.py \
  tests/services/llm/test_sdk_contract.py
```

Expected: missing `LiteLLMBackend` failures.

**Step 2: Implement the backend**

Expose:

```python
class LiteLLMBackend:
    @property
    def sdk(self) -> ModuleType: ...

    @property
    def router(self) -> object | None: ...

    async def call(self, operation: str, /, **params: Any) -> Any: ...

    async def close(self) -> None: ...
```

Validate operation names with a single-segment public identifier rule and
`inspect.iscoroutinefunction`. Build `litellm.Router(**config)` only for an
enabled Router profile. Do not copy Router methods and do not mutate LiteLLM
globals. Since 1.92.0 has no owned Router close API and `reset()` mutates global
callbacks, shutdown only releases resources explicitly owned by this runtime.

**Step 3: Verify**

Rerun the three tests and:

```bash
uv run -m ruff check \
  src/plugins/nonebot_plugin_lingchu_bot/services/llm/backends.py \
  tests/services/llm/test_litellm_backend.py \
  tests/services/llm/test_router.py \
  tests/services/llm/test_sdk_contract.py --output-format=github
```

Expected: all native-surface and no-global-mutation assertions pass.

## Task 6: Implement Runtime State, Stable Responses, Errors, And Telemetry

**Files:**

- Create: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/runtime.py`
- Create: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/observability.py`
- Modify: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/__init__.py`
- Create: `tests/services/llm/test_runtime.py`
- Create: `tests/services/llm/test_responses.py`
- Create: `tests/services/llm/test_observability.py`
- Create: `tests/services/llm/test_lifecycle.py`

**Step 1: Write failing runtime tests**

Cover all four states, concurrent profile acquisition, one backend per named
profile/config generation, bounded ephemeral profiles, API-key rotation,
creation-vs-close races, cancellation during close, multiple close failures,
idempotent close, and no creation after `CLOSING`.

For `respond()`, cover OpenAI `responses.create`, LiteLLM `aresponses` when the
profile mode is `responses`, LiteLLM `acompletion` only when mode is `chat`, no
fallback on provider errors, parameter merge order, normalized output, raw
native object retention, usage/request ID/model extraction, error mapping, and
control-plane parameter rejection.

Telemetry tests assert only event name, backend, model alias, duration, token
counts, status, and request ID are emitted. Prompt, output, API key, URL query,
headers, exception body, and provider payload must never be logged.

Run:

```bash
TMPDIR=/tmp uv run -m pytest -s \
  tests/services/llm/test_runtime.py \
  tests/services/llm/test_responses.py \
  tests/services/llm/test_observability.py \
  tests/services/llm/test_lifecycle.py
```

Expected: missing runtime API failures.

**Step 2: Implement the runtime**

Expose:

```python
class LLMRuntime:
    def profile(self, name: str | None = None) -> LLMProfile: ...
    def litellm(self, name: str | None = None) -> LiteLLMBackend: ...
    def openai(self, name: str | None = None) -> OpenAIBackend: ...

    async def respond(
        self,
        input: object,
        *,
        profile: str | None = None,
        **params: object,
    ) -> LLMResponse: ...

    async def close(self) -> None: ...
```

Named caches use profile name plus configuration generation, never the profile
dataclass or a plaintext credential. A one-way credential fingerprint triggers
replacement and closure on environment-key rotation. Ephemeral compatibility
profiles are request-scoped and closed after use.

Reject at least `api_key`, `base_url`, `api_base`, `organization`, `project`,
`transport`, `http_client`, `client`, `callbacks`, `success_callback`,
`failure_callback`, `custom_logger`, `max_retries`, and retry-client overrides
from stable calls. Native handles retain the SDKs' full option surface.

**Step 3: Verify**

Rerun the four test modules, then:

```bash
uv run -m ruff check \
  src/plugins/nonebot_plugin_lingchu_bot/services/llm \
  tests/services/llm --output-format=github
uv run -m ruff format --check \
  src/plugins/nonebot_plugin_lingchu_bot/services/llm \
  tests/services/llm
```

Expected: runtime, normalization, security, and lifecycle tests pass.

## Task 7: Add Streaming Projection And Cancellation Safety

**Files:**

- Create: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/events.py`
- Modify: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/runtime.py`
- Modify: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/__init__.py`
- Create: `tests/services/llm/test_streaming.py`

**Step 1: Write failing event-projection tests**

Test `started`, text delta, tool-call delta, output item, usage, completed,
provider error, and unknown native event preservation. Verify the completed
event contains the assembled `LLMResponse`. Assert cancellation remains
`asyncio.CancelledError`, the underlying iterator/context is closed in
`finally`, and tool requests are emitted as data without execution.

Run:

```bash
TMPDIR=/tmp uv run -m pytest -s tests/services/llm/test_streaming.py
```

Expected: missing `stream()` and projection failures.

**Step 2: Implement the async iterator**

Add:

```python
def stream(
    self,
    input: object,
    *,
    profile: str | None = None,
    **params: object,
) -> AsyncIterator[LLMEvent]: ...
```

Use provider-specific adapters only to project common events. Preserve every
unrecognized event as `LLMEvent(type="native", raw=event)`. Do not catch or
wrap `CancelledError`; cleanup belongs in `finally` and must not hide the
original provider or cancellation exception.

**Step 3: Verify**

```bash
TMPDIR=/tmp uv run -m pytest -s tests/services/llm/test_streaming.py
uv run -m ruff check \
  src/plugins/nonebot_plugin_lingchu_bot/services/llm/events.py \
  src/plugins/nonebot_plugin_lingchu_bot/services/llm/runtime.py \
  tests/services/llm/test_streaming.py --output-format=github
```

Expected: all event, cleanup, and cancellation tests pass.

## Task 8: Add Advisory Capabilities And Migrate Compatibility Calls

**Files:**

- Create: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/capabilities.py`
- Modify: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/compat.py`
- Modify: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/__init__.py`
- Create: `tests/services/llm/test_capabilities.py`
- Modify: `tests/services/test_llm.py`
- Modify: `tests/core/subplugins/novelai_image/test_intent.py`
- Modify: `tests/core/subplugins/novelai_image/test_search.py`

**Step 1: Re-run impact analysis and add failing tests**

Re-run upstream impact for the three compatibility functions immediately before
editing them. Warn again about the HIGH-risk `complete_chat` boundary.

Capability tests cover `supported`, `unsupported`, and `unknown`; probe
exceptions map to `unknown`; operation existence does not imply model support;
cache keys contain no secret; and configuration reload invalidates the cache.

Compatibility tests lock these contracts:

- `complete_chat()` returns `str` and keeps native Chat Completions semantics:
  OpenAI uses `chat.completions.create`, LiteLLM uses `acompletion`.
- `LLMOptions` creates a request-scoped ephemeral profile and never expands the
  named-client cache.
- `supports_web_search()` projects `unknown` to `False`.
- `complete_with_web_search()` remains fail-open, deduplicates URLs, rejects
  hostile annotation shapes, and logs no prompt, secret, or provider body.

Run:

```bash
TMPDIR=/tmp uv run -m pytest -s \
  tests/services/llm/test_capabilities.py \
  tests/services/test_llm.py \
  tests/core/subplugins/novelai_image/test_intent.py \
  tests/core/subplugins/novelai_image/test_search.py
```

Expected: capability imports fail and compatibility delegation assertions fail.

**Step 2: Implement advisory probes and runtime delegation**

Define:

```python
@dataclass(frozen=True, slots=True)
class CapabilityResult:
    capability: str
    support: CapabilitySupport
    source: str
    reason: str | None = None
```

Capability results never block an explicitly requested native call. Replace
the old `_call_openai` and `_call_litellm` implementation with runtime-backed
operations while preserving public signatures and exception behavior. Update
tests to patch backend/client factories rather than re-exporting obsolete
private helpers.

**Step 3: Verify the HIGH-risk flows**

```bash
TMPDIR=/tmp uv run -m pytest -s \
  tests/services \
  tests/core/subplugins/llm_chat \
  tests/core/subplugins/novelai_image/test_intent.py \
  tests/core/subplugins/novelai_image/test_search.py
```

Expected: all legacy consumers and new runtime tests pass.

## Task 9: Add Atomic Initialization, Reload, Shutdown, And Subplugin Contract

**Files:**

- Modify: `src/plugins/nonebot_plugin_lingchu_bot/services/llm/runtime.py`
- Modify: `src/plugins/nonebot_plugin_lingchu_bot/start/startup.py`
- Modify: `src/plugins/nonebot_plugin_lingchu_bot/hooks/handlers/lifecycle.py`
- Modify: `src/plugins/nonebot_plugin_lingchu_bot/core/subplugins/contracts.py`
- Modify: `src/plugins/nonebot_plugin_lingchu_bot/core/subplugins/__init__.py`
- Modify: `tests/start/test_startup.py`
- Modify: `tests/hooks/handlers/test_lifecycle.py`
- Modify: `tests/core/subplugins/test_contracts.py`
- Modify: `tests/core/subplugins/test_import_boundary.py`
- Create: `tests/services/llm/test_reload.py`

**Step 1: Analyze each existing lifecycle symbol**

Run upstream impact before editing the startup hook, shutdown hook, contract
exports, or their existing functions. Report affected startup, shutdown, and
subplugin import flows.

**Step 2: Add failing lifecycle and reload tests**

Test lazy singleton access, concurrent initialize, valid atomic reload, invalid
reload preserving the old runtime, old-resource close after successful swap,
first invalid config leaving non-AI startup alive, backend-local missing
dependencies, and shutdown ordering. Make shutdown continue closing the LLM and
message store even if a previous service fails, while reporting the failures.

Lock this contract:

```python
def get_llm_runtime() -> LLMRuntime: ...
async def initialize_llm_runtime() -> LLMRuntime: ...
async def reload_llm_runtime() -> LLMRuntime: ...
async def shutdown_llm_runtime() -> None: ...

def get_subplugin_llm_runtime() -> LLMRuntime:
    return get_llm_runtime()
```

Run:

```bash
TMPDIR=/tmp uv run -m pytest -s \
  tests/services/llm/test_reload.py \
  tests/start/test_startup.py \
  tests/hooks/handlers/test_lifecycle.py \
  tests/core/subplugins/test_contracts.py \
  tests/core/subplugins/test_import_boundary.py
```

Expected: missing lifecycle and contract failures.

**Step 3: Implement the integration**

Startup order is schema installation, runtime config creation, LLM config
creation, LLM runtime initialization, then existing services. A configuration
failure records LLM as unavailable and continues non-AI startup.

Shutdown order is scheduler, LLM runtime, then message store. Use structured
cleanup so every service is attempted. Export the getter from both contract
modules. Subplugins continue to import only the parent-owned contract and never
`services.llm` directly.

**Step 4: Verify**

```bash
TMPDIR=/tmp uv run -m pytest -s \
  tests/services/llm/test_reload.py \
  tests/start/test_startup.py \
  tests/hooks/handlers/test_lifecycle.py \
  tests/hooks/test_integration.py \
  tests/core/subplugins/test_contracts.py \
  tests/core/subplugins/test_import_boundary.py
```

Expected: atomic reload, startup isolation, shutdown, and import boundaries pass.

## Task 10: Align Dependencies, Live Contracts, Environment Examples, And Docs

**Files:**

- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `README-zh.md`
- Modify: `apps/docs/content/docs/user-guide/configuration/index.mdx`
- Modify: `apps/docs/content/docs/user-guide/configuration/index.zh.mdx`
- Modify: `REUSE.toml` only if existing globs do not cover new files
- Create: `tests/services/llm/test_live.py`

**Step 1: Reconcile concurrent dependency changes**

Re-read `git diff -- pyproject.toml uv.lock` before editing. Preserve unrelated
NovelAI/dependency work. Set the `ai` extra minimums to the inspected native
contract versions:

```toml
ai = [
  "openai>=2.45.0",
  "litellm>=1.92.0",
]
```

Use the repository's actual dependency table shape rather than duplicating
keys. Regenerate the lock with `uv lock`; do not hand-edit resolved entries.

**Step 2: Add opt-in live contract tests**

Add `llm_live = "calls configured live LLM providers"` to
`[tool.pytest.ini_options].markers`. `test_live.py` skips unless
`LINGCHU_LLM_LIVE_TESTS=1` and the relevant credential environment variable is
present. Cover one minimal OpenAI Responses request and one minimal LiteLLM
request without asserting provider wording. Default CI performs no billed call.

Run:

```bash
TMPDIR=/tmp uv run -m pytest -s tests/services/llm/test_live.py
```

Expected: tests skip cleanly without the opt-in environment variable.

**Step 3: Document the operator workflow and security boundary**

Document `llm.toml`, profiles, `llm.toml > legacy ai_*` precedence,
`api_key_env`, Responses versus Chat mode, Router, native escape hatches,
capability tri-state, reload behavior, private-network/custom-credential
switches, and the no-automatic-tool-execution rule in English and Chinese.

Correct stale README environment names from `AI_*` to `LINGCHU_AI_*`, and add a
safe `.env.example` showing environment variable names without secret values.
No QQ command reference change is needed because command syntax is unchanged.

**Step 4: Verify dependencies and docs**

```bash
uv lock --check
TMPDIR=/tmp uv run -m pytest -s tests/services/llm/test_sdk_contract.py
pnpm --filter docs lint
pnpm --filter docs test
pnpm --filter docs exec tsc --noEmit
pnpm exec markdownlint-cli2
reuse lint
```

Expected: lock is current, SDK sentinel tests pass, docs checks pass, and every
new file is REUSE-covered.

## Task 11: Full Regression, Security Review, And Completion Evidence

**Files:** No intended source edits; fix only evidence-backed findings.

**Step 1: Run the focused security suite**

```bash
TMPDIR=/tmp uv run -m pytest -s \
  tests/services/llm/test_security.py \
  tests/services/llm/test_config.py \
  tests/services/llm/test_lifecycle.py \
  tests/services/llm/test_streaming.py \
  tests/services/llm/test_reload.py
```

Expected: redaction, SSRF, input-boundary, cancellation, close, and reload tests
all pass.

**Step 2: Run Python and consumer regression gates**

```bash
uv run -m ruff check . --output-format=github
uv run -m ruff format --check .
uv run -m pyright
uv run -m ty check --output-format github
TMPDIR=/tmp uv run -m pytest -s \
  tests/services \
  tests/start \
  tests/hooks \
  tests/core/subplugins/llm_chat \
  tests/core/subplugins/novelai_image \
  tests/core/test_schemas.py \
  tests/core/test_runtime_config.py \
  tests/core/test_runtime_config_ai.py
```

Expected: all commands exit zero.

**Step 3: Run repository-level gates**

```bash
task check
task test
timeout 20s uv run nb run -r
```

Expected: repository checks pass. The smoke test reaches
`Application startup complete.` without AI extras being required; timeout exit
124 is acceptable only after that line and one event-loop cycle are observed.

**Step 4: Perform final graph and diff review**

Run:

```text
detect_changes(scope="compare", base_ref="main")
```

Confirm the affected graph is limited to the expected LLM chat, NovelAI
intent/search, startup/shutdown, schema, configuration, and contract flows.
Review `git status --short`, `git diff`, and `git diff --cached`; distinguish
pre-existing concurrent work from this implementation.

Ask a fresh reviewer to check the completed implementation against the design,
this plan, and the security invariants. Resolve every Critical, High, and
Medium finding and rerun the relevant gates. Do not weaken tests, add inline
ignore comments, or broaden exception handling to make a check green.

**Step 5: Report completion evidence**

Report changed files, targeted and full checks, skipped live tests and their
reason, pre-existing changes left untouched, GitNexus affected flows, and
whether AGENTS/CLAUDE/Chinese mirrors needed synchronization. They should not
need changes because no repository-wide agent rule is added by this feature.
