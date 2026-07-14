# Full-Featured LLM Runtime Design

**Status:** Approved for implementation planning

**Date:** 2026-07-14

## Goal

Replace the current text-only LLM wrapper with a managed runtime that preserves
the complete capabilities of the installed LiteLLM and OpenAI Python SDKs while
keeping Lingchu Bot's existing chat and NovelAI consumers stable.

The result must support ordinary provider-neutral use, full provider-native
use, and future SDK endpoints without requiring every SDK parameter or resource
to be copied into a Lingchu-owned request model first.

## Definition Of “All Features”

“All features” is a non-lossy access guarantee, not a claim that every model,
provider, or SDK implements the same operations.

The implementation is complete when all of the following are true:

1. Internal callers can obtain a managed native `AsyncOpenAI` client and use
   every resource exposed by the installed OpenAI SDK.
2. Internal callers can access the installed LiteLLM async SDK operations and a
   managed LiteLLM `Router` without a Lingchu-maintained endpoint allowlist.
3. Native request parameters, provider-specific parameters, `extra_body`,
   `extra_query`, `extra_headers`, streaming events, native response objects,
   usage data, request IDs, and provider metadata are not discarded.
4. Updating either SDK can expose a new native resource or async operation
   without first adding an equivalent Lingchu wrapper method.
5. The stable Lingchu API covers common application workflows but is never the
   only route to the SDKs.
6. Capability checks are advisory. They may report supported, unsupported, or
   unknown, but they do not block an explicitly requested native call.

This definition deliberately does not promise that an OpenAI-only endpoint can
be emulated by LiteLLM, that every LiteLLM provider accepts every OpenAI field,
or that a configured model supports every modality.

## Current Baseline

The repository currently has:

- `services/llm.py`, a single-file service centered on
  `complete_chat(...) -> str`;
- a LiteLLM `acompletion` path and a direct OpenAI Chat Completions fallback;
- a LiteLLM-only native web-search special case;
- global `ai_provider`, `ai_model`, `ai_base_url`, `ai_api_key`, and
  `ai_timeout` settings;
- stable parent-to-subplugin contracts used by the LLM chat and NovelAI image
  subplugins.

The dependency snapshot inspected for this design is LiteLLM 1.92.0 and OpenAI
Python 2.45.0 from `uv.lock`. The declared minimums are older. Implementation
must raise the `ai` extra minimums to the inspected versions because this design
depends on their current native surfaces.

GitNexus reports `complete_chat` as a **HIGH-risk** change point: it has two
direct contract callers and affects both the LLM chat and NovelAI image flows.
The migration must therefore add the new runtime first and retain the existing
text facade until all current consumers pass their existing tests.

## Product Decisions

- LiteLLM remains the default backend for multi-provider access.
- The direct OpenAI SDK remains a first-class backend, not merely an emergency
  implementation hidden behind LiteLLM.
- OpenAI Responses is the preferred OpenAI generation API. Chat Completions is
  retained as a compatibility resource and for OpenAI-compatible endpoints.
- The public architecture has three access levels: stable Lingchu operations,
  typed backend access, and an explicit native escape hatch.
- Native SDK objects are allowed inside `services/llm/` and through explicit
  native handles. Ordinary handlers continue to depend on subplugin contracts.
- Native return objects remain native. A normalized result may contain a native
  object, but it never replaces or truncates it.
- LiteLLM Router support is in-process. Running LiteLLM Proxy or managing its
  administrative API is not required by this design.
- The bot does not automatically execute model-requested tools. Tool schemas,
  tool calls, and tool results can pass through; execution policy belongs to a
  separate agent/tool-runtime feature.
- Prompts, files, audio, images, tool arguments, API keys, and provider response
  bodies are not logged by default.

## Rejected Approaches

### One Universal Request And Response Model

A universal model looks convenient but becomes a lowest-common-denominator
API. It would need continual edits for new OpenAI resources, LiteLLM operations,
provider-specific parameters, and streaming event types. This recreates the
thin-service limitation at a larger scale.

### Direct SDK Imports Throughout Business Code

Direct imports preserve features but spread credential resolution, timeouts,
retries, client cleanup, logging, and dependency errors across handlers. They
also violate the existing parent-to-subplugin import boundary.

### Selected Design: Dual Native Backends With A Stable Facade

The selected design centralizes lifecycle and policy while exposing native
clients and operations explicitly. Common behavior stays easy to consume, and
uncommon or newly released SDK behavior remains immediately reachable.

