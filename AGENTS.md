<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **lingchu-bot** (5612 symbols, 10307 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/lingchu-bot/context` | Codebase overview, check index freshness |
| `gitnexus://repo/lingchu-bot/clusters` | All functional areas |
| `gitnexus://repo/lingchu-bot/processes` | All execution flows |
| `gitnexus://repo/lingchu-bot/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

## Lingchu Bot Agent Guide

> English | [中文](.github/note/AGENTS-zh.md)

The GitNexus block above is managed by `gitnexus analyze`. Do not edit, translate, reformat, or synchronize content between `<!-- gitnexus:start -->` and `<!-- gitnexus:end -->` manually. Treat angle-bracket HTML comments such as `<!-- ... -->` as CLI locator anchors: do not remove, escape, rename, translate, duplicate, or move them unless the owning CLI documents that change.

Use this file as the canonical shared context for Codex, Trae, and related agents. Keep it compact, current, and action-oriented. Do not turn it into a generated inventory of the repository.

## CREATE Framework

This guide is organized by CREATE so agents can extract the right constraint quickly:

| Letter | Section | Purpose |
| --- | --- | --- |
| C | Context | What the project is and where each source of truth lives |
| R | Role | How agents are expected to operate in this repo |
| E | Expectations | Non-negotiable constraints and quality gates |
| A | Actions | Standard development workflow and propagation surfaces |
| T | Tools | Commands, skills, hooks, and validation routes |
| E | Evidence | Lessons learned, checklists, and final proof expectations |

When editing this file, follow DRY and SMAR/TL:

- **Specific**: rules name the exact files, commands, or APIs they constrain.
- **Measurable**: each workflow has a concrete verification command or evidence requirement.
- **Actionable**: avoid vague advice; write the next operation an agent can perform.
- **Relevant**: keep only repo-wide rules or high-value failure shields.
- **Time-bounded / Timeliness-aware**: mark dependency and CI lessons as potentially stale and re-verify before relying on them.
- **Linked**: prefer references to canonical files over duplicated tables, trees, or generated inventories.
- **Tool-owned**: leave generated sections to their owning CLI; put human-maintained guidance outside generated markers. Preserve HTML-style locator tags such as `<!-- gitnexus:start -->` exactly.

## C — Context

Lingchu Bot is a NoneBot2-based group management bot. The monorepo follows a strict asset hierarchy:

- `src/` — primary asset: the Python backend plugin `src/plugins/nonebot_plugin_lingchu_bot/` (stays in place; never migrate it into `apps/`)
- `apps/` — additional assets: the Astro Starlight documentation site `apps/docs/` and the operations CLI `apps/lingc-cli/` (independently published PyPI package; uv workspace member and turbo workspace node)
- `packages/` — shared JS configurations
- Repo root — repo-level orchestration: uv workspace root, `turbo.json`, root `package.json`, and the thin-delegation `Taskfile.yml`
- Project-local skills (single source of truth): `.agents/skills/`
  - `.claude/skills/` and `.trae/skills/` are **whole-directory symlinks** to `.agents/skills/`, so Codex, Trae, and Claude Code all read from the same set; add or update a skill in `.agents/skills/` and all three agents see it.
- Chinese agent guide mirror: `.github/note/AGENTS-zh.md`
- Claude Code guide mirror: `CLAUDE.md`

Anything required for build or package distribution must live under `src/plugins/nonebot_plugin_lingchu_bot/`. Repository-root runtime/config files such as `config/` and `data/` are local development artifacts and disposable.

Do not maintain a hand-written full repository tree in this file. Use `rg --files`, GitNexus, or docs under `apps/docs/src/content/docs/developer-guide/` for current structure.

## Tech Stack

Python backend:

- Python 3.13, managed by `uv`
- NoneBot2 with OneBot V11 adapter; Milky, QQ, and OneBot V12 are deprecated and removed
- `nonebot-plugin-alconna` for command parsing
- `nonebot-plugin-orm` with `aiosqlite` for async database access
- `nonebot-plugin-localstore` for mutable data, config, cache, resource, and schema paths
- Ruff, Pyright, ty, pytest

Docs site:

- Astro, Starlight static export, React 19, Tailwind CSS 4, TypeScript 6
- `shadcn/ui` (component sources in `apps/docs/src/components/ui/`, sharing Tailwind v4 theme with Starlight via `@theme inline` bridge)
- `p5.js` (instance mode, wrapped by `src/components/p5/`, supports MDX inline demos via client wrapper and home hero animation)
- Vitest, Testing Library, ESLint, Playwright
- i18n, Starlight/Pagefind search, sitemap, Mermaid, Twoslash
- Starlight content collections own docs routing, sidebar, and localized static output
- Turborepo workspace using `pnpm`

Task orchestration:

- Turborepo unifies the whole monorepo: root tasks (`//#py:*`, `//#md:*`, `//#js:*`, `//#wheel-smoke`, scripts in root `package.json`) wrap the Python toolchain with caching; `apps/docs` and `apps/lingc-cli` are turbo workspace nodes
- `Taskfile.yml` is a thin delegation shell: `check` / `test` / `build` / `format` / `fix` / `ci:*` are single-line `pnpm turbo run ...` calls; release / version / db / hooks / smoke / gitmoji stay in Taskfile (GITHUB_OUTPUT, secrets, CLI arg passthrough)
- `task install` = `uv sync --all-extras --all-packages` + `pnpm install`

## R — Role

Agents are implementation partners for an early-stage project. Severe breaking changes are acceptable when they simplify the architecture or unblock the intended product direction, but they must be explicit, traceable, and documented.

Operating rules:

- Inspect the current repo before designing; stale memory and stale generated docs are not enough.
- Prefer existing project patterns over new abstractions.
- Ask early when requirements are missing; once the user says to implement, execute end to end.
- Do not commit, push, or open a PR without explicit user instruction.
- Before any commit, run `git status` and review `git diff` / staged diff. Never commit blindly.
- When invoking PowerShell from automation, use `pwsh.exe -NoProfile`.
- Keep AGENTS, Claude, and Chinese mirrors aligned as described below.
- After SubAgent tasks complete, the orchestrator MUST run `git status --short` and remove any scratch files (e.g. `_tmp_*`, `_writetest*`, scratch scripts, probe files) the SubAgents created. SubAgents do not clean up after themselves; the orchestrator owns the worktree hygiene boundary.

## E — Expectations

### Canonical Context Files

| File | When loaded | Purpose |
| --- | --- | --- |
| `AGENTS.md` | Codex / Trae shared context | Canonical project rules, commands, constraints, and lessons |
| `CLAUDE.md` | Claude Code context | Same shared structure as `AGENTS.md`, plus the only allowed extra section: Claude Code Behavioral Guidelines |
| `.github/note/AGENTS-zh.md` | Chinese mirror | Chinese counterpart of `AGENTS.md`, structurally synced |
| `.trae/rules/git-commit-message.md` | Trae always-applied rule | Gitmoji + Conventional Commits validation |

When `AGENTS.md`, `CLAUDE.md`, and `.github/note/AGENTS-zh.md` diverge, treat `AGENTS.md` as the source of truth, then copy/sync the same structural changes to the other two files.

This sync rule starts after `<!-- gitnexus:end -->`. GitNexus marker blocks are tool-owned and may differ by file; do not normalize them by hand. HTML comment markers are part of the CLI contract, not prose.

### Hard Constraints

- **Localstore path ownership**: All mutable data, config, cache, resource, and schema files MUST be resolved through `nonebot_plugin_localstore` helpers such as `get_plugin_data_dir()`, `get_plugin_config_dir()`, `get_plugin_cache_dir()`, `get_plugin_data_file()`, `get_plugin_config_file()`, or `get_plugin_cache_file()`.
- **No hard-coded mutable paths**: `Path("...")` for mutable runtime files is forbidden.
- **Explicit configuration writes only**: Startup MUST NOT create, migrate, or regenerate configuration files. Configuration writes belong to localstore-owned paths or explicitly supplied deployment paths.
- **Handle default registration**: Handle-level defaults MUST be registered in `handle_config_defaults/` using `register_handle_defaults()` before `HandleConfigManager` can read or update `<command_key>.toml` files.
- **Prek is hook source of truth**: `prek.toml` is the only pre-commit hook configuration (explicitly declares ruff/ty hooks, decoupled from husky, no duplicate execution). Do not reintroduce `.pre-commit-config.yaml`.
- **Version sync**: Use `Taskfile.yml` task `ci:version:write-config` to write both `src/plugins/nonebot_plugin_lingchu_bot/core/config.py` and root `package.json`.
- **Manual-trigger releases**: Formal releases are manual-trigger only — `release.yml` runs via `workflow_dispatch` with a `bump` input (no `releases/<bump>` branches). The release version is **derived entirely by the workflow** (`ci:version:bump` → `uv version --bump` from the latest tag); the developer never writes version files. Developer work is limited to scaffolding `.github/releases/<version>.md` (`task release:prepare BUMP=<bump>`) + `CHANGELOG.md`, committing those on `main`, then running `task release:publish BUMP=<bump>` (`gh workflow run release.yml -f bump=<bump>`). The workflow commits the derived version files to `main` and tags the synced commit, keeping tag and source in sync.
- **Release notes**: Every formal release updates `CHANGELOG.md` and the release policy record.
- **Release publishing**: PyPI uses Trusted Publishing / OIDC; GHCR uses `GITHUB_TOKEN` with `packages: write`; do not add long-lived package tokens.
- **Skills exclusion sync**: When changing skills exclusion patterns in `pyproject.toml`, sync the corresponding `prek.toml` comments/patterns.
- **REUSE compliance**: All files MUST have SPDX license declarations via `REUSE.toml`; `reuse lint` MUST pass before commit. New files MUST be covered by `REUSE.toml` globs or have inline `SPDX-License-Identifier` headers.
- **Docker build context**: `.dockerignore` MUST exclude `.git`, `.venv`, `node_modules`, `.env*` (except `.env.example`/`.env.prod.example`), `tests/`, `.github/`, `.trae/`, `.gitnexus/`, `.turbo/`, and cache directories before `docker build`.
- **CODEOWNERS**: `.github/CODEOWNERS` routes `src/`, `apps/docs/`, `.github/`, `Dockerfile`, `docker-compose.yml`, `Taskfile.yml`, `pyproject.toml`, `package.json`, `REUSE.toml`, `LICENSE-*` to `@xinvxueyuan` for auto-review.
- **Workflow filename hygiene**: `.github/workflows/*.yml` filenames use plain kebab-case without leading emoji prefixes. Emoji is reserved for the `name:` field so the Actions UI can still group workflows visually. CI does not reject emoji in filenames, but downstream tooling (Cygwin paths, zip archives, Windows shell autocompletion) is fragile around them, so new workflows MUST follow the plain-name convention and existing files MUST be renamed via `git mv` if touched.

### Code Style

The project enforces a unified code style across Python and frontend workspaces:

- **`.editorconfig`**: Root-level editor baseline. Python uses 4-space indent; JS/TS/CSS/MD/YAML/TOML/JSON use 2-space. LF line endings, UTF-8, final newline, trimmed trailing whitespace for all text files.
- **Python formatting**: `ruff format` (line-length 88, LF, double quotes). No Black or isort — Ruff replaces both.
- **Python docstrings**: Ruff `D` (pydocstyle) rule family with `convention = "google"`. Missing-docstring rules (`D100`–`D103`) are globally ignored due to the existing codebase size; D rules still enforce style on EXISTING docstrings. Tests have per-file D ignores.
- **Python linting**: Ruff with rule families F, W, E, I, C90, N, PL, UP, YTT, ANN, ASYNC, BLE, FBT, B, A, COM, C4, D, DTZ, T10, ICN, PIE, T20, PYI, Q, RSE, RET, SIM, SLOT, TID, TC, ARG, PTH, FAST, PERF, PGH, FURB, TRY, RUF.
- **Python type checking**: Pyright `standard` mode + ty (Astral, fast feedback). Both run in CI.
- **Frontend formatting**: Prettier (`.prettierrc.json`) for JS/TS/TSX/CSS/JSON. Markdown files are excluded — `markdownlint-cli2` owns `.md`, `eslint-plugin-mdx` owns `.mdx` (dual-linter policy).
- **Frontend linting**: ESLint 10 flat config. `apps/docs` uses Astro/Starlight-aware TypeScript and MDX linting. `eslint-config-prettier` is appended last to disable formatting rules that conflict with Prettier.
- **TypeScript**: TS 6 with `strict: true`, `target: ES2025`, `module: ESNext`, `moduleResolution: Bundler` (in `packages/typescript-config/base.json`).
- **Tool versions**: ruff>=0.15.22, pyright>=1.1.411, ty>=0.0.61, prek>=0.4.10, ESLint 10.x, TypeScript 6.x.
- **Format workflow**: `task format` runs Ruff format → Prettier → markdownlint --fix. `task fix` runs Ruff check --fix → Ruff format → Prettier → ty check --fix → markdownlint --fix.
- **Dead scaffolding removed**: `packages/eslint-config/` and `packages/ui/` (Turborepo template leftovers, not consumed by any app). `apps/docs` has its own `eslint.config.mjs`.
- **Ignore comment governance**: Inline `# noqa`, `# type: ignore`, `# pyright: ignore`, `# ty: ignore`, and file-level `# ruff: noqa` are prohibited in `src/`. All legitimate suppressions MUST live in `pyproject.toml` `[tool.ruff.lint.per-file-ignores]` with a `# comment` justification per entry. Module-level `# pyright: reportMissingImports=false` is allowed for optional-dependency imports. Frontend `@ts-ignore` is banned via `@typescript-eslint/ban-ts-comment`; use `@ts-expect-error` with a description instead. Pre-commit Phase 2.5 warns on new `# noqa` in staged `src/*.py`; CI `ignore-comment-audit` job posts a PR comment on regressions.
- **Aggressive Toolchain Strategy (2026 future-facing)**: The project commits to a future-facing toolchain baseline; the rules below are non-negotiable unless explicitly rolled back.
  - Ruff: `preview = true` + `explicit-preview-rules = true` for lint and format, proactively adopting the 2026 style guide; `future-annotations = true`, explicit `isort`, `task-tags`.
  - Pyright: `typeCheckingMode = "strict"`; NoneBot framework-constrained handler signatures are centrally managed through equivalent `per-file-ignores` config, no inline `# pyright: ignore`.
  - ty: strict mode via `[tool.ty]` + `[[tool.ty.overrides]]`; Taskfile MUST NOT mask failures with `|| true`.
  - TypeScript: strictest four-pack (`exactOptionalPropertyTypes`, `noImplicitOverride`, `noPropertyAccessFromIndexSignature`, `noUnusedLocals`) + `verbatimModuleSyntax` in `packages/typescript-config/base.json`.
  - ESLint: type-aware rule set (`no-floating-promises`, `no-misused-promises`, etc.) with `projectService`; `eslint-plugin-import-x` + `eslint-plugin-unicorn` enforce `import/order`, `import/no-cycle`, `unicorn/filename-case`.
  - Prettier: `printWidth = 100`, `singleAttributePerLine = true`.
  - pytest: `--strict-markers --strict-config`; `[tool.coverage.run]` with `branch = true`.
  - Python baseline: 3.13 (downgrade guard), `requires-python = ">=3.13, <4.0"`, `target-version = "py313"`, do NOT upgrade to 3.14.
  - Docker Compose: no `version` field, `name: lingchu-bot`, `restart: unless-stopped`.
  - CI: all workflows top-level `permissions: contents: read`, job-level elevated as needed with comment justification.

### Architecture Decisions

- Docs i18n uses Starlight root locale for English; default English URLs omit `/en/`.
- Docs build output is `apps/docs/dist`; CI, Pages upload, and smoke tests must consume that directory.
- Client components use `useSyncExternalStore` instead of `useState` + `useEffect` for mount detection.
- GitNexus is the code-intelligence and impact-analysis layer; its generated context block is owned by the CLI.
- Platform default identity groups live in platform modules such as `platforms/qq/permissions.py`; core permissions consume seeds and runtime resolvers but do not hard-code platform role trees.

## A — Actions

### Standard Development Flow

1. Check `git status --short` and note existing user changes.
2. Load only relevant skills or references; do not pre-load every guide.
3. Use GitNexus for code understanding and impact analysis before symbol edits.
4. Inspect nearby source and tests manually; tools can miss business surfaces.
5. Make the smallest coherent change.
6. Propagate user-facing or behavior changes to tests, i18n, docs, menus, triggers, runtime config, and schemas as needed.
7. Run targeted checks from the quick reference.
8. Before a requested commit, review diffs, run `detect_changes()`, then commit with the required convention.

### Cross-Cutting Change Checklist

When modifying business logic, especially adapter-layer code, check all relevant surfaces before considering the task complete:

| Surface | Typical files |
| --- | --- |
| Source | `src/plugins/nonebot_plugin_lingchu_bot/` |
| Tests | `tests/` |
| i18n | `src/plugins/nonebot_plugin_lingchu_bot/i18n/`; run `task i18n` when user-facing strings change |
| Docs | `apps/docs/src/content/docs/` |
| Menu | `src/plugins/nonebot_plugin_lingchu_bot/handle/menu.py` |
| Runtime config | NoneBot deployment environment, localstore `runtime-overrides.toml`, `bot_state.toml`, `menu.toml`, and `_lingchu_bot_contracts/` |
| Handle config files | `handle_config_defaults/<command>.py`, `<command_key>.toml` in localstore config_dir |
| Triggers | `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/commands/triggers.py` |
| Handler session injection | New matcher handlers add `session: async_scoped_session` (type only, no `= Depends(...)`); pass `session` as first arg to repository/permission calls |
| Agent context | `AGENTS.md`, `CLAUDE.md`, `.github/note/AGENTS-zh.md` |

For handle, QQ command, adapter handler, matcher, `command_key`, menu, trigger, permission, or config-coupled work, inspect `src/plugins/nonebot_plugin_lingchu_bot/handle/` and adjacent tests directly — the previous `engineering-workflow` skill reference has been removed.

### Command And Menu Rules

- Group command trigger words are locale-exclusive. Do not register Chinese and English triggers at the same time for the same matcher. Use `get_configured_locale()` and keep inactive language aliases out.
- Menus fail closed. Hide commands the current identity or implementation cannot execute.
- `MENU_FEATURES.command_key` is the shared command identifier for permission checks, menu filtering, and handler decorators.
- When adding commands, update triggers, `MENU_FEATURES`, tests, and QQ command-reference docs together.
- The remote management commands are OneBot V11 only and implemented under `handle/qq/adapters/onebot11/default/remote.py`.

### State And Config Rules

- `core/bot_state.py` persists `bot_state.toml` through localstore.
- `is_handle_active(platform_id)` resolves global AND platform state.
- `is_silent_mode(platform_id)` resolves global OR platform state.
- `selected_adapter_handle()` supports `bypass_gate` and `bypass_silent`.
- "闭嘴"/"说话" bypass silent mode but not shutdown gate.
- "开机"/"关机" bypass both gate and silent mode.
- Startup MUST NOT create, migrate, or regenerate configuration or schema files; missing mutable files use typed in-memory defaults. Deployment settings belong to NoneBot configuration, and `MutableRuntimeSettings` belongs to localstore `runtime-overrides.toml`.

### Repository API Style

- Use frozen dataclass request objects for write/audit APIs with coupled fields.
- Use `CommandAudit` for command audit payloads, then call `record_audit_fire_and_forget()` or `record_command_audit()`.
- Do not add long parameter lists for platform, adapter, bot, group, target, reason, and duration; create a request object.
- Use `fire_and_forget(coro, *, name="...")` only for discardable background work whose result is not needed by the caller.
- **Session-first parameter convention**: All `database/orm_crud/*.py` and `repositories/*.py` functions MUST accept `session: AsyncSession | async_scoped_session` as the first positional parameter. Functions MUST NOT open their own `get_session()` (only background tasks in `services/scheduler.py` and `services/message_store.py` retain `async with get_session() as s:` because they own their lifecycle). Functions MUST NOT `commit`/`rollback` — the caller controls the transaction boundary. **Exception — self-owned sessions MUST self-commit**: code paths that open their own `get_session()` (background tasks, fire-and-forget audit writers) are their own transaction boundary; they MUST `await session.commit()` after writes. `async with get_session() as s:` only closes the session on exit — an uncommitted flushed transaction is silently rolled back (2026-08-14: the message store wrote zero rows for months because of this).
- **Fire-and-forget audit/permission helpers**: When a handler-side helper (e.g. `_default_permission_resolver`, `_default_audit_writer`) wraps a repository function whose signature now requires `session`, the helper MUST open its own scoped session (`async with get_session() as session:`) to satisfy the Protocol/Callable type the caller still expects. Do not push the session parameter into the Protocol signature; keep the boundary seam local to the helper.

## T — Tools

### Skills And MCPs

| Need | Route |
| --- | --- |
| Plan/domain: grill a plan against codebase, build CONTEXT.md + ADRs | `grill-with-docs` skill |
| Plan/domain: sharpen domain language and terminology | `domain-modeling` skill |
| Plan/domain: lighter pressure-test without docs artifacts | `grilling` skill |
| Turn plan/conversation into a spec | `to-spec` skill |
| Break spec into tracer-bullet tickets with blocking edges | `to-tickets` skill |
| Test-driven development (red-green-refactor, vertical slices) | `tdd` skill |
| Lazy / minimal solution enforcement | `ponytail` skill |
| Current library, framework, SDK, API, CLI, or cloud docs | `context7-cli` / `find-docs` skills |
| OpenAI product/API docs | `openai-docs`, official docs only |
| Architecture, impact, refactor, review | GitNexus (see top of this file) |
| Hooks, Prek, Husky | `prek` skill |
| React code triage / cleanup | `react-doctor` skill |
| Web scraping, crawling, search | `firecrawl-*` skills |
| OneBot V11 / NapCat API signatures | Inspect current adapter and NapCat documentation before writing adapter calls |
| GitHub PRs, issues, CI, publishing | GitHub skills |

### Development Workflow Chain

Skills form a scheduling chain from plan to commit. Load each skill when the corresponding phase starts; do not preload the entire chain.

```text
grill-with-docs          ← phase 1: PLAN
  ↓                        grill the plan, build CONTEXT.md + ADRs
domain-modeling          ← phase 1b: sharpen domain language (optional)
  ↓
to-spec                  ← phase 2: SPEC
  ↓                        synthesize plan into a spec
to-tickets               ← phase 3: TICKETS
  ↓                        break spec into vertical-slice tickets
tdd                      ← phase 4: IMPLEMENT
  ↓                        red-green-refactor, one slice at a time
  ├─ ponytail             ← enforce minimal solution during implementation
  ├─ context7-cli         ← look up library docs when needed
  ├─ gitnexus             ← run impact() before editing any symbol
  ├─ firecrawl-*          ← web research/scraping when needed
  └─ react-doctor         ← React triage for frontend changes
prek                     ← phase 5: COMMIT
                           Git hooks: lint + format + type + test
```

Lighter alternatives: `grilling` replace `grill-with-docs` + `domain-modeling` when you only need a pressure-test without docs artifacts.

### Development Commands

Turbo aggregate entrypoints (first choice):

```bash
pnpm lint          # docs + lingc-cli lint, root ruff check, markdownlint
pnpm check-types   # docs + lingc-cli type checks, root pyright + ty
pnpm test          # root pytest + lingc-cli pytest + docs Vitest
pnpm build         # root wheel + lingc-cli wheel + docs build
pnpm format        # ruff format + prettier + markdownlint --fix
```

Taskfile (thin turbo delegation, CI-compatible entry):

```bash
task check
task test
task build
task format
task fix
task ci:static
task ci:typecheck
task ci:test
task ci:fix
task ci:build
task ci:docs
task py:test -- -k <name>   # root pytest with arg passthrough (bypasses turbo)
task i18n
task ci
```

Python (equivalent low-level calls):

```bash
uv run -m ruff check . --output-format=github
uv run -m ruff check --fix .
uv run -m ruff format --check .
uv run -m ruff format .
uv run -m pyright
uv run -m ty check --output-format github
uv run -m pytest
```

Docs:

```bash
pnpm --filter docs lint
pnpm --filter docs test
pnpm --filter docs check-types
pnpm --filter docs build
```

### Quick Verification Matrix

| Changed | Minimum checks before commit |
| --- | --- |
| Python source only | Ruff check + Ruff format check + Pyright strict + ty strict (`uv run -m ty check --output-format github`) + relevant pytest |
| Docs site only | `pnpm --filter docs lint` (covers `.ts/.tsx/.astro/.mdx` via ESLint/Astro/MDX config) + docs tests + docs type check + docs build + Playwright hook smoke + Vitest for `src/components/p5/` or `src/components/ui/` changes |
| Markdown only | `pnpm exec markdownlint-cli2` |
| i18n strings | `task i18n` + relevant pytest |
| Infrastructure config | `docker compose config` + `prek run --all-files` + `task ci:typecheck` |
| Mixed / uncertain | `task check && task test` |

Prefer granular checks during development. Full `task check && task test` is for pre-commit or broad verification.

### Git Hooks

- Pre-commit runs Prek auto-fix, markdownlint, Ruff, Pyright, ty, pytest, docs lint/type/test/e2e smoke, React Doctor for `.tsx`, then non-blocking `gitnexus analyze --force` (full rebuild, not incremental — see `.trae/specs/fix-gitnexus-post-commit-fts/` for why incremental was abandoned) and auto-stages AGENTS.md/CLAUDE.md updates into the upcoming commit.
- Commit messages use gitmoji + Conventional Commits and auto-append Signed-off-by.
- Hook CLI resolution order is local `node_modules/.bin`, global PATH, global `.cmd` shim through `cmd.exe /c`, `pnpm dlx`, then `npx -y`.
- Set `$env:HUSKY='0'` only when explicitly needed, such as automated commits.

## E — Evidence

### Required Closeout

At the end of code-changing work, report:

- What changed and which files were touched.
- Which targeted checks ran and their result.
- Any checks not run and why.
- Any existing dirty worktree changes that were left untouched.
- Whether AGENTS/CLAUDE/Chinese mirrors needed syncing.

### Lessons Learned

Lessons are failure shields, not a changelog. Keep them short, current, and verifiable. Before relying on dependency, API, or CI behavior below, verify it still holds.

#### Documentation And Mirror Sync

- When updating repo guidance, keep `AGENTS.md`, `CLAUDE.md`, and `.github/note/AGENTS-zh.md` structurally aligned.
- All three agent context files (`AGENTS.md`, `CLAUDE.md`, `.github/note/AGENTS-zh.md`) MUST be structurally aligned. When adding lessons or constraints to one, mirror to the other two in the same PR.
- Structural alignment excludes the GitNexus marker block, which is generated by `gitnexus analyze`. Preserve marker comments and other angle-bracket locator tags exactly so CLIs can find their managed ranges.
- Do not embed large generated inventories in agent context. Link to canonical docs or inspect live files.
- After structural source changes, update developer docs and search for stale references.

#### Ignore Comment Governance

- Inline `# noqa` / `# type: ignore` in `src/` are fully consolidated into `pyproject.toml` `[tool.ruff.lint.per-file-ignores]`; the prohibition and enforcement (Phase 2.5 warning + CI `ignore-comment-audit` PR comment) are documented under "Code Style → Ignore comment governance". The bullets below capture the legitimate exceptions retained in `per-file-ignores`.
- `PLR0913` (too-many-arguments) for NoneBot matcher handlers and ORM upsert functions is suppressed via `per-file-ignores` because the parameter lists are framework-constrained. Future refactoring to frozen dataclass request objects (per "Repository API Style") should reduce these suppressions.
- `BLE001` (blind-except) is intentionally allowed in startup/probe code (fail-closed/fail-soft design). Justification comments are preserved inline as plain `# <reason>` comments, not as `# noqa` directives.

#### Adapter And API Boundaries

- Same-named adapter APIs can return different shapes. OneBot V11 APIs often return `dict`; inspect installed adapter source before writing access patterns.
- Deprecated Milky, QQ, and OneBot V12 source has been fully removed from the project, including any on-demand loading utility.
- OneBot V11 group `event.get_session_id()` can include both group and user IDs. Group-scoped history must use `group_id` as `conversation_id`.
- For OneBot V11 image APIs, verify file field format against current adapter and NapCat docs before changing calls.
- WSL2 + Docker Desktop bind mount requires the WSL distro root to be in Docker Desktop's File Sharing allow-list. When it is missing, the container sees an empty directory at the bind target while `docker inspect` still reports the source path. Detect with `docker exec <ctr> mount | grep <src>`: a `fuse.bind` or plain `bind` line is correct; `overlay` (lower=`/tmp/docker-desktop-root-ro`) means the bridge returned an empty view. Fix by adding `\\wsl.localhost\<distro>\` (or `\\wsl$\<distro>\` on older WSL) under Docker Desktop → Settings → Resources → File sharing, then **Apply & restart** and recreate the container. The Windows-side `docker` daemon does not see WSL paths through plain bind; do not assume the integration is "already on" — WSL Integration and File Sharing are two distinct settings.

#### Handler Session Injection

- nonebot_plugin_orm's `async_scoped_session` is `Annotated[sa_async.async_scoped_session[sa_async.AsyncSession], Depends(coroutine(get_scoped_session))]` — `Depends` is already embedded in the `Annotated` metadata. The correct handler signature is `async def handler(session: async_scoped_session, ...)` (type annotation only); writing `session: async_scoped_session = Depends(async_scoped_session)` triggers pyright strict errors and is wrong.
- Handler signatures that need NoneBot dependency injection (bot, event, session) MUST use `@wraps(func)` on any wrapper so `inspect.signature(wrapper)` follows the wrapped function — NoneBot reads the signature to know which kwargs to inject.
- Inside wrappers (e.g. `_permission_wrapper`), extract the injected session via `session = kwargs.get("session")`; do not re-open `get_session()`.
- Test fixtures for handlers use `mock_session = AsyncMock()` with `sess.add = MagicMock()` / `sess.add_all = MagicMock()` (sync mocks for sync API), then call the handler with `session=mock_session`. For `mock.call_args` assertions, remember that `args[0]` is now `session` (repository/permission functions take session as first positional arg).
- Background tasks (`services/scheduler.py`, `services/message_store.py`) keep `async with get_session() as session:` because they own their lifecycle and are not NoneBot handler dependencies. They MUST `await session.commit()` inside the block after writes — the `async with` exit only closes the session (rolling back any uncommitted transaction); there is no outer caller to commit for them (2026-08-14: the message store silently recorded nothing for months, which made `撤回`/recall always return 0/0/0).

#### NoneBot Config Passthrough

- NoneBot's `Config` is case-insensitive: custom env keys are stored **lowercase** in `Config.model_dump()` (`LINGCHU_MESSAGE_STORE_ENABLED` → `lingchu_message_store_enabled`). Attribute access (`driver.config.LINGCHU_X`) is case-insensitive and works; **dict lookups on `model_dump()` MUST use the lowercase key**.
- When reading custom keys through `_value(source, *names, default)`, the name list MUST include the lowercase full name (`lingchu_<field>`), not just the uppercase env name. Otherwise the key never matches and the setting is a **dead config** — runtime always equals the default no matter what `.env.dev` says. Fixed 2026-08-14: 7 keys in `_lingchu_bot_contracts/runtime_settings.py` (message_store_enabled, retention_days, summary_limit, record_api_calls, cleanup_enabled, recall_message_default_count, superuser_key, protected_subject_feature_keys) were silently dead and now resolve.
- Diagnosis: a setting visible in the startup DEBUG log `Loaded Config: {...}` is NOT proof it takes effect. Check whether the consumer reads via attribute access or via dict lookup on `model_dump()`. Dead-config symptom: changing `.env.dev` has zero runtime effect and the value stays at the default.
- Env file resolution: `Env()` reads `.env` → `ENVIRONMENT` → `nonebot.init()` loads `.env.{ENVIRONMENT}` (e.g. `.env.dev`) as `_env_file`. The DEBUG line `Current Env: dev` confirms the chain.
- zhenxun host deployment: `_lingchu_bot_contracts` is imported from the **site-packages copy** (installed via uv), NOT `zhenxun/plugins/` — patch the venv copy too; a later `uv sync`/reinstall wipes the manual edit.

#### Adapter Handle Decorators

- Handler modules wrapped by `selected_adapter_handle` MUST NOT use `from __future__ import annotations`. NoneBot's `get_typed_signature` resolves forward refs via `wrapper.__globals__` (the `handle/qq/commands/common.py` module namespace), not `func.__globals__`. `@wraps(func)` copies `__wrapped__` / `__name__` / `__annotations__` but NOT `__globals__`, so adapter-specific event types (e.g. `GroupMessageEvent`) become unresolvable `NameError` at startup. Keep annotations as real type objects; mirror the same-name OneBot V11 sibling file, which never uses `from __future__ import annotations`.
- Failure surface: `handle/qq/commands/common.py::_state_wrapper` (the decorator); the 5 Telegram handlers under `handle/telegram/adapters/default/` (`bot_state.py`, `menu.py`, `moderation.py`, `mute.py`, `recall.py`) previously triggered `NameError: name 'GroupMessageEvent' is not defined` during the dev smoke test. The fix lives as a docstring at the top of each Telegram file and a NOTE block inside `_state_wrapper`.

#### Supply Chain

- All third-party GitHub Actions in `.github/workflows/*.yml` are pinned by 40-char commit SHA with `# vX.Y.Z` comments (not mutable tags). `ci-builds.yml` and `release.yml` both use `actions/attest-build-provenance@v4.1.0` (SHA `a2bbfa2…`) for SLSA Build L3 provenance. Verify with `gh attestation verify <artifact> --repository xinvxueyuan/lingchu-bot`.
- CircleCI side (`.circleci/`) uses no orbs except the certified `codecov/codecov` orb (version-pinned `@6.0.0`) for coverage uploads; cimg images are pinned by minor tag (`cimg/python:3.13.15`, `cimg/node:24.19`); uv and Task are installed from their official installers.
- Version validation system: branch name conventions (`dev-minor-*`/`dev-major-*`/`dev-alpha-*`/`dev-beta-*`/`dev-rc-*`/`dev-stable-*`) drive `BUMP_LEVEL`/`BUMP_PRERELEASE` in `ci:version:bump`. `ci:version:precheck` validates PEP 440 + greater-than-all-tags + source consistency + no-duplicate-tag. `ci:version:postcheck` calls `release:verify-version` + dev release semantics. The smart bump strategy handles stable vs pre-release tags: stable tags need level+prerelease, same-type pre-release tags just bump prerelease, `stable` clears prerelease.
- Releases are manual-trigger only: `release.yml` runs via `workflow_dispatch` with a `bump` input (`major`/`minor`/`patch`/`stable`/`alpha`/`beta`/`rc`); no `releases/<bump>` branches are pushed. The version is **derived entirely by `uv version --bump`** from the latest tag (same `ci:version:bump` chain as the daily dev build); the developer never writes version files. The developer scaffolds `.github/releases/<version>.md` with `task release:prepare BUMP=<bump>`, updates `CHANGELOG.md`, commits on `main`, and triggers with `task release:publish BUMP=<bump>`. The `build` job writes the derived version files and commits them to `main`; the `github-release` job tags that synced commit so tag and source stay in sync. `ci-builds.yml::versioned-build` runs on a **daily schedule (02:00 Asia/Shanghai, UTC `0 18 * * *`)** — never on pushes — so neither `dev*` pushes nor release commits on `main` ever receive dev auto-tags, keeping release history linear.
- `release.yml::validate` derives `BUMP_LEVEL` / `BUMP_PRERELEASE` from the `workflow_dispatch` `bump` input via the shared `task ci:version:derive-bump` task (delegating to `scripts/ci_derive_bump.py`), the same single source of truth that `ci-builds.yml::versioned-build`, `release:prepare`, and `release:notes` consume. `task ci:version:bump` is called with `DRY_RUN=true` from `release:prepare` / `release:notes` so local scaffolding does not mutate `pyproject.toml` (the task runs `git checkout -- pyproject.toml` after the bump); the `build` job writes the CI-derived version files and commits them to the dispatch branch (`main`) so the tag and source files stay in sync.
- Release notes are keyed by computed version (`.github/releases/<version>.md`); the developer scaffolds the file with `task release:prepare BUMP=<bump>` (or `task release:notes BUMP=<bump>`) and commits it on the dispatch branch before triggering. At release time, the `github-release` job merges the manual notes with GitHub's auto-generated changelog (generate-notes API, called after the tag is created) into the release body — manual notes on top, auto PR/commit changelog below a `---` separator. The merge step also replaced the old cross-job `RUNNER_TEMP` body_path reference (job temp dirs are isolated, so that body file never existed on the release runner).
- `.github/ISSUE_TEMPLATE/` uses YAML form templates (`bug.yml`, `feature.yml`, `docs.yml`, `config.yml`); `blank_issues_enabled: false` with contact_links to docs site and security policy. Do not reintroduce Markdown issue templates.
- `CHANGELOG.md` follows Keep a Changelog 1.1.0 format with `## [Unreleased]` section and compare links at the bottom.

#### Docker And Runtime

- `Dockerfile` uses multi-stage build with `# syntax=docker/dockerfile:1.7` BuildKit pragma, non-root `app` user, full OCI labels, and `SMOKE_TEST` build arg for conditional smoke-test. `docker-compose.yml` uses named volumes (`lingchu-config`/`lingchu-data`/`lingchu-cache`) and `env_file: .env.prod`.

#### Testing And Typing

- When changing function signatures, grep all callers, update fixtures, and run Ruff, Pyright, ty, and pytest.
- After hook, adapter, or startup-flow changes, run the three-stage live smoke test (full procedure: `apps/docs/src/content/docs/developer-guide/engineering/testing-ci.mdx` → "Runtime smoke test"):
  - **Dev env**: `uvx --from nb-cli nb.exe run` loads `.env` + `.env.dev` via `ENVIRONMENT=dev`; wait for `Application startup complete.` and at least one event cycle. Catches forward-reference signature errors and import-order issues that static analysis misses.
  - **Prod env**: delete `config/nonebot_plugin_lingchu_bot/`, `data/nonebot_plugin_lingchu_bot/`, `data/nonebot_plugin_orm/`, `cache/nonebot_plugin_lingchu_bot/` (all localstore-owned), set `ENVIRONMENT=prod`, then `uvx --from nb-cli nb.exe run` loads `.env` + `.env.prod`. Verifies startup survives a clean localstore.
- Do not shadow gettext helper `_` with throwaway locals in gettext-heavy handlers.
- In tests, side-effect exceptions must match the production `except` clause.
- Use `isinstance(event, GroupMessageEvent)` for NoneBot event narrowing.
- Mock adapter return shapes according to the real API shape.
- `assert_called_once_with()` is exact; for optional kwargs, assert presence through `mock.call_args.kwargs`.
- SubAgents spawn scratch files (`_tmp_cov.sh`, `_writetest.txt`, probe scripts) and never self-clean. The orchestrator MUST run `git status --short` after SubAgent batches and `rm -f` any scratch file before staging or commit, otherwise pre-commit hooks fail on unintended files and the commit carries garbage.
- When overriding `list.__getitem__` in tests, match the typeshed signature: `def __getitem__(self, index: SupportsIndex | slice, /) -> list[object]`. Using `int | slice` or omitting the `/` triggers `reportIncompatibleMethodOverride`. Override `BaseException.args` is brittle (signature mismatch with the read-write property); prefer `__getattribute__` interception for hostile-args tests.
- Pytest fixtures using `yield` MUST declare return type `collections.abc.Iterator[None]` (or `Generator[None, None, None]`), never `-> None`. Pyright in strict mode flags `-> None` on generator functions as a return-type error and the husky pre-commit Phase 4 hook blocks the commit.

#### Monorepo Task Orchestration

- Turborepo owns task scheduling: root tasks (`//#py:*` / `//#md:*` / `//#js:*` / `//#wheel-smoke`, scripts in root `package.json`) wrap the Python toolchain; Taskfile `check` / `test` / `build` / `format` / `fix` / `ci:*` are single-line `pnpm turbo run ...` delegations. release / version / db / hooks / smoke / gitmoji / clean:dev-data stay in Taskfile (GITHUB_OUTPUT, secrets, CLI arg passthrough don't fit turbo).
- Turbo custom `inputs` globs do NOT respect `.gitignore` (package-level default inputs do). Root-task inputs MUST explicitly exclude `__pycache__` / `.ruff_cache` / `.pytest_cache` / `dist` / `test-results` / `htmlcov`, or cache-dir writes change the hash and destroy cache hits.
- Turbo strict env mode: env vars a task needs (e.g. `SQLALCHEMY_DATABASE_URL` for `//#py:test`) MUST be declared in the task's `env` list to reach the script and join the cache hash; `UV_*` and Windows toolchain paths live in `globalPassThroughEnv`.
- `task test` does not forward CLI args through turbo; use `task py:test -- -k <name>` for targeted root pytest runs.
- python.yml's 8-engine tests matrix intentionally runs pytest / pyright / ty directly (per-engine env matrix — pnpm/turbo overhead outweighs cache gains); every other CI surface enters via `task ci:*` and inherits turbo automatically.

#### Docs Site And Frontend

- `eslint-plugin-react@7.x` is incompatible with ESLint 10; pin ESLint 9 or migrate to `@eslint-react/eslint-plugin`.
- `apps/docs` uses Astro/Starlight-aware lint and type checks. Keep MDX lint scoped to docs content, keep `.astro` files covered by the docs lint script, and let `astro check` validate Starlight content collections before build. Dual markdown linter policy remains: `markdownlint-cli2` covers `.md`; docs ESLint/MDX tooling covers `.mdx` (no overlap).
- MDX table cells cannot contain raw `|` inside inline code like `<群号|群名称>`; use wording such as `<群号或群名称>`.
- Starlight root-locale pages publish without `/en/`; use root-relative internal links that match the generated Astro routes.
- Mock Starlight/Astro content collection imports in Vitest tests that touch docs routing helpers.
- Extract shared functions from component files when tests need to import them.
- Utility exports from component files can break React Fast Refresh; move them to non-component modules.
- Starlight/Pagefind search output is generated during the docs build; CI smoke tests must serve `apps/docs/dist`.
- Docker services must not bind Playwright webServer port `3100`; use ports outside the CI range such as `6100:3000`.
- `docs:check-types` should run Astro/Starlight type validation directly; do not reintroduce legacy docs generation or framework typegen steps.
- Pre-commit hook Phase 6d (Playwright Chromium smoke test) checks for browser binaries in `~/.cache/ms-playwright` before running. If Chromium is not installed, it skips with a warning instead of blocking the commit. Run `pnpm --filter docs exec playwright install` to install browsers.

#### Database And Runtime Files

- All data access goes through `nonebot_plugin_orm` and `database/orm_crud/`; do not reintroduce custom engine management.
- Package conversions need explicit `__init__.py` re-exports.
- Alembic model packages must import all models so discovery works.
- Run migrations before non-SQLite tests.
- `ensure_toml_dict_file_async()` only creates missing files; use `write_toml_dict_file_async()` to overwrite.
- Migration authoring: `nb orm revision -m "msg" --branch-label nonebot_plugin_lingchu_bot` autogenerates by default (no `--autogenerate` flag). Taskfile aliases: `task db:revision -- MSG="..."`, `task db:check`, `task db:upgrade`. Autogenerate emits `sa.Boolean` / `sa.DateTime(timezone=True)` / `sa.Text` / `sa.String` — manually rewrite to `CompatBoolean` / `CompatDateTimeTZ` / `CompatText` / `compat_string(length)` from `database/_dialect_compat.py` for cross-dialect compatibility. Autogenerate cannot detect column/table renames (emits drop+add, loses data) — author rename migrations manually with `op.alter_column`. CI runs `nb orm check` after `nb orm upgrade` to enforce model/migration sync. Without --branch-label the file lands in ./migrations/versions/ instead of the plugin migrations dir.
- `nb orm upgrade` is unreliable on local dev DBs created outside the migration system (e.g., via `Base.metadata.create_all()` or earlier direct table creation). The alembic version table has no initial migration record, so `nb orm upgrade` re-runs the initial schema and fails with `sqlite3.OperationalError: table lingchu_message_records already exists`. Always hand-write migration scripts on model definition changes (autogenerate is a starting point only, not a finish line). If the local dev DB already has tables but no migration history, use `nb orm stamp head` to mark it as current instead of re-running migrations; or delete the DB file and run `nb orm upgrade` from scratch.

#### Cross-Database Compatibility

- `database/_dialect_compat.py` provides `CompatBoolean`, `CompatDateTimeTZ`, `CompatText`, and `compat_string(length)` as cross-dialect types; ORM models MUST use these helpers instead of raw `String` / `Text` / `Boolean` / `DateTime(timezone=True)`.
- `CompatDateTimeTZ` on MySQL / MariaDB is compiled to `DATETIME(6)` and emits a "timezone only supported in MySQL 5.6+" warning; writes use `datetime.now(UTC)` (`utc_now()` in `database/models/message.py`) so no drift occurs in practice.
- `CompatBoolean` maps to native `BOOLEAN` on all four backends; no application-side variant is required.
- `CompatText` maps to `TEXT` on SQLite / PostgreSQL and `LONGTEXT` on MySQL / MariaDB for unlimited-length text.
- `compat_string(length)` compiles to `VARCHAR(length)` on all four backends; all current `String` columns in this repo are ≤ 128, so they remain as `VARCHAR(N)`.
- `orm_crud/_bulk.py::upsert` supports four backends: SQLite / PostgreSQL use `sqlite_insert` / `postgresql_insert` with `on_conflict_do_update`; MySQL / MariaDB share the `mysql_insert` + `on_duplicate_key_update` path (the `mariadb` official driver stays on the `mysql` dialect in SQLAlchemy, but `dialect.name == "mariadb"`).
- MariaDB 与 MySQL 使用统一驱动 `aiomysql`；SQLAlchemy 通过连接字符串自动检测 dialect（`mysql` vs `mariadb`），无需专用 `mariadb` Python 驱动。移除专用驱动可简化依赖并避免 CI 静态分析环境的系统库问题（`mariadb` 驱动依赖系统级 MariaDB Connector/C，在极简 CI 环境可能构建失败）。
- The CI matrix runs 8 jobs across 4 engines with `fail-fast: false` (SQLite + PostgreSQL 16/18 + MySQL 8.4/9.7 LTS + MariaDB 11.4/11.8 LTS); a full matrix run typically finishes well within normal CI budgets. Matrix entries carry an `engine` + `image` field; service containers select their image via `${{ matrix.db.engine == '<engine>' && matrix.db.image || '' }}` so multiple versions of the same engine can coexist in one matrix.

#### Actions DRY Refactor

- **Composite action catalog**: Five reusable composite actions live under `.github/actions/<name>/action.yml` — `checkout`, `setup-node-pnpm`, `setup-uv-task`, `setup-toolchain` (which composes the first three), `verify-wheel`, and `attest-slsa`. New workflows MUST consume them via `uses: ./.github/actions/<name>` rather than re-declaring `actions/checkout`, `actions/setup-node`, `pnpm/action-setup`, `astral-sh/setup-uv`, `go-task/setup-task`, or inline `actions/attest-build-provenance` steps. Inputs (`fetch-depth`, `node-version`, `python-version`, `with-retry`, `subject-path`) cover every prior call site; add a new input only when a previously-impossible parameter is required.
- **Centralized bump derivation**: `task ci:version:derive-bump` (delegating to `scripts/ci_derive_bump.py`) is the single source of truth for `BUMP_LEVEL` + `BUMP_PRERELEASE`. `ci-builds.yml::versioned-build`, `release.yml::validate`, `task release:prepare`, and `task release:notes` all call it instead of maintaining their own `case` mappings. Branch-name conventions are encoded in one regex set, so adding a new dev- or release-bump flavor is a one-line change.
- **SHA upgrade cost reduction**: Before the DRY refactor, upgrading `actions/checkout` SHA meant editing 37 workflow files. After the refactor, the same upgrade is a single edit in `.github/actions/checkout/action.yml`; downstream workflows inherit it automatically. The composite action boundary is the new "pin surface" — keep the 40-char SHA + `# vX.Y.Z` comment convention on the `uses:` line inside the composite action, never on the consumer.
- **Inline code off-YAML**: Wheel verification, SLSA attestation setup, and bump derivation used to live as 12-line `run:` blocks embedded in three workflows each. They are now `scripts/ci_verify_wheel.py`, `.github/actions/attest-slsa`, and `scripts/ci_derive_bump.py` respectively. New workflow steps that exceed ~5 lines of logic SHOULD be extracted to `scripts/` and invoked through a thin composite action or `run:` step.
- **Filename de-emoji**: `git mv` was used to rename 10 workflows (e.g. `🚀-release.yml` → `release.yml`). `git log --follow <new-name>` preserves history across the rename. When adding a new workflow, the file MUST NOT have a leading emoji in its name; the emoji belongs in the `name:` field only.

#### Hooks, CI, And GitHub

- Bash hooks on Windows may find `.cmd` shims that are not directly runnable. Launch Windows Node shims through `cmd.exe /c`.
- Do not suppress `git diff --cached` failures in hooks.
- Use CLI auto-fix tools before manual mechanical edits: Ruff fix/format, markdownlint `--fix`, ESLint `--fix`, Prek.
- Markdownlint config is centralized in `.markdownlint-cli2.jsonc`; invocation sites should rely on that config.
- For PowerShell markdownlint, prefer `pwsh.exe -NoProfile` and avoid ad hoc quoted globs.
- Pin GitHub Actions by commit SHA, not annotated tag object SHA.
- Workflow filenames use plain kebab-case (no leading emoji); the `name:` field still uses English with matching emoji so the Actions UI can group them visually. Updating the `name:` emoji does NOT require renaming the file.
- `.github` YAML comments should be English; remove broken empty schema comments.
- Check remote branch existence with `git ls-remote` before `git push origin --delete`.
- CI workflows are split by domain: `python.yml` (Python static analysis + multi-DB test matrix + auto-format), `frontend.yml` (docs lint/type/test/links), `docs.yml` (docs deploy), `ci-builds.yml` (version bump + build artifacts + SLSA provenance), `release.yml` (PyPI/GHCR publish), `clear-workflow.yml` (manual dispatch; deletes non-running workflow runs via `actions: write`), `issues-top.yml` (scheduled daily; labels and displays top issues), `stale.yml` (scheduled daily; marks and closes stale issues after 14+7 days of inactivity), `react-doctor.yml` (PR/push on `.tsx` changes; runs React Doctor CLI directly — see Pending Rollbacks), `playwright.yml` (PR/push on `apps/docs` changes; Playwright E2E with browser cache). Shared change detection lives in the `.github/actions/detect-changes` composite action (outputs python/markdown/frontend-* flags). Shared setup logic lives in the `.github/actions/{checkout,setup-node-pnpm,setup-uv-task,setup-toolchain,verify-wheel,attest-slsa}` composite actions so each workflow only needs to declare its `uses:` references. Standard trigger convention: PR runs checks only (no commits/deploy); push to `main`/`dev` runs checks + auto-format + deploy. Each workflow has its own concurrency group to avoid cross-canceling. Workflow filenames no longer carry leading emoji prefixes (the `name:` field still does) so cross-platform file systems and CLI tab-completion stay predictable.
- CircleCI dual-line watchdog: `.circleci/config.yml` (setup pipeline; hourly fallback via a project-level Schedule Trigger, since `triggers: schedule` is unsupported in setup configs) runs a `preflight` job that sleeps 15s to give GitHub Actions a startup window, queries the head commit's `actions/runs` via `scripts/ci_gh_preflight.py`, and only continues with the full `.circleci/checks.yml` (mirrors python.yml static-analysis + 7-cell DB test matrix + frontend.yml docs checks) when GitHub Actions is entirely failed/absent; a healthy GH (queued/in_progress/success/skipped) continues as a no-op. Missing `GITHUB_TOKEN` (manual Project Settings env var, `actions: read` only) or GitHub API errors fail open to the full checks; fork PRs carry no secrets and fail open. Build/release/deploy remain GitHub Actions only. CircleCI has no cancel-in-progress equivalent.
- Codecov coverage uploads come from the SQLite cell only (one representative report per commit): GH uses `codecov/codecov-action@v7.0.0` (SHA-pinned) in the python.yml tests job; CircleCI uses the `codecov/codecov@6.0.0` orb on the tests-sqlite job. Secret `CODECOV_TOKEN` lives as a GitHub repo secret and a CircleCI project env var. Codecov's own numbers may differ slightly from pytest's `--cov-fail-under` gate because of report processing.
- Static Analysis jobs in Python CI use `uv sync --no-dev --group lint --group git --frozen` + `UV_NO_SYNC=1` to install only the minimal dependencies needed for linting/formatting (ruff, pyright, ty, prek), avoiding the test group which contains database drivers (e.g. the `mariadb` package) that require system-level libraries and can fail to build in minimal CI environments. Use this pattern for any CI job that doesn't need to run tests.

#### Pending Rollbacks

| What | Where | Why | Rollback condition |
| --- | --- | --- | --- |
| `deslop/unused-export: "off"` | `doctor.config.ts` | `useMDXComponents` is a framework-required re-export but currently unused | Remove after `useMDXComponents` is consumed |
| React Doctor CLI instead of action | `.github/workflows/react-doctor.yml` | Upstream action bugs: detached HEAD and ANSI leak | Switch back after upstream releases a fix |
