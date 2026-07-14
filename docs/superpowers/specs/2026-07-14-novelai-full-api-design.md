# NovelAI Full API Capability Design

**Status:** Implemented and verified
**Date:** 2026-07-14
**Target branch:** `main`
**Reference capability baseline:** `tmp/NekoAI-API` at local `main` (`0.4.0`)

## 1. Goal

Replace Lingchu Bot's generate-only NovelAI transport with a first-class NovelAI
domain service that exposes every API capability present in the reference client,
while preserving Lingchu's existing intelligent prompt pipeline and project-owned
configuration, transport, error, i18n, and subplugin boundaries.

The completed feature must be useful from the QQ command surface and reusable from
Python code. It must not depend on, vendor, or copy `nekoai-api`; that project is an
AGPL-3.0 reference implementation, while Lingchu Bot code is LGPL-3.0-or-later.

## 2. Product Principles

1. **Full capability, not a forwarding wrapper.** Lingchu owns request models,
   validation, payload construction, response parsing, caching, and API methods.
2. **One NovelAI domain.** Text generation, image-conditioned generation, image
   tools, utilities, and account queries share authentication and error semantics.
3. **Safe chat UX.** Binary inputs come from image segments attached to explicit
   command options; credentials and raw base64 are never echoed to chat.
4. **Feature-aware degradation.** Optional LLM search and TIPO remain fail-open.
   NovelAI API operations themselves fail explicitly with localized errors.
5. **No hidden compatibility layer.** The old text-to-image command remains valid,
   but new capabilities use an explicit action/subcommand grammar.

## 3. Capability Contract

### 3.1 Authentication and hosts

- Direct bearer token remains the preferred credential.
- Optional username/password authentication derives the NovelAI access key and
  exchanges it through `POST /user/login` on the account host.
- `base_url` targets image APIs; `account_base_url` targets login/account APIs.
- Custom reverse-proxy hosts are supported independently.
- The service never persists a derived access token or password.

### 3.2 Image generation

Supported models:

- NAI Diffusion V4.5 Full and Curated, including inpainting variants.
- NAI Diffusion V4 Full and Curated, including inpainting variants.
- NAI Diffusion V3 and Furry V3, including inpainting variants.

Supported generation behaviors:

- text-to-image, img2img, and inpainting;
- 1-8 samples with model/resolution-aware validation;
- V4/V4.5 length-prefixed MessagePack responses and real-time events;
- V3 ZIP responses;
- multi-character prompts, per-character undesired content, coordinates, and order;
- quality tags, undesired-content presets, sampler/noise schedule, CFG rescale,
  SMEA/dynamic SMEA, dynamic thresholding, and legacy compatibility flags;
- V3 raw-reference vibe transfer;
- V4/V4.5 `/ai/encode-vibe` conversion with in-memory content-addressed caching;
- Anlas cost estimation as informational metadata, never as authorization logic.

The existing LLM -> optional web search -> optional TIPO -> planner pipeline feeds
text-to-image defaults. Explicit user options continue to outrank LLM hints, which
continue to outrank TOML defaults. Image-conditioned modes may reuse the same prompt
pipeline but must not require it for pure image tools.

### 3.3 Director tools

`POST /ai/augment-image` supports:

- line art;
- sketch;
- background removal;
- declutter;
- colorize with prompt and defry strength;
- emotion change with emotion and strength presets.

### 3.4 Utilities and account APIs

- `POST /ai/upscale` for 2x/4x upscaling.
- `POST /ai/annotate-image` for ControlNet condition masks.
- `GET /ai/generate-image/suggest-tags` for tag completion.
- `GET /user/subscription` for tier/Anlas data.
- `GET /user/data` for account data.

### 3.5 Binary input and output

- Image-tool methods accept raw PNG/JPEG bytes; generation requests carry base64
  image fields. Named chat options resolve unified-message image segments into bytes.
- Image dimensions are extracted without adding Pillow.
- Generated batches are returned as immutable image value objects.
- V4 intermediate JPEG and final PNG events retain sample index, step index,
  generation id, and sigma.
- The QQ surface sends final images only. Streaming events are available to Python
  callers and can drive future progress UIs without changing the protocol client.

## 4. Architecture

The subplugin is split by responsibility:

- `constants.py`: stable enums and endpoint/model capability tables.
- `auth.py`: access-key derivation and credential selection.
- `imaging.py`: PNG/JPEG parsing and base64 conversion.
- `models.py`: immutable requests, responses, generation settings, and validation.
- `payload.py`: generation/director/utility payload serialization.
- `response.py`: status mapping, ZIP parsing, MessagePack incremental parsing.
- `client.py`: endpoint operations over NoneBot's shared HTTP session, plus a bounded
  process-wide vibe-token cache isolated by host, model, information strength, and
  reference content.
- `service.py`: child-config credential and client construction.
- `handler.py`: Alconna grammar, named image-option resolution, orchestration, and
  i18n.

The parent plugin continues to expose only generic facilities through
`core/subplugins/contracts.py`; no NovelAI-specific registry is added to the parent.

## 5. Command Surface

The legacy form remains the default text-to-image action:

```text
生图 <description> [generation options]
```

Additional explicit actions are provided under the same locale-exclusive command:

```text
生图 img2img <description> --image <image> [--strength N] [--noise N]
生图 inpaint <description> --image <image> --mask <image> [options]
生图 vibe <description> --reference <image> [--reference-strength N]
生图 tool <lineart|sketch|background-removal|declutter> --image <image>
生图 tool colorize --image <image> [--prompt TEXT] [--defry N]
生图 tool emotion --image <image> --emotion NAME [--emotion-level N]
生图 upscale --image <image> --factor <2|4>
生图 annotate --image <image> --model MODEL
生图 tags <prefix> [--model MODEL] [--lang LANG]
生图 account <subscription|data>
```

`<image>` is a OneBot image segment supplied to the named option. The unified
message layer may represent it as bytes, a local adapter path, or an HTTP(S) URL;
downloads enforce HTTP(S), a bounded response size, image-signature validation,
and the configured timeout. Inpainting requires two explicit image segments.

## 6. Configuration

`novelai_image.toml` gains:

- `account_base_url`, `username`, and optional environment-only password support;
- default model/action generation controls;
- quality/UC/noise/SMEA/CFG and sample defaults;
- image-download byte limit;
- vibe cache entry limit;
- timeout and cache/download safety limits. Python callers always have access to the
  streaming method; chat continues to send final images only.

Secrets accept `LINGCHU_NOVELAI_*` environment overrides. Generated TOML omits
password and token values when unset. The generated JSON schema describes all
TOML-representable fields.

## 7. Error Model

Transport, timeout, validation, authentication, insufficient Anlas, concurrency,
provider, malformed response, and image-processing errors are distinct exception
types. HTTP status mapping is:

- 400 -> validation;
- 401 -> authentication;
- 402 -> insufficient credits/subscription;
- 409 -> provider conflict;
- 429 -> concurrency/rate limit;
- other 4xx/5xx -> provider error.

Error bodies are bounded before inclusion in logs/exceptions and never include
credentials. Chat receives localized, non-sensitive summaries.

## 8. Testing and Acceptance

Acceptance requires:

1. Payload-shape tests for V3/Furry and V4/V4.5 generation families, conditioned
   modes, batch limits, prompt presets, and reference conditioning.
2. Red/green tests for auth derivation, model/action validation, image parsing,
   ZIP/MessagePack parsing, streaming chunk boundaries, vibe caching, endpoints,
   and status mapping.
3. Handler tests covering legacy generation plus each new action family.
4. Config/schema/default tests and English/Chinese docs parity.
5. Targeted NovelAI tests, Ruff format/check, Pyright strict, ty strict, relevant
   docs tests, and GitNexus `detect_changes(scope="compare", base_ref="main")`.

Live NovelAI calls are not required because they need user credentials and consume
Anlas. HTTP interactions are verified with deterministic mocked responses and
field-level comparisons derived from the reference payload fixtures.

## 9. Non-goals

- Persisting NovelAI credentials, access tokens, or generated images.
- Replacing the global LLM service or TIPO server.
- Reintroducing V1/V2 image generation; ControlNet support is annotation-only.
- Copying NekoAI-API source or making it a runtime dependency.
- Sending intermediate streaming frames into QQ in this iteration.

## 10. Completion Evidence

The final report must list touched files, targeted and broad verification outputs,
unrun checks with reasons, dirty worktree preservation, mirror-sync applicability,
and the final GitNexus affected-flow summary. This document must be updated if the
implementation makes a materially different product decision.

Final evidence recorded on 2026-07-14:

- NovelAI-focused suite: 195 tests passed during feature iteration.
- Full backend suite: 1020 tests passed; branch coverage reached 86.31% against
  the enforced 86% minimum.
- Full docs unit suite: 115 tests passed.
- `task check` passed Ruff check/format, Markdownlint, docs ESLint, Pyright, ty,
  and docs TypeScript checks. Pyright reported zero errors; the existing 737
  strict-mode warnings remain non-blocking. Docs ESLint reported zero errors and
  15 pre-existing warnings.
- Serialized Playwright hook smoke passed all 3 tests. A prior concurrent attempt
  was discarded because two workers contended for the same local port.
- Markdownlint checked 20 human-facing files with zero errors.
- `reuse --no-multiprocessing lint` and `git diff --check` passed. The global
  switch avoids this host's Python 3.14 fork-server limitation.
- GitNexus compared the worktree to `main`: 63 indexed symbols in 16 indexed files
  changed and seven existing NovelAI flows were affected. Every flow starts at
  `novelai_image_handler` and continues through either the existing LLM prompt
  analysis chain or child-config loading; no unrelated runtime flow was reached.
- No live NovelAI request was run because it requires a user credential and spends
  Anlas. All HTTP contracts use deterministic mocked responses.

## 11. Repository Markdown Quality Boundary

Markdownlint uses `.markdownlint-cli2.jsonc` as its only scope and rule source.
Positive globs include root policy/readme files plus Markdown under `apps`,
`packages`, and `.github`. Native Git-ignore discovery excludes generated output,
caches, local data, tool indexes, temporary reference checkouts, and other non-human
artifacts. Agent-only skill content is not in the positive globs. Task, Husky, and
both CI workflows invoke markdownlint without their own path lists.