## Architecture

```text
Handlers and nested subplugins
          |
          | stable parent contracts
          v
      LLMRuntime
       /      \
      /        \
stable facade   native backend handles
  |                 /            \
  |                /              \
text/responses  LiteLLMBackend   OpenAIBackend
stream/search    SDK + Router     AsyncOpenAI
  |                |               |
normalized        native          native
events/results    objects         objects
```

`LLMRuntime` owns resolved profiles, backend instances, client reuse, optional
Router construction, structured telemetry, and shutdown. It does not pretend
that the two native SDK object graphs share one type.

## Package Layout

Convert `services/llm.py` into a package:

```text
services/llm/
  __init__.py
  backends.py
  capabilities.py
  compat.py
  config.py
  errors.py
  events.py
  runtime.py
  types.py
```

Responsibilities:

| File | Responsibility |
| --- | --- |
| `__init__.py` | Small public export surface; no eager optional-SDK imports |
| `backends.py` | `LiteLLMBackend` and `OpenAIBackend` native access |
| `capabilities.py` | Advisory capability probes and support states |
| `compat.py` | Existing `complete_chat` and web-search compatibility facade |
| `config.py` | Localstore-backed `llm.toml`, profile resolution, legacy defaults |
| `errors.py` | Dependency, configuration, transport, rate-limit, and response errors |
| `events.py` | Stable streaming event projection with attached native event |
| `runtime.py` | Runtime lifecycle, facade operations, backend/profile selection |
| `types.py` | Frozen project-owned requests, results, profiles, and metadata |

The package conversion must include `__init__.py` re-exports so existing
imports from `...services.llm` continue to resolve.

## Public Interfaces

### Profiles

```python
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

LLMBackendName = Literal["litellm", "openai"]

@dataclass(frozen=True, slots=True)
class LLMProfile:
    name: str
    backend: LLMBackendName
    model: str
    base_url: str | None = None
    api_key: str | None = None
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
```

`provider_options` is an internal, administrator-controlled passthrough. It is
not populated from QQ command input. Call-specific keyword arguments override
profile defaults, except that the stable facade rejects credentials, endpoint
overrides, transports, clients, callbacks, loggers, and retry-control objects.
Those control-plane features remain available only through explicit native
handles used by trusted internal code.

### Runtime

```python
from collections.abc import AsyncIterator, Mapping, Sequence

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

    def stream(
        self,
        input: object,
        *,
        profile: str | None = None,
        **params: object,
    ) -> AsyncIterator[LLMEvent]: ...

    async def close(self) -> None: ...
```

`respond` is the modern stable generation facade. For OpenAI it uses Responses.
For LiteLLM it uses `aresponses` when `litellm_generation = "responses"` and
`acompletion` when `litellm_generation = "chat"`. A provider error never
silently changes the operation. It forwards unknown data-plane fields unchanged
after applying project-owned defaults and rejecting control-plane overrides.

The facade is intentionally not used for embeddings, image/audio/video
generation, files, batches, realtime, vector stores, fine-tuning, evals, or
other resource-specific operations. Those use backend-native access so their
types and semantics remain intact.

### Stable Response And Stream Projection

```python
@dataclass(frozen=True, slots=True)
class LLMUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None

@dataclass(frozen=True, slots=True)
class LLMResponse:
    text: str | None
    backend: LLMBackendName
    model: str
    request_id: str | None
    usage: LLMUsage
    raw: object

@dataclass(frozen=True, slots=True)
class LLMEvent:
    type: Literal[
        "started",
        "text_delta",
        "tool_call_delta",
        "output_item",
        "usage",
        "completed",
        "error",
        "native",
    ]
    data: object
    raw: object
```

Every native stream event is observable through `raw`. Events that cannot be
normalized become `type="native"`; they are never silently dropped. The final
`completed` event carries the assembled `LLMResponse` when the SDK provides
enough information to build one.

### OpenAI Native Backend

```python
class OpenAIBackend:
    @property
    def client(self) -> AsyncOpenAI: ...

    def with_options(self, **options: object) -> AsyncOpenAI: ...
```

The managed client exposes the installed SDK unchanged, including resources
such as Responses, Chat Completions, embeddings, images, audio, moderations,
files, uploads, batches, vector stores, containers, conversations, realtime,
fine-tuning, evals, skills, videos, webhooks, and future resources.

