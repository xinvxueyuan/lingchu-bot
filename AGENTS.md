<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **lingchu-bot** (6691 symbols, 12358 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
| T | Tools | Commands, skills, MCPs, hooks, and validation routes |
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

Lingchu Bot is a NoneBot2-based group management bot. The monorepo contains:

- Python backend plugin: `src/plugins/nonebot_plugin_lingchu_bot/`
- Next.js documentation site: `apps/docs/`
- Project-local skills (single source of truth): `.agents/skills/`
  - `.claude/skills/` and `.trae/skills/` are **whole-directory symlinks** to `.agents/skills/`, so Codex, Trae, and Claude Code all read from the same set; add or update a skill in `.agents/skills/` and all three agents see it.
- Chinese agent guide mirror: `.github/note/AGENTS-zh.md`
- Claude Code guide mirror: `CLAUDE.md`

Anything required for build or package distribution must live under `src/plugins/nonebot_plugin_lingchu_bot/`. Repository-root runtime/config files such as `config/` and `data/` are local development artifacts and disposable.

Do not maintain a hand-written full repository tree in this file. Use `rg --files`, GitNexus, or docs under `apps/docs/content/docs/developer-guide/` for current structure.

## Tech Stack

Python backend:

- Python 3.13, managed by `uv`
- NoneBot2 with OneBot V11 adapter; Milky, QQ, and OneBot V12 are deprecated and removed
- `nonebot-plugin-alconna` for command parsing
- `nonebot-plugin-orm` with `aiosqlite` for async database access
- `nonebot-plugin-localstore` for mutable data, config, cache, resource, and schema paths
- Ruff, Pyright, ty, pytest

Docs site:

- Next.js 16, Fumadocs 16 static export, React 19, Tailwind CSS 4, TypeScript 6
- Vitest, Testing Library, ESLint, Playwright
- i18n, RSS, Mermaid, Twoslash, EPUB export, `/llms.txt`, `/llms-full.txt`, document graph
- All server components, route handlers, and lib functions are async
- Turborepo workspace using `pnpm`

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
- **No packaged schema resources**: Do not use `importlib.resources` or wheel data for JSON schemas. Schema text lives in `src/plugins/nonebot_plugin_lingchu_bot/core/schemas.py` and is installed by `install_schemas()`.
- **Handle default registration**: Handle-level defaults MUST be registered in `handle_config_defaults/` using `register_handle_defaults()` before `HandleConfigManager` can read or update `<command_key>.toml` files.
- **Prek is hook source of truth**: `prek.toml` is the only pre-commit hook configuration (explicitly declares ruff/ty hooks, decoupled from husky, no duplicate execution). Do not reintroduce `.pre-commit-config.yaml`.
- **Version sync**: Use `Taskfile.yml` task `ci:version:write-config` to write both `src/plugins/nonebot_plugin_lingchu_bot/core/config.py` and root `package.json`.
- **Release branches**: Formal releases use `releases/<version>` branches and must keep `pyproject.toml`, `package.json`, and `core/config.py` versions synchronized before publishing.
- **Release notes**: Every formal release updates `CHANGELOG.md` and the release policy record.
- **Release publishing**: PyPI uses Trusted Publishing / OIDC; GHCR uses `GITHUB_TOKEN` with `packages: write`; do not add long-lived package tokens.
- **Skills exclusion sync**: When changing skills exclusion patterns in `pyproject.toml`, sync the corresponding `prek.toml` comments/patterns.
- **REUSE compliance**: All files MUST have SPDX license declarations via `REUSE.toml`; `reuse lint` MUST pass before commit. New files MUST be covered by `REUSE.toml` globs or have inline `SPDX-License-Identifier` headers.
- **Docker build context**: `.dockerignore` MUST exclude `.git`, `.venv`, `node_modules`, `.env*` (except `.env.example`/`.env.prod.example`), `tests/`, `.github/`, `.trae/`, `.gitnexus/`, `.turbo/`, and cache directories before `docker build`.
- **CODEOWNERS**: `.github/CODEOWNERS` routes `src/`, `apps/docs/`, `.github/`, `Dockerfile`, `docker-compose.yml`, `Taskfile.yml`, `pyproject.toml`, `package.json`, `REUSE.toml`, `LICENSE-*` to `@xinvxueyuan` for auto-review.

### Code Style

The project enforces a unified code style across Python and frontend workspaces:

- **`.editorconfig`**: Root-level editor baseline. Python uses 4-space indent; JS/TS/CSS/MD/YAML/TOML/JSON use 2-space. LF line endings, UTF-8, final newline, trimmed trailing whitespace for all text files.
- **Python formatting**: `ruff format` (line-length 88, LF, double quotes). No Black or isort — Ruff replaces both.
- **Python docstrings**: Ruff `D` (pydocstyle) rule family with `convention = "google"`. Missing-docstring rules (`D100`–`D103`) are globally ignored due to the existing codebase size; D rules still enforce style on EXISTING docstrings. Tests have per-file D ignores.
- **Python linting**: Ruff with rule families F, W, E, I, C90, N, PL, UP, YTT, ANN, ASYNC, BLE, FBT, B, A, COM, C4, D, DTZ, T10, ICN, PIE, T20, PYI, Q, RSE, RET, SIM, SLOT, TID, TC, ARG, PTH, FAST, PERF, PGH, FURB, TRY, RUF.
- **Python type checking**: Pyright `standard` mode + ty (Astral, fast feedback). Both run in CI.
- **Frontend formatting**: Prettier (`.prettierrc.json`) for JS/TS/TSX/CSS/JSON. Markdown files are excluded — `markdownlint-cli2` owns `.md`, `eslint-plugin-mdx` owns `.mdx` (dual-linter policy).
- **Frontend linting**: ESLint 10 flat config. `apps/docs` uses `eslint-config-next/core-web-vitals` + `eslint-config-next/typescript` + `eslint-plugin-mdx`. `eslint-config-prettier` is appended last to disable formatting rules that conflict with Prettier.
- **TypeScript**: TS 6 with `strict: true`, `target: ES2025`, `module: ESNext`, `moduleResolution: Bundler` (in `packages/typescript-config/base.json`).
- **Tool versions**: ruff>=0.15.21, pyright>=1.1.410, ty>=0.0.58, prek>=0.4.4, ESLint 10.x, TypeScript 6.x.
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

- Docs route handlers, server components, `baseOptions()`, `buildGraph()`, and `getRSS()` return Promises.
- Docs i18n uses `hideLocale: 'default-locale'`; default English URLs omit `/en/`.
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
| Docs | `apps/docs/content/docs/` |
| Menu | `src/plugins/nonebot_plugin_lingchu_bot/handle/menu.py` |
| Runtime config | `config.toml`, `bot_state.toml`, `menu.toml`, schema text in `core/schemas.py` |
| Handle config files | `handle_config_defaults/`, `<command_key>.toml` in localstore config_dir |
| Triggers | `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/commands/triggers.py` |
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
- `install_schemas()` must run before runtime TOML files reference schema basenames. Its failure is logged and non-fatal.

### Repository API Style

- Use frozen dataclass request objects for write/audit APIs with coupled fields.
- Use `CommandAudit` for command audit payloads, then call `record_audit_fire_and_forget()` or `record_command_audit()`.
- Do not add long parameter lists for platform, adapter, bot, group, target, reason, and duration; create a request object.
- Use `fire_and_forget(coro, *, name="...")` only for discardable background work whose result is not needed by the caller.

## T — Tools

### Skills And MCPs

| Need | Route |
| --- | --- |
| Plan/domain: grill a plan against codebase, build CONTEXT.md + ADRs | `grill-with-docs` skill |
| Plan/domain: sharpen domain language and terminology | `domain-modeling` skill |
| Plan/domain: lighter pressure-test without docs artifacts | `grilling` / `grill-me` skill |
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
| OneBot V11 / NapCat API signatures | NapCat API MCP before writing adapter calls |
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

Lighter alternatives: `grilling` / `grill-me` replace `grill-with-docs` + `domain-modeling` when you only need a pressure-test without docs artifacts.

### Development Commands

Python:

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
pnpm --filter docs run test:e2e:hook
pnpm --filter docs run test:e2e
pnpm turbo run check-types
pnpm --filter docs exec tsc --noEmit
pnpm --filter docs dev
pnpm turbo run build --filter=docs
```

Project:

```bash
pnpm exec markdownlint-cli2
pnpm exec markdownlint-cli2 --fix
task i18n
task check
task test
task ci
```

### Quick Verification Matrix

| Changed | Minimum checks before commit |
| --- | --- |
| Python source only | Ruff check + Ruff format check + Pyright strict + ty strict (`uv run -m ty check --output-format github`) + relevant pytest |
| Docs site only | `pnpm --filter docs lint` (covers `.ts/.tsx/.mdx` via ESLint flat config + eslint-plugin-mdx; type-aware rules via `projectService`) + docs tests + Playwright hook smoke + docs type check + link lint when content changes |
| Markdown only | `pnpm exec markdownlint-cli2` |
| i18n strings | `task i18n` + relevant pytest |
| Infrastructure config | `docker compose config` + `prek run --all-files` + `task ci:typecheck` |
| Mixed / uncertain | `task check && task test` |

Prefer granular checks during development. Full `task check && task test` is for pre-commit or broad verification.

### Git Hooks

- Pre-commit runs Prek auto-fix, markdownlint, Ruff, Pyright, ty, pytest, docs lint/type/test/e2e smoke, React Doctor for `.tsx`, and non-blocking GitNexus analysis based on changed file classes.
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
- Module-level `# pyright: reportMissingImports=false` in `services/llm.py` is the only legitimate inline type-ignore directive, used for optional `openai`/`litellm` dependency imports.

#### Adapter And API Boundaries

- Same-named adapter APIs can return different shapes. OneBot V11 APIs often return `dict`; inspect installed adapter source before writing access patterns.
- Deprecated Milky, QQ, and OneBot V12 source has been fully removed from the project, including any on-demand loading utility.
- OneBot V11 group `event.get_session_id()` can include both group and user IDs. Group-scoped history must use `group_id` as `conversation_id`.
- For OneBot V11 image APIs, verify file field format against current adapter and NapCat docs before changing calls.
- WSL2 + Docker Desktop bind mount requires the WSL distro root to be in Docker Desktop's File Sharing allow-list. When it is missing, the container sees an empty directory at the bind target while `docker inspect` still reports the source path. Detect with `docker exec <ctr> mount | grep <src>`: a `fuse.bind` or plain `bind` line is correct; `overlay` (lower=`/tmp/docker-desktop-root-ro`) means the bridge returned an empty view. Fix by adding `\\wsl.localhost\<distro>\` (or `\\wsl$\<distro>\` on older WSL) under Docker Desktop → Settings → Resources → File sharing, then **Apply & restart** and recreate the container. The Windows-side `docker` daemon does not see WSL paths through plain bind; do not assume the integration is "already on" — WSL Integration and File Sharing are two distinct settings.

#### Supply Chain

- All third-party GitHub Actions in `.github/workflows/*.yml` are pinned by 40-char commit SHA with `# vX.Y.Z` comments (not mutable tags). `👷-ci-builds.yml` and `🚀-release.yml` both use `actions/attest-build-provenance@v4.1.0` (SHA `a2bbfa2…`) for SLSA Build L3 provenance. Verify with `gh attestation verify <artifact> --repository xinvxueyuan/lingchu-bot`.
- Version validation system: branch name conventions (`dev-minor-*`/`dev-major-*`/`dev-alpha-*`/`dev-beta-*`/`dev-rc-*`/`dev-stable-*`) drive `BUMP_LEVEL`/`BUMP_PRERELEASE` in `ci:version:bump`. `ci:version:precheck` validates PEP 440 + greater-than-all-tags + source consistency + no-duplicate-tag. `ci:version:postcheck` calls `release:verify-version` + dev release semantics. The smart bump strategy handles stable vs pre-release tags: stable tags need level+prerelease, same-type pre-release tags just bump prerelease, `stable` clears prerelease.
- `.github/ISSUE_TEMPLATE/` uses YAML form templates (`bug.yml`, `feature.yml`, `docs.yml`, `config.yml`); `blank_issues_enabled: false` with contact_links to docs site and security policy. Do not reintroduce Markdown issue templates.
- `CHANGELOG.md` follows Keep a Changelog 1.1.0 format with `## [Unreleased]` section and compare links at the bottom.

#### Docker And Runtime

- `Dockerfile` uses multi-stage build with `# syntax=docker/dockerfile:1.7` BuildKit pragma, non-root `app` user, full OCI labels, and `SMOKE_TEST` build arg for conditional smoke-test. `docker-compose.yml` uses named volumes (`lingchu-config`/`lingchu-data`/`lingchu-cache`) and `env_file: .env.prod`.

#### Testing And Typing

- When changing function signatures, grep all callers, update fixtures, and run Ruff, Pyright, ty, and pytest.
- After hook, adapter, or startup-flow changes, run a short live smoke test with `timeout 10s nb run -r` (adjust the timeout based on startup output; wait until `Application startup complete.` and at least one event cycle are observed). This catches forward-reference signature errors and import-order issues that static analysis misses.
- Do not shadow gettext helper `_` with throwaway locals in gettext-heavy handlers.
- In tests, side-effect exceptions must match the production `except` clause.
- Use `isinstance(event, GroupMessageEvent)` for NoneBot event narrowing.
- Mock adapter return shapes according to the real API shape.
- `assert_called_once_with()` is exact; for optional kwargs, assert presence through `mock.call_args.kwargs`.

#### Docs Site And Frontend

- `eslint-plugin-react@7.x` is incompatible with ESLint 10; pin ESLint 9 or migrate to `@eslint-react/eslint-plugin`.
- `eslint-plugin-mdx@3.8.1` integrates MDX lint into `apps/docs/eslint.config.mjs` with three layers: `mdx.flat` (parser + `mdx/*` rules), `mdx.createRemarkProcessor({ lintCodeBlocks: true })` (code-block lint), and `mdx.flatCodeBlocks` (code-block rules). `peerDependencies: { eslint: ">=8.0.0" }` is compatible with ESLint 10. Code-block rules MUST turn off all `react/*` and `@next/*` rules (scoped via `files: ['**/*.{md,mdx}/**']`) to avoid `vercel/next.js#89764` `TypeError: contextOrFilename.getFilename is not a function` crashes on virtual files. `.remarkrc.json` MUST list `remark-frontmatter` BEFORE lint presets, otherwise frontmatter `---` delimiters are misparsed as setext H2 underlines, producing `remark-lint-heading-style` false positives (306 baseline warnings, all resolved by adding `remark-frontmatter`). Dual markdown linter policy: `markdownlint-cli2` covers `.md`; `eslint-plugin-mdx` covers `.mdx` (no overlap). Pre-commit hook uses a dedicated `HAS_DOCS_MDX` flag (matched via `^apps/docs/.*\.mdx$`) and CI uses a dedicated `frontend-mdx` output flag, both scoped to avoid spurious ESLint triggers on `.json` content changes.
- MDX table cells cannot contain raw `|` inside inline code like `<群号|群名称>`; use wording such as `<群号或群名称>`.
- Fumadocs link validation needs absolute URLs from root index pages.
- Mock `collections/server` in Vitest tests that import `src/lib/source.ts`.
- Extract shared functions from component files when tests need to import them.
- Utility exports from component files can break React Fast Refresh; move them to non-component modules.
- `/llms.txt` is a route handler; link internally with Next.js `Link`.
- Docker services must not bind Playwright webServer port `3100`; use ports outside the CI range such as `6100:3000`.
- `next typegen` may clear `apps/docs/.source/server.ts` (and `browser.ts`) to 0 bytes after the first `fumadocs-mdx` call. The `docs:check-types` script MUST run `fumadocs-mdx` a second time after `next typegen` to repopulate the collections exports, otherwise `tsc --noEmit` fails with `TS2305: Module '"collections/server"' has no exported member 'docs'`. Use `fumadocs-mdx && next typegen && fumadocs-mdx && tsc --noEmit`.
- Pre-commit hook Phase 6d (Playwright Chromium smoke test) checks for browser binaries in `~/.cache/ms-playwright` before running. If Chromium is not installed, it skips with a warning instead of blocking the commit. Run `pnpm --filter docs exec playwright install` to install browsers.

#### Database And Runtime Files

- All data access goes through `nonebot_plugin_orm` and `database/orm_crud/`; do not reintroduce custom engine management.
- Package conversions need explicit `__init__.py` re-exports.
- Alembic model packages must import all models so discovery works.
- Run migrations before non-SQLite tests.
- `ensure_toml_dict_file_async()` only creates missing files; use `write_toml_dict_file_async()` to overwrite.
- Runtime config defaults must be JSON-serializable; dump Pydantic defaults with `mode="json"` when needed.

#### Cross-Database Compatibility (added with MariaDB / Oracle / SQL Server support)

- `database/_dialect_compat.py` provides `CompatBoolean`, `CompatDateTimeTZ`, `CompatText`, and `compat_string(length)` as cross-dialect types; ORM models MUST use these helpers instead of raw `String` / `Text` / `Boolean` / `DateTime(timezone=True)`.
- `CompatDateTimeTZ` on MySQL / MariaDB is compiled to `DATETIME(6)` and emits a "timezone only supported in MySQL 5.6+" warning; writes use `datetime.now(UTC)` (`utc_now()` in `database/models/message.py`) so no drift occurs in practice.
- `CompatBoolean` maps to `NUMBER(1)` on Oracle pre-23c and native `BOOLEAN` on 23c+; no application-side variant is required.
- `CompatText` maps to `CLOB` on Oracle to avoid `VARCHAR2(4000)` truncation.
- `compat_string(length)` only switches to `NVARCHAR(MAX)` on SQL Server for `length > 4000`; all current `String` columns in this repo are ≤ 128, so they remain as `VARCHAR(N)` on every backend.
- `orm_crud/_bulk.py::upsert` supports six backends: SQLite / PostgreSQL use `sqlite_insert` / `postgresql_insert` with `on_conflict_do_update`; MySQL / MariaDB share the `mysql_insert` + `on_duplicate_key_update` path (the `mariadb` official driver stays on the `mysql` dialect in SQLAlchemy 2.0.51, but `dialect.name == "mariadb"`); Oracle / SQL Server go through `_oracle_upsert` / `_mssql_upsert` private helpers that hand-write a `MERGE INTO` statement via `sqlalchemy.text()` with named bind parameters.
- **Oracle / SQL Server upsert verified fact**: `from sqlalchemy.dialects.{oracle,mssql} import insert` raises `ImportError: cannot import name 'insert'`; the generic `from sqlalchemy import insert` returns an `Insert` object that has **no** `on_conflict_do_update` method; `oracle/base.py` and `mssql/base.py` have no `MERGE INTO` / `visit_insert` compilation logic. Re-evaluate if SQLAlchemy is upgraded to ≥ 2.1 (which adds `mssql.insert` / `oracle.insert`).
- Oracle `MERGE INTO` uses `USING (SELECT :p1 AS c1, :p2 AS c2 FROM DUAL) s`; SQL Server uses `USING (SELECT :p1 AS c1, :p2 AS c2) s` (no `FROM DUAL`). Both execute the MERGE then follow up with a `SELECT ... WHERE conflict_keys` because neither backend supports `INSERT ... RETURNING`.
- Oracle 12.2 (2016-12) is the minimum version; all current table / constraint names are within the 128-char limit, so no renames were needed. Do not extend identifier names past 30 characters without verifying the deployment target.
- MariaDB 与 MySQL 使用统一驱动 `aiomysql`；SQLAlchemy 通过连接字符串自动检测 dialect（`mysql` vs `mariadb`），无需专用 `mariadb` Python 驱动。移除专用驱动可简化依赖并避免 CI 静态分析环境的系统库问题（`mariadb` 驱动依赖系统级 MariaDB Connector/C，在极简 CI 环境可能构建失败）。
- `oracledb` 2.0+ uses Thin mode by default, so no Oracle Instant Client is required in CI.
- `aioodbc` (and its `pyodbc` transitive dependency) needs the system ODBC Driver 18 package on Linux CI (`ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18 unixodbc-dev`); macOS uses brew; Windows is built-in.
- The CI matrix runs 10 jobs across 6 engines with `fail-fast: false` (SQLite + PostgreSQL 16/18 + MySQL 8.4/9.7 LTS + MariaDB 11.4/11.8 LTS + Oracle 23ai + SQL Server 2022/2025); Oracle / SQL Server startup is slow (health-start-period 90-180s), and a full matrix run takes 8-15 minutes, so plan timing budgets accordingly. SQL Server migrated off the deprecated `azure-sql-edge` image to `mcr.microsoft.com/mssql/server:{2022,2025}-latest` (both ship `mssql-tools18` for the healthcheck). Matrix entries carry an `engine` + `image` field; service containers select their image via `${{ matrix.db.engine == '<engine>' && matrix.db.image || '' }}` so multiple versions of the same engine can coexist in one matrix.

#### Hooks, CI, And GitHub

- Bash hooks on Windows may find `.cmd` shims that are not directly runnable. Launch Windows Node shims through `cmd.exe /c`.
- Do not suppress `git diff --cached` failures in hooks.
- Use CLI auto-fix tools before manual mechanical edits: Ruff fix/format, markdownlint `--fix`, ESLint `--fix`, Prek.
- Markdownlint config is centralized in `.markdownlint-cli2.jsonc`; invocation sites should rely on that config.
- For PowerShell markdownlint, prefer `pwsh.exe -NoProfile` and avoid ad hoc quoted globs.
- Pin GitHub Actions by commit SHA, not annotated tag object SHA.
- Workflow filenames use emoji-prefix + kebab-case, and workflow `name:` uses English with matching emoji.
- `.github` YAML comments should be English; remove broken empty schema comments.
- Check remote branch existence with `git ls-remote` before `git push origin --delete`.
- CI workflows are split by domain: `🧪-python.yml` (Python static analysis + multi-DB test matrix + auto-format), `🧪-frontend.yml` (docs lint/type/test/links), `📚-docs.yml` (docs deploy), `👷-ci-builds.yml` (version bump + build artifacts + SLSA provenance), `🚀-release.yml` (PyPI/GHCR publish), `🧹-clear-workflow.yml` (manual dispatch; deletes non-running workflow runs via `actions: write`), `🏷️-issues-top.yml` (scheduled daily; labels and displays top issues), `🩺-react-doctor.yml` (PR/push on `.tsx` changes; runs React Doctor CLI directly — see Pending Rollbacks), `🎭-playwright.yml` (PR/push on `apps/docs` changes; Playwright E2E with browser cache). Shared change detection lives in the `.github/actions/detect-changes` composite action (outputs python/markdown/frontend-* flags). Standard trigger convention: PR runs checks only (no commits/deploy); push to `main`/`dev` runs checks + auto-format + deploy. Each workflow has its own concurrency group to avoid cross-canceling.
- Static Analysis jobs in Python CI use `uv sync --no-dev --group lint --group git --frozen` + `UV_NO_SYNC=1` to install only the minimal dependencies needed for linting/formatting (ruff, pyright, ty, prek), avoiding the test group which contains database drivers (mariadb, aioodbc) that require system-level libraries and can fail to build in minimal CI environments. Use this pattern for any CI job that doesn't need to run tests.

#### Pending Rollbacks

| What | Where | Why | Rollback condition |
| --- | --- | --- | --- |
| `deslop/unused-export: "off"` | `doctor.config.ts` | `useMDXComponents` is a framework-required re-export but currently unused | Remove after `useMDXComponents` is consumed |
| React Doctor CLI instead of action | `.github/workflows/🩺-react-doctor.yml` | Upstream action bugs: detached HEAD and ANSI leak | Switch back after upstream releases a fix |
