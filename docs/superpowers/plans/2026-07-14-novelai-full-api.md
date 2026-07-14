# NovelAI Full API Capability Implementation Plan

> **For agentic workers:** Execute sequentially in this checkout. Use TDD for every
> behavior change. Do not commit because the user has not authorized commits.

**Goal:** Give Lingchu Bot complete feature parity with the local NekoAI-API 0.4.0
capability surface without depending on or copying that AGPL package.

**Architecture:** Build a project-owned NovelAI domain layer inside the removable
subplugin, then expose its safe operations through the existing locale-exclusive QQ
command. Keep the intelligent prompt pipeline as the text-generation frontend.

**Tech Stack:** Python 3.13, frozen dataclasses, Pydantic configuration, NoneBot
shared HTTP session, Alconna, MessagePack, pytest.

## Global Constraints

- Work directly on `main`; do not create a branch, worktree, commit, push, or PR.
- Run GitNexus impact analysis before editing existing symbols.
- Preserve LGPL licensing; do not import or copy NekoAI-API implementation code.
- All mutable files use localstore; this feature adds no persistent files.
- Search and TIPO remain fail-open; NovelAI operations fail explicitly.
- Keep English/Chinese docs and i18n surfaces aligned.

---

### Task 1: Protocol primitives and response parsing

**Files:** create `constants.py`, `auth.py`, `imaging.py`, `response.py`; modify
`models.py`; add focused tests beside existing NovelAI tests.

- [x] Add failing tests for enums, credential selection, access-key determinism,
  PNG/JPEG dimensions, ZIP batches, MessagePack batches/events, split chunks, and
  HTTP status-to-exception mapping.
- [x] Run those tests and confirm failures identify missing APIs.
- [x] Implement immutable protocol values and parsers with bounded input handling.
- [x] Run the focused tests and Ruff on touched files.

### Task 2: Complete generation request model and payload parity

**Files:** modify `models.py` and `payload.py`; expand `test_models.py` and
`test_payload.py`; add fixture-derived parameterized cases.

- [x] Add failing cases for all model families, generation actions, batch limits,
  quality/UC presets, V4 character prompts, img2img, inpaint, vibe, noise schedules,
  SMEA/CFG/legacy flags, and cost estimation.
- [x] Run failing cases, implement validation/serialization, then run them green.
- [x] Compare serialized shapes field-by-field with every JSON fixture under
  `tmp/NekoAI-API/examples/payloads/` without importing reference code.

### Task 3: Full endpoint client and high-level service

**Files:** rewrite `client.py`; create `service.py`; expand `test_client.py` and add
`test_service.py`.

- [x] Add failing HTTP contract tests for login, V3/V4 generation, streaming,
  vibe encode/cache, all Director tools, upscale, annotate, tags, subscription,
  user data, custom hosts, timeouts, and provider errors.
- [x] Implement endpoint methods over NoneBot's shared HTTP session.
- [x] Implement the service's credential resolution, bounded vibe cache, image
  normalization, generation orchestration, and immutable return values.
- [x] Run client/service tests and static checks on touched modules.

### Task 4: Configuration and command exposure

**Files:** modify `config.py`, `handler.py`, `i18n.py`; update config/handler tests.

- [x] Add failing config/default/schema tests for new non-secret fields and secret
  environment overrides.
- [x] Add failing parser/orchestration tests for legacy generation and every action
  family in the design command grammar.
- [x] Implement config and action dispatch, including safe option/URL image loading,
  localized errors, batch final-image delivery, and account summary redaction.
- [x] Run focused handler/config tests. (`task i18n` is part of final verification.)

### Task 5: Documentation and cross-surface validation

**Files:** update English/Chinese command reference and configuration docs; update
this spec if implementation decisions changed.

- [x] Document command examples, action matrix, costs/caveats, config, secret rules,
  streaming Python API, and optional dependency installation.
- [x] Run markdown/MDX lint, docs tests, and docs type checks required by AGENTS.
- [x] Search for stale statements that describe NovelAI as generate-only.

### Task 6: Final verification and review

- [x] Run all NovelAI tests, Ruff check/format, Pyright strict, and ty strict.
- [x] Run the broad project verification appropriate to the final changed surface.
- [x] Run `git diff --check`, review `git status` and the complete diff.
- [x] Run GitNexus `detect_changes(scope="compare", base_ref="main")` and inspect
  every affected execution flow.
- [x] Re-read the design acceptance criteria line by line; fix any uncovered gap.
- [x] Report exact evidence and leave all changes uncommitted on `main`.