Callers can also use `client.with_raw_response`,
`client.with_streaming_response`, resource auto-pagination, `extra_headers`,
`extra_query`, and `extra_body`. Lingchu does not wrap or retype these native
paths.

One managed `AsyncOpenAI` client is cached per resolved profile. The runtime
closes every cached client during NoneBot shutdown. Per-call variants use the
SDK's `with_options(...)` rather than constructing throwaway HTTP clients.

### LiteLLM Native Backend

```python
from collections.abc import Awaitable, Callable
from types import ModuleType
from typing import Any

class LiteLLMBackend:
    @property
    def sdk(self) -> ModuleType: ...

    @property
    def router(self) -> object | None: ...

    async def call(
        self,
        operation: str,
        /,
        **params: Any,
    ) -> Any: ...
```

`sdk` is the lazily imported `litellm` module. `call` resolves a public async
operation by name, verifies that it is callable and asynchronous, merges the
resolved profile defaults, then invokes it. It must not maintain an endpoint
allowlist.

This makes current operations such as `aresponses`, `acompletion`,
`aembedding`, `aimage_generation`, `aimage_edit`, `aimage_variation`, `aspeech`,
`atranscription`, `amoderation`, `arerank`, batch/file/vector-store/container/
eval/fine-tuning/video operations, `allm_passthrough_route`, provider-native
generation, and future async operations available without a service edit.

Operation names are internal code constants. User-controlled text cannot select
an arbitrary operation or supply arbitrary keyword arguments.

When Router is enabled, `router` exposes the real LiteLLM `Router`. Callers use
its native async methods and receive native objects. When disabled, `router` is
`None`; direct LiteLLM SDK operations remain available.

The runtime must not change LiteLLM process-wide globals for per-request
behavior. Router configuration and call parameters are preferred over global
assignments such as module-level retry or callback settings.

## Capability Model

```python
CapabilitySupport = Literal["supported", "unsupported", "unknown"]

@dataclass(frozen=True, slots=True)
class CapabilityResult:
    capability: str
    support: CapabilitySupport
    source: str
    reason: str | None = None
```

Rules:

- LiteLLM uses its native `supports_*` probes where available.
- The presence of an SDK operation means the operation is available, not that
  the configured provider/model supports it.
- OpenAI resource presence is detectable; model-level support is `unknown`
  unless the SDK/API supplies authoritative metadata.
- Probe exceptions return `unknown`, not `unsupported`.
- Capability results may guide user experience but cannot veto a native call.
- Results may be cached only by backend, model, base URL, SDK version, and
  capability. Configuration reload invalidates the cache.

The existing boolean `supports_web_search` remains as a compatibility helper
implemented on top of this tri-state model.

## Configuration

### Existing Defaults

The existing `config.toml` keys remain accepted and form an implicit `default`
profile when no dedicated LLM profile exists:

- `ai_provider`
- `ai_model`
- `ai_base_url`
- `ai_api_key`
- `ai_timeout`

`ai_provider` continues to mean SDK backend (`litellm` or `openai`), not the
upstream model vendor.

### Dedicated LLM Configuration

Add localstore-managed `llm.toml` and `llm.schema.json`. The first startup
creates both through the existing subplugin/config patterns.

```toml
default_profile = "default"

[profiles.default]
backend = "litellm"
model = "openai/gpt-5.5"
timeout = 60.0
max_retries = 2
api_key_env = "OPENAI_API_KEY"
litellm_generation = "responses"
allow_private_network = false
allow_credentials_to_custom_base_url = false

[profiles.direct_openai]
backend = "openai"
model = "gpt-5.5"
timeout = 60.0
max_retries = 2
api_key_env = "OPENAI_API_KEY"

[litellm.router]
enabled = false
routing_strategy = "simple-shuffle"
allowed_fails = 3
cooldown_time = 60
model_list = []
fallbacks = []
context_window_fallbacks = []

[observability]
log_usage = true
```

`base_url` accepts only HTTP(S), with no userinfo, fragment, or control
characters. Link-local and metadata endpoints are always rejected. Private and
loopback networks require `allow_private_network = true`; sending credentials
to a custom endpoint additionally requires
`allow_credentials_to_custom_base_url = true`. Operators must account for DNS
rebinding and redirect targets when enabling private-network access.

Requirements:

- Profile names are unique non-empty strings.
- `default_profile` must exist after legacy fallback resolution.
- `api_key_env` names an existing environment variable at call time. A missing
  key raises a configuration error only when that profile is used.
- A literal `api_key` remains accepted for current configuration compatibility
  but documentation marks environment-based secrets as preferred.
- `timeout` is positive and `max_retries` is non-negative.
- Profile `provider_options` and LiteLLM Router-specific tables allow extra
  keys so new SDK options do not require an immediate schema release.
- Extra keys remain administrator-controlled configuration and are never
  copied from incoming chat messages.
- `llm.toml` wins over legacy `ai_*` values for named profiles. Legacy values
  remain the fallback for the implicit default profile.
- Invalid `llm.toml` fails LLM initialization with a precise file-and-field
  error but does not corrupt or overwrite the user's file.

## Dependency And Import Behavior

The `ai` optional extra becomes:

```toml
ai = [
  "openai>=2.45.0",
  "litellm>=1.92.0",
]
```

No SDK imports execute at base plugin import time. Backend selection performs a
lazy import. If one dependency is missing:

- selecting that backend raises `LLMDependencyError` with the exact missing
  extra and install command;
- the other installed backend remains usable;
- importing subplugin contracts and running non-AI bot features still works.

Provider SDK types may appear under `TYPE_CHECKING`; runtime annotations must
not force optional dependency imports.

## Errors And Cancellation

Native access preserves native SDK exceptions. Stable facade operations map
known failures to project errors while retaining the original exception as
`__cause__` and exposing safe metadata:

```text
LLMError
├── LLMDependencyError
├── LLMConfigurationError
├── LLMAuthenticationError
├── LLMRateLimitError
├── LLMTimeoutError
├── LLMConnectionError
├── LLMResponseError
└── LLMProviderError
```

Stable errors carry backend, model, request ID, HTTP status when known, and a
retryable flag. They do not include API keys, authorization headers, full
prompts, file bodies, or raw provider response bodies in their public message.

`asyncio.CancelledError`, generator cancellation, and client shutdown signals
are never wrapped or converted into soft provider failures. Stream cleanup must
close the underlying native stream or response context.

The existing web-search helper keeps its documented soft-failure behavior for
the NovelAI research path. The native and stable general-purpose APIs do not
silently convert failures into `None`.

## Observability

Every stable call emits one structured completion record with:

- operation;
- profile name;
- backend and resolved model;
- duration;
- success or normalized error category;
- request ID when available;
- input, output, cached, and reasoning token counts when available;
- LiteLLM cost when available;
- retry/fallback count when the SDK exposes it.

Logs never include prompts, outputs, authorization values, raw provider bodies,
URL query secrets, or binary content. Native calls may participate in
LiteLLM callbacks or OpenAI response metadata, but callback registration must
be runtime-owned and idempotent.

The initial implementation writes structured logs only. Persistent usage,
budget dashboards, OpenTelemetry exporters, and billing enforcement can consume
the same record in later features without changing backend calls.

## Existing Consumer Migration

### Compatibility Facade

Keep these public functions and their current behavior in `compat.py`:

```python
async def complete_chat(
    messages: Sequence[ChatMessage],
    *,
    model: str | None = None,
    options: LLMOptions | None = None,
) -> str: ...

def supports_web_search(options: LLMOptions) -> bool: ...

async def complete_with_web_search(
    messages: Sequence[ChatMessage],
    *,
    options: LLMOptions | None = None,
) -> WebSearchResult | None: ...
```

They delegate to the new runtime and project a plain string or
`WebSearchResult`. `LLMOptions` remains available and resolves to an ephemeral
profile. No current caller is forced to understand native objects.

### Subplugin Contracts

The parent contract remains the only supported import route for nested
subplugins. Add:

```python
def get_subplugin_llm_runtime() -> LLMRuntime: ...
```

Existing helpers remain exported. New advanced subplugins may obtain the
runtime and explicitly choose stable or native access without importing parent
implementation modules directly.

The contract must not expose a user-selectable operation-by-name API. Child
code chooses operations statically.

### Current Flows

- LLM chat continues to use `complete_subplugin_chat_default` and receives
  plain text.
- NovelAI intent analysis continues to use the same plain-text contract.
- NovelAI visual research continues to receive `WebSearchResult | None` and
  retains soft failure.
- After compatibility tests pass, these consumers may adopt Responses or
  streaming in separate product changes. That adoption is not required to
  complete this runtime redesign.

## Security Boundaries

- QQ users cannot select SDK operation names, resource paths, base URLs,
  headers, arbitrary request bodies, files, or provider options.
- Base URLs and credentials come only from administrator configuration or the
  process environment.
- Native web/file/MCP/tool results are untrusted input and never become system
  instructions automatically.
- No generic automatic tool executor is included.
- File operations must use explicit application-selected files and existing
  localstore ownership rules; model-produced paths are not opened.
- Provider callbacks and logs receive bounded, redacted metadata. The runtime
  never logs prompts, outputs, raw provider bodies, or authorization data.
- Realtime connections and streams are bounded by timeout/cancellation and
  closed when their owning task exits.
- Operation names and native arguments are selected by trusted internal code;
  QQ text, HTTP input, and model tool arguments never flow into the generic
  operation resolver.

## Lifecycle And Reload

The runtime has explicit `NEW`, `RUNNING`, `CLOSING`, and `CLOSED` states.
Initialization and backend acquisition are concurrency-safe. Once closing
begins, no new client or Router may be created. Close is idempotent,
cancellation-safe, and attempts every owned resource even if one close fails.

Reload parses and validates a complete candidate configuration before an
atomic swap. Only after the new runtime is active is the old runtime closed. A
failed reload leaves the existing runtime untouched. A bad initial LLM
configuration disables LLM features and emits a safe diagnostic, but does not
prevent non-AI bot startup.

Named-profile caches use profile name plus configuration generation and a
non-reversible credential fingerprint. Ephemeral `LLMOptions` profiles are
request-scoped and never enter the named cache, preventing unbounded growth.

## SDK Capability Coverage

The following matrix defines verification sentinels. It is not an allowlist.

| Capability family | LiteLLM native route | OpenAI native route |
| --- | --- | --- |
| Responses/reasoning | `aresponses` | `client.responses` |
| Chat completions | `acompletion` | `client.chat.completions` |
| Streaming | native async iterator | Responses/chat native streams |
| Tools/structured output | native request/response fields | Responses parse/tools fields |
| Multimodal input | native message/content params | Responses/chat native params |
| Embeddings | `aembedding` | `client.embeddings` |
| Images | image async operations | `client.images` |
| Audio | `aspeech`, `atranscription` | `client.audio` |
| Moderation | `amoderation` | `client.moderations` |
| Rerank | `arerank` | native SDK only if/when exposed |
| Files/uploads/batches | native async operations | `files`, `uploads`, `batches` |
| Vector stores/containers | native async operations | `vector_stores`, `containers` |
| Realtime | native realtime operations | `client.realtime` |
| Fine-tuning/evals | native async operations | `fine_tuning`, `evals` |
| Video/skills/new resources | native async operations | `videos`, `skills`, future resources |
| Provider passthrough | `allm_passthrough_route`, native kwargs | `extra_*`, custom base URL/client |
| Routing/fallback/cooldown | native `Router` | application-selected profiles |

If a sentinel is renamed or removed by an SDK update, the dependency contract
test fails and forces an intentional compatibility decision. New SDK resources
remain accessible through the native handles before being added to this table.

## Testing Strategy

### Unit And Contract Tests

- Lazy import: base plugin and subplugin contracts import with neither AI SDK
  installed.
- Dependency isolation: LiteLLM missing does not disable OpenAI and vice versa.
- Profile resolution: dedicated profile, legacy fallback, env secret, overrides,
  validation, and config reload.
- OpenAI lifecycle: one client per profile, `with_options` reuse, and shutdown
  closes all clients exactly once.
- OpenAI non-loss: arbitrary `extra_headers`, `extra_query`, `extra_body`, and a
  native typed response survive unchanged.
- LiteLLM non-loss: arbitrary provider parameters are forwarded unchanged and
  native return objects are returned unchanged.
- LiteLLM operation resolution: a public async operation succeeds; missing,
  private, or synchronous names fail closed.
- Router: disabled state, configured construction, native async method access,
  fallback settings, and no module-global mutation.
- Responses: text, refusal, incomplete response, structured parsed output, tool
  call output, usage, request ID, and empty output.
- Streaming: text deltas, tool deltas, unknown native events, usage, completion,
  provider error, caller cancellation, and underlying stream cleanup.
- Error normalization: authentication, rate limit, timeout, connection, HTTP
  status, malformed response, safe error text, and preserved `__cause__`.
- Capability probes: supported, unsupported, unknown, probe exception, cache,
  and invalidation.
- Compatibility: all existing `tests/services/test_llm.py`, subplugin contract,
  LLM chat, NovelAI intent, and NovelAI search behavior remains green.
- SDK sentinel contract: the installed SDK exposes the resource and operation
  families listed in the capability matrix.

Unit tests mock network boundaries and never spend provider credits.

### Opt-In Integration Tests

Mark live tests separately and require explicit environment variables. Cover:

- one non-streaming Responses call through direct OpenAI;
- one streaming call with cancellation cleanup;
- one structured output or tool-call round trip;
- one LiteLLM completion through a configured provider;
- one LiteLLM Router fallback using test deployments;
- one embedding operation on each configured backend;
- one raw native call proving provider-specific metadata survives.

Paid, realtime, audio, image, video, fine-tuning, batch, and file operations are
not mandatory CI calls. Their SDK accessibility is covered by contract tests.

### Repository Verification

Implementation is not complete until these pass:

```bash
uv run -m ruff check . --output-format=github
uv run -m ruff format --check .
uv run -m pyright
uv run -m ty check --output-format github
uv run -m pytest -s tests/services tests/core/subplugins tests/core/test_runtime_config.py
pnpm --filter docs lint
pnpm --filter docs test
pnpm --filter docs exec tsc --noEmit
pnpm exec markdownlint-cli2
reuse lint
```

Run the repository's full `task check && task test` before a requested commit.
Run GitNexus `detect_changes(scope="compare", base_ref="main")` before any
requested commit and review both LLM chat and NovelAI affected flows.

## Documentation And Propagation

Implementation must update:

- English and Chinese runtime configuration docs;
- the AI chat command reference only where operator-visible defaults change;
- `.env.example` with non-secret variable names and comments;
- `core/schemas.py` or the dedicated schema installer for `llm.schema.json`;
- package extras and `uv.lock`;
- startup/shutdown hooks for runtime initialization and client cleanup;
- subplugin import-boundary tests and public contract exports.

No i18n catalog update is required unless user-facing error messages change.
No menu or trigger update is required because this design adds no command.
AGENTS, CLAUDE, and the Chinese agent-guide mirror do not need changes unless
implementation adds a new repository-wide rule.

## Delivery Slices

The implementation should be reviewed in four independently testable slices:

1. Package conversion, profiles, lazy dependencies, runtime lifecycle, and
   compatibility facade with no behavior change to existing consumers.
2. Direct OpenAI backend, Responses facade, streaming projection, native access,
   error metadata, and lifecycle tests.
3. LiteLLM native operation access, Router, capability probes, passthrough, and
   non-loss tests.
4. Dedicated configuration/schema, observability, subplugin runtime contract,
   docs, SDK sentinel tests, and full regression verification.

Each slice must leave the current chat and NovelAI flows operational. The HIGH
risk around `complete_chat` forbids a flag-day return-type change.

## Acceptance Criteria

The redesign is accepted when:

- `complete_chat` still returns plain text for every current caller;
- a caller can use `runtime.openai().client.<resource>` for any resource present
  in the installed OpenAI SDK and receives the native result;
- a caller can use `runtime.litellm().call("<public async operation>", ...)` or
  the native Router without adding a service wrapper;
- unknown native request fields and unknown native stream events are preserved;
- OpenAI Responses, Chat Completions compatibility, LiteLLM completions,
  streaming, tools/structured output transport, and embeddings have automated
  behavioral coverage;
- Router fallback/retry/cooldown configuration has automated coverage;
- missing optional dependencies fail only the selected backend;
- clients and streams are closed on shutdown or cancellation;
- logs and public errors contain no secrets or payloads by default;
- current LLM chat and NovelAI tests pass without consumer-visible regression;
- configuration, schemas, English docs, and Chinese docs agree;
- all targeted static checks, tests, markdown lint, and REUSE checks pass.

## Out Of Scope

- Deploying or administering LiteLLM Proxy.
- Building an autonomous agent loop or automatically executing tools.
- Exposing raw SDK operations as QQ commands or public HTTP endpoints.
- Persisting conversations, Responses objects, vector stores, files, or usage
  accounting in Lingchu's database.
- A web UI for credentials, model catalogs, budgets, or provider health.
- Emulating an unsupported capability across providers.
- Live CI coverage for every paid or long-running provider endpoint.
- Rewriting the current chat user experience to stream messages.

These are separate product features. Their APIs can build on this runtime
without expanding the core service into a provider emulator.
