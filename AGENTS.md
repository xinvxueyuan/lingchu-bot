<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **lingchu-bot** (3311 symbols, 6244 relationships, 278 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.

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

## Available Agent Skills

This repo can use the current Codex skill set when a task matches the skill trigger. Keep this section as a compact routing index; load the corresponding `SKILL.md` only when needed.

### Documentation Lookup

- **tool-workflows**: Use `.agents/skills/tool-workflows/SKILL.md` for Context7/find-docs, prek/Husky hook work, and project skill management. For current documentation, start with `resolve-library-id` unless the user provides an exact `/org/project` ID, then query docs with the full user question.
- **openai-docs**: Use for OpenAI product/API questions; prefer official OpenAI docs. (Routing-only — no local SKILL.md; loaded from Codex platform skills at runtime.)

### Code Intelligence And Git

- **engineering-workflow**: Use `.agents/skills/engineering-workflow/SKILL.md` for GitNexus architecture exploration, debugging, impact analysis, refactoring, PR review, CLI operations, delivery loops, frontend quality, design prototyping, and issue planning. Follow the GitNexus requirements above before editing symbols or committing.
- **GitHub skills**: Use for GitHub repository, issue, pull request, review-comment, CI, and publish/PR workflows.

### Development Workflow

- **engineering-workflow**: Routes disciplined debugging, TDD, code review, PRDs, issue breakdown, triage, refactor plans, interface design exploration, design grilling, and throwaway prototypes through focused references.

### Frontend And Docs Site

- **engineering-workflow**: Use its frontend-quality route for React diagnostics, visual polish, accessibility, and health checks on the docs site (`apps/docs`).
- **Browser / Playwright / Chrome**: Use Browser for local in-app browser checks, Playwright for terminal-driven browser automation, and Chrome only when existing user Chrome state is required. (Routing-only — no local SKILL.md; loaded from Codex platform skills at runtime.)
- **Vercel skills**: Use for Next.js, React best practices, shadcn/ui, AI SDK, deployments, Vercel CLI/API, storage, auth, payments, cron, routing middleware, functions, workflow, and verification tasks. (Routing-only — no local SKILL.md; loaded from Codex platform skills at runtime.)
- **Cloudflare skills**: Use for Workers, Wrangler, Durable Objects, Agents SDK, MCP servers, sandbox SDK, and Cloudflare platform work. (Routing-only — no local SKILL.md; loaded from Codex platform skills at runtime.)

### Artifacts And Media

- **Documents / Presentations / Spreadsheets / PDF**: Use for `.docx`, slide decks, spreadsheet files, and PDF tasks where rendering or file-format behavior matters. (Routing-only — no local SKILL.md; loaded from Codex platform skills at runtime.)
- **imagegen**: Use for raster image generation or edits when visuals are requested. (Routing-only — no local SKILL.md; loaded from Codex platform skills at runtime.)

### Skill Authoring

- **skill-creator**: Use when creating or updating Codex skills. Required skill folders contain `SKILL.md`; optional resources include `scripts/`, `references/`, `assets/`, and `agents/openai.yaml`.
- **skill-installer / plugin-creator**: Use when installing skills or scaffolding Codex plugins. (Routing-only — no local SKILL.md; loaded from Codex platform skills at runtime.)

Project-local skill index is available at `.agents/skills/available-skills/SKILL.md`.

# Project Context

> English | [中文](.github/note/AGENTS-zh.md)

## Overview

Lingchu Bot is a NoneBot2-based group management bot. The monorepo contains a Python backend plugin (`nonebot-plugin-lingchu-bot`) and a Next.js documentation site (`apps/docs`).

## Tech Stack

### Python Backend

- Python 3.13, managed by `uv`
- NoneBot2 with OneBot V11 adapter (Milky, QQ, OneBot V12 deprecated; available via `tools/adapter_loader.py`)
- `nonebot-plugin-alconna` for command parsing
- `nonebot-plugin-orm` (aiosqlite) for async database
- `nonebot-plugin-localstore` for file storage
- Ruff (lint + format), Pyright, ty (type check), pytest (test)

### Documentation Site (`apps/docs`)

- Next.js 16 + Fumadocs 16 (static export)
- React 19, Tailwind CSS 4, TypeScript 6
- Vitest + @testing-library/react (unit tests), ESLint (lint)
- Features: i18n (en/zh), RSS, Mermaid, Twoslash, EPUB export, LLM-friendly text (`/llms.txt`, `/llms-full.txt`), document relationship graph
- All server components, route handlers, and lib functions are async
- Turborepo workspace, pnpm package manager

## Project Structure

> See the [Project Directory Tree](#project-directory-tree) section below for the complete annotated tree with file-level descriptions. The docs site has a dedicated [Platforms](apps/docs/content/docs/platforms) section that separates documentation by platform → protocol → implementation.

## Development Commands

> Use granular commands for faster feedback during development. Only run `task check` / `task test` for full verification before commits.

### Python — Lint & Format

```bash
uv run -m ruff check . --output-format=github   # Lint only
uv run -m ruff check --fix .                     # Auto-fix lint issues
uv run -m ruff format --check .                  # Format check only
uv run -m ruff format .                          # Apply formatting
```

### Python — Type Check

```bash
uv run -m pyright .                              # Pyright type check
uv run -m ty check --output-format github        # ty type check
```

### Python — Test

```bash
uv run -m pytest                                 # All tests
uv run -m pytest tests/handle/commands/group/    # Specific test directory
uv run -m pytest -k "test_mute"                  # By keyword
uv run -m pytest --lf                            # Re-run last failures
```

### Python — Multi-Locale Testing

`tests/conftest.py` provides two parametrized fixtures and a marker for testing both `zh_CN` and `en_US` locales in a single pytest session:

| Fixture | Modifies global state? | Use when |
|---------|------------------------|----------|
| `locale` | No — returns the locale string only | Test calls gettext helpers with an explicit `locale=` argument (e.g., `gettext(msg, locale=locale)`) |
| `configured_locale` | Yes — calls `_read_configured_locale.cache_clear()` and monkeypatches it to return the parametrized locale | Test relies on `get_configured_locale()` or the `_()` shorthand (no explicit locale argument) |

- **`i18n` marker**: Registered in `pytest_configure()` via `config.addinivalue_line("markers", ...)`. Mark multi-locale tests with `@pytest.mark.i18n` so they can be selected/filtered with `-m i18n`.

**Example:**

```python
@pytest.mark.i18n
def test_gettext_explicit(locale):
    """Uses the `locale` fixture — no global state change."""
    assert gettext("禁言", locale=locale)  # pass locale explicitly


@pytest.mark.i18n
def test_configured_locale(configured_locale):
    """Uses the `configured_locale` fixture — patches the cached locale."""
    assert _("禁言")  # reads via get_configured_locale()
```

> **Why two fixtures?** `_read_configured_locale()` is decorated with `@lru_cache(maxsize=1)`, so its first return value is cached for the entire session. The `configured_locale` fixture clears that cache and monkeypatches the function so each parametrized locale takes effect. See the "Bypassing lru_cache for Multi-Locale Tests" lesson.

### Docs Site — Lint & Type Check

```bash
pnpm --filter docs lint                          # ESLint for docs site
pnpm turbo run check-types                       # TypeScript type check (all workspaces)
pnpm --filter docs exec tsc --noEmit             # TypeScript check (docs only)
```

### Docs Site — Test

```bash
pnpm --filter docs test                          # Vitest for docs site
```

### Docs Site — Dev & Build

```bash
pnpm --filter docs dev                           # Dev server
pnpm turbo run build --filter=docs               # Production build
```

### Markdown Lint

```bash
pnpm exec markdownlint-cli2 {{.MD_GLOB}}         # Check (use the MD_GLOB from Taskfile.yml)
pnpm exec markdownlint-cli2 --fix {{.MD_GLOB}}   # Auto-fix
```

### i18n

```bash
task i18n                                        # Extract + update + compile translations
```

### Task Runner — Full Verification

```bash
task check                                       # All static checks (ruff lint + format + markdown + ESLint + pyright + ty + tsc)
task test                                        # All tests (pytest + Vitest)
task ci                                          # check + test + build
```

### Quick Reference: What to Run When

| What changed | Minimum checks before commit |
|---|---|
| Python source only | `ruff check` + `ruff format --check` + `pyright` + `ty check` + `pytest` |
| Docs site only | `pnpm --filter docs lint` + `pnpm --filter docs test` + `pnpm turbo run check-types --filter=docs` + `pnpm --filter docs lint:links` |
| Markdown only | `markdownlint-cli2` |
| i18n strings | `task i18n` + `pytest` |
| Mixed / unsure | `task check && task test` |

## Git Hooks

- **pre-commit**: Conditional checks (v3 — granularized) — Prek auto-fix (always) → Markdownlint via `markdownlint-cli2` (on `.md` changes, uses the same glob as `Taskfile.yml`'s `MD_GLOB`) → Ruff lint/format (on Python changes) → Pyright/ty (on Python changes) → pytest (on Python changes) → ESLint via `pnpm turbo run lint` (on code/style/config changes — `NEEDS_LINT`: docs `.ts`/`.tsx`/`.mjs`/`.mts`/`.css`/config, packages `.ts`/`.tsx`/`.mjs`/`.mts`/`.js`/`.css`; skips pure `.mdx`/`.json` content changes) → check-types via `pnpm turbo run check-types` (on any frontend change — `NEEDS_TYPE_CHECK`) → Docs Vitest (on docs code/content/config changes — `NEEDS_DOCS_TEST`; skips pure `.css` style-only changes) → React Doctor (on `.tsx` changes only — `NEEDS_REACT_DOCTOR`, prefers global/local install, falls back to `pnpm dlx` cache, last resort `npx -y`) → Gitnexus analyze (always, non-blocking, prefers `node_modules/.bin/gitnexus` for zero download)
- **commit-msg**: gitmoji + Conventional Commits format validation + auto-append Signed-off-by (with trailer block detection)
- **prepare-commit-msg**: Interactive gitmoji commit message via direct `node_modules/.bin/gitmoji --hook` (zero pnpm/npx overhead; falls back to npx / global gitmoji if local missing)
- **CLI resolution order** (all hooks): local `node_modules/.bin/<bin>` → global PATH → global `.cmd` shim → `pnpm dlx` cache (last resort: `npx -y` for non-devDeps)
- Set `$env:HUSKY='0'` to skip hooks when needed (e.g., automated commits)

## Agent Preferences

These rules are injected as context for every conversation. Treat them as hard constraints.

- **Always check git workspace status before committing** — before any commit, run `git status` and `git diff` to verify all necessary changes are tracked, no unintended files are staged, and the working tree is clean. Never commit blindly.
- **No commits or pushes without explicit user instruction** — never auto-commit, auto-push, or assume the user wants a commit after finishing a task. Wait for the user to say so.
- **Write persistent preferences into AGENTS.md** — memory files and session context are ephemeral; AGENTS.md is the single source of truth for project-level rules and user preferences. When the user says "remember this" or expresses a preference, add it here.
- **Pre-planning development stage** — this project is still in a pre-planning / early development stage, so severe breaking changes are acceptable when they simplify the architecture or unblock the intended product direction.
- **Prefer granular checks over full `task check`** — use the Quick Reference table above to run only the checks relevant to what changed. Full `task check && task test` is for pre-commit verification, not for every intermediate step.
- **Use PowerShell without profiles** — when explicitly invoking PowerShell from automation, use `pwsh.exe -NoProfile` so user profile scripts do not slow down or pollute command output.
- **Sync Chinese/English documents** — when editing AGENTS.md, always propagate the same structural changes to `.github/note/AGENTS-zh.md` and vice versa.
- **Sync AGENTS.md and CLAUDE.md** — these two files share the same structure and content (GitNexus block, project context, dev commands, lessons learned, etc.). When editing either file, always propagate the same structural changes to the other. The only allowed difference is the Claude Code Behavioral Guidelines section, which exists only in `CLAUDE.md`.

## AI Context Injection Map

All files and directories that inject context into AI coding agents. Use this map to understand what each injection point does and when it's loaded, avoiding redundant reads.

### Root-Level Files

| File | When Loaded | Purpose |
|------|-------------|---------|
| `AGENTS.md` | Every conversation (Trae, Codex) | Single source of truth for project rules, conventions, dev commands, lessons learned. Also contains GitNexus config block. |
| `CLAUDE.md` | Every conversation (Claude Code) | Same role as `AGENTS.md` but for Claude Code. Contains GitNexus block, project context, dev commands, and behavioral guidelines (simplicity-first, surgical changes, goal-driven execution). Largely duplicates `AGENTS.md` content. |

### Trae IDE Rules (`.trae/rules/`)

| File | When Loaded | Purpose |
|------|-------------|---------|
| `.trae/rules/git-commit-message.md` | Always applied (Trae) | Gitmoji + Conventional Commits format specification. Enforces commit message format with regex validation. |

### Skill Directories

Skills are loaded **on demand** — only when the user's task matches the skill trigger. They are NOT injected into every conversation.

#### `.agents/skills/` (Trae / Codex)

| Skill | Trigger | Purpose |
|-------|---------|---------|
| `available-skills/` | When choosing which skill to load | Compact routing index of all available skills. Lists project-local, coding, frontend, cloud, artifact, and skill-authoring skills. |
| `engineering-workflow/` | Code understanding, GitNexus, debugging, TDD, review, frontend quality, design, and issue planning | Consolidated engineering entrypoint with focused references for GitNexus, delivery-loop, design-prototyping, frontend-quality, and issue-planning. |
| `tool-workflows/` | Documentation lookup, hooks, prek/Husky, and skill maintenance | Consolidated tool entrypoint with focused references for Context7 docs, repo hooks, and skill management. |

### Cross-Language Counterpart

| File | Purpose |
|------|---------|
| `.github/note/AGENTS-zh.md` | Chinese translation of `AGENTS.md`. Must be kept in sync with structural changes. |

### What Gets Injected Automatically

Only these are injected into **every** conversation without explicit loading:

1. **`AGENTS.md`** (or `CLAUDE.md` for Claude Code) — full file content
2. **`.trae/rules/git-commit-message.md`** — Trae only, always applied
3. **Skill descriptions** — the `description` field from each `SKILL.md` frontmatter is listed in the tool's `available_skills`, but the full `SKILL.md` content is only loaded when the skill is invoked

Everything else (skill files, reference docs, manifests) is loaded **on demand** only when a matching task triggers the skill.

## Architecture Decisions

- All server components and route handlers in `apps/docs` are async functions
- `baseOptions()`, `buildGraph()`, `getRSS()` return Promises
- i18n uses `hideLocale: 'default-locale'` — default locale (en) omits prefix in URLs
- Client components use `useSyncExternalStore` instead of `useState` + `useEffect` for mount detection
- GitNexus is used for code intelligence, impact analysis, and safe refactoring

## Commit Convention

Use conventional commit + gitmoji: `✨ feat:`, `🐛 fix:`, `📝 docs:`, `⚡ perf:`, etc.

## CI

GitHub Actions runs on push to `main`/`dev` and on PRs:

- **🧪 CI**: Change detection job (`changes`) outputs boolean flags per file type (python/markdown/frontend/frontend-code/frontend-style/frontend-content/frontend-tsx), then conditionally runs downstream jobs — Static analysis (Ruff + Markdown + Turborepo lint, on Python or markdown changes), Tests & type check (Pyright + ty + pytest, on Python changes), Docs check (ESLint on code/style, check-types on any frontend, link validation on content, Vitest on code/content — aligned with pre-commit v3 `NEEDS_LINT`/`NEEDS_TYPE_CHECK`/`NEEDS_DOCS_TEST`). Auto-format on push to main/dev. Test jobs install `--extra deprecated-adapters` so test files importing optional dependencies (Milky adapter) can resolve.
- **👷 CI-builds**: Build verification on Python/package changes
- **📚 Docs Deploy**: Build and deploy to GitHub Pages on push to main/dev
- **� React Doctor**: React codebase health check on PRs (uses CLI, not the action — see Lessons Learned)
- **� Clear Workflow**: Stale workflow cleanup
- **🏷️ Issues Top**: Issue triage automation

## Engineering Conventions

### `fire_and_forget` Helper

- **Location**: `src/plugins/nonebot_plugin_lingchu_bot/core/async_utils.py`
- **Signature**: `fire_and_forget(coro, *, name="fire_and_forget")`
- **Use for**: discardable background operations (audit logs, telemetry, cache writes) whose results the caller does not need. The helper schedules the coroutine as an `asyncio.Task`, tracks it in a module-level set, and logs exceptions via `logger.exception` in a done-callback.
- **Do NOT use for**: operations whose results are needed by the caller, or operations that must complete before the function returns. In those cases, use `await` directly.
- **Reference management**: the helper stores the task in a module-level set so Python's GC does not cancel it prematurely; the done-callback removes the reference after logging any exception.

### Command Handler State Control (Silent Mode & Handle Gate)

- **Location**: `src/plugins/nonebot_plugin_lingchu_bot/core/bot_state.py`
- **Two-tier state model**: Maintains a global state plus per-platform overrides for `handle_active` (gate, default `True`) and `silent_mode` (default `False`). State is persisted to `bot_state.json5` in the plugin data directory via `get_plugin_data_dir()`.
- **Resolution semantics**:
  - `is_handle_active(platform_id)`: global AND platform — global OFF disables all platforms.
  - `is_silent_mode(platform_id)`: global OR platform — global ON silences all platforms.
  - Both functions now require a `platform_id` parameter.
- **`selected_adapter_handle` params**: The decorator in `handle/qq/commands/common.py` accepts `bypass_gate: bool = False` and `bypass_silent: bool = False` keyword params. It resolves `platform_id` from `adapter_id` via `get_platform_profile`. When both bypass flags are `False` (default), the handler is wrapped by `_state_wrapper` which enforces both the handle gate and silent mode.
- **`_state_wrapper`**: Accepts `platform_id`, `check_gate`, and `check_silent` params. Wrapper chain order: `_state_wrapper` (outermost) → `_permission_wrapper` → `func`. `_state_wrapper` checks the gate first (returns early if handle is inactive), then checks silent mode (routes to `_silent_call` if silent).
- **`_silent_call`**: Temporarily replaces `command.finish` with a no-send version that raises `FinishedException`, so the handler runs its logic but no response message is sent. The original `finish` is restored in a `finally` block.
- **Commands control global state**: The 4 commands ("闭嘴"/"说话"/"开机"/"关机") control global state via `set_global_silent_mode()` and `set_global_handle_active()` functions.
- **Command bypass settings**:
  - "闭嘴"/"说话" (silence/speak) use `bypass_silent=True` — they always respond, but are disabled when the bot is shut down (gate off).
  - "开机"/"关机" (boot/shutdown) use both `bypass_gate=True` and `bypass_silent=True` — they must always work to recover the bot from any state.
- **Menu**: The "bot-control" page is replaced with a "system-management" / "系统管理" top-level page containing children "silent-mode" / "静默模式" and "handle-gate" / "开关机".

### Configuration Management

- **Pre-commit hooks**: `prek.toml` is the single source of truth for pre-commit hook configuration. The legacy `.pre-commit-config.yaml` has been removed — do not re-introduce it.
- **Version sync**: The `Taskfile.yml` `ci:version:write-config` task writes the project version to both `src/plugins/nonebot_plugin_lingchu_bot/core/config.py` (Python `__version__`) and `apps/docs/package.json` (`version` field). When bumping the version, run this task rather than editing files manually.
- **JSON Schemas**: The `schema/` directory at the repository root contains JSON Schema files for validating JSON5 config files: `config.schema.json5` (for `config.json5`) and `bot_state.schema.json5` (for `bot_state.json5`). Editors that support `$schema` comments can reference these for autocompletion and validation.
- **Skills exclusion sync**: `pyproject.toml` has comments at skills exclusion lists noting "skills 排除列表同步至 prek.toml" — when updating exclusion patterns in one config, sync the other.

## Lessons Learned

> **Timeliness warning**: Lessons below reflect the state of the codebase and dependencies at the time they were written. Before relying on any lesson, verify it still holds — APIs change, packages add exports, and CI configs evolve. When a lesson becomes outdated, update or remove it rather than propagating stale assumptions.

### Cross-Cutting Change Checklist

When modifying business logic (especially adapter-layer code), changes MUST propagate to all affected areas **before considering the task done**:

1. **Source code** — `src/plugins/nonebot_plugin_lingchu_bot/`
2. **Tests** — `tests/` (add/update tests for new behavior, remove tests for deleted behavior)
3. **i18n** — `src/plugins/nonebot_plugin_lingchu_bot/i18n/` (run `task i18n` if user-facing strings change)
4. **Docs** — `apps/docs/content/docs/`:
   - `platforms/qq/commands.mdx` (and `.zh.mdx`) — Full command reference
   - `platforms/qq/<protocol>/<implementation>.mdx` — Implementation-specific docs
   - `user-guide/commands.mdx` — High-level overview (only if menu structure changes)
   - `developer-guide/introduction.mdx` — Project structure (only if source layout changes)
5. **Menu** — `src/plugins/nonebot_plugin_lingchu_bot/handle/menu.py` (update `MENU_FEATURES` when adding/removing/modifying command handlers: command key, usage text, summary, availability)
6. **Triggers** — `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/commands/triggers.py` (add command triggers for new commands)
7. **AGENTS.md** — Update Project Directory Tree and Lessons Learned if structure or conventions change

After changes, always run the full check suite: `task check && task test`

### Use MCP / Skills Proactively

- **NapCat API MCP** (`mcp_NapCat_-_API_Wen_Dang_*`): Use to look up OneBot V11 API specs (parameters, response fields) before writing adapter calls. Avoid guessing API signatures.
- **Context7 / find-docs**: Use for up-to-date library docs (NoneBot2, Alconna, Pydantic, etc.) — training data may be outdated.
- **GitNexus MCP**: Run `gitnexus_impact` / `gitnexus_context` before editing symbols; run `gitnexus_detect_changes` before committing.
- **WebSearch / WebFetch**: Use when MCP tools don't cover the needed info (e.g., third-party API changelogs).
- Rule of thumb: **When touching adapter boundaries, external APIs, or unfamiliar libraries, always verify via MCP/skills first** — don't rely on memory or assumptions.

### Session Epilogue: Update AGENTS.md

At the end of every conversation that involves code changes, review what went wrong or what took extra iterations, and append reusable lessons to this `Lessons Learned` section. This prevents repeating the same mistakes.

### Command Trigger Localization

Group command trigger words are locale-exclusive. Do not register Chinese and English command triggers at the same time for the same matcher. Use the i18n locale resolution helpers (`LINGCHU_LOCALE`, `lc_locale`, `locale` via `get_configured_locale()`) to choose one trigger language during command registration, and keep the inactive language out of `aliases`.

### Layered Menu Commands

When turning menu categories into standalone commands, audit conflicts with existing feature command aliases before registering the category matcher. Keep the top-level `菜单` / `menu` response as an index and test it separately from category pages, so feature filtering assertions target the page that actually renders the feature rows.

### Permission System Boundaries

Platform default identity groups live in platform modules such as `platforms/qq/permissions.py`; the core `permissions/` package consumes seeds and runtime resolvers but must not hard-code platform role trees. Command permission checks, menu filtering, and handler decorators all use `MENU_FEATURES.command_key` as the shared command identifier. Menus should fail closed and hide commands the current identity cannot execute. SUPERUSERS may CRUD custom platform identity groups and memberships through public async APIs, but builtin platform groups are seeded by platform modules and must not be overwritten by admin CRUD.

### Adapter API Differences

Same-named APIs return different types across adapters:

| API | OneBot V11 | Milky |
|-----|-----------|-------|
| `get_group_member_info` | `dict` (use `.get("card")`) | `Member` model (use `.card`) |
| `set_group_ban` | `set_group_ban(group_id, user_id, duration)` | `set_group_member_mute(group_id, user_id, duration)` |

The project uses `platforms/registry.py` to unify adapters under a single "QQ" platform profile. Only OneBot V11 is now active; Milky, QQ, and OneBot V12 are deprecated and removed from the startup flow. QQ and OneBot V12 source files are preserved with `DEPRECATED = True` markers and can be loaded on demand via `tools/adapter_loader.py`; the Milky adapter has been fully removed. QQ group command code lives under `handle/qq/`: shared command definitions in `handle/qq/commands/`, OneBot V11 handlers in `handle/qq/adapters/onebot11/{default,llonebot,napcat}/`. Always verify the return type by inspecting the adapter source in `.venv/Lib/site-packages/nonebot/adapters/` before writing access patterns.

### Function Signature Changes

When changing a function signature (sync→async, adding/removing params):

1. Use `Grep` to find ALL callers across the entire codebase
2. Update every caller — not just the obvious ones (check `mute.py`, `member.py`, etc.)
3. Update test fixtures (`conftest.py`) and test functions that construct mock objects
4. Run `ruff check`, `pyright`, `ty check`, and `pytest` to catch missed updates

### Exception Handling in Tests

- Test `side_effect` exceptions must match the actual `except` clause in source code
- `ActionFailed()` from Milky and OneBot V11 adapters may not accept positional arguments — always check the constructor signature
- Use `ruff check` to catch BLE001 (blind `except Exception`) — prefer specific adapter exceptions

### Gettext Helper Shadowing

- Many handlers import gettext as `_`. Do not use `_` as a throwaway local variable in those functions (for example `deleted, _ = ...`) because it shadows the gettext helper and causes later `await _("...")` calls to fail at runtime. Use `result = ...; deleted = result[0]` or a descriptive unused name outside gettext-heavy scopes.

### Removing Code

When removing functions/helpers:

1. `Grep` for all references (including tests) before deletion
2. Remove associated tests that test the deleted behavior
3. Remove unused imports that were only needed by the deleted code
4. Verify no other module re-exports or depends on the removed symbol

### Mock Object Patterns for Adapter Models

- OneBot V11 returns `dict` → mock with `return_value={}`
- Milky returns pydantic `Model` objects → mock with `MagicMock(card="", nickname="")` so attribute access works
- Never use `dict` as mock return value for APIs that return Model objects — attribute access (`obj.card`) will raise `AttributeError`

### Python Package Directory Names

- Directory segments that are imported as Python packages must be valid Python identifiers for both runtime imports and static tools. For protocol versions, prefer a leading letter such as `v1_2` instead of `1_2`; `importlib` may load numeric-leading folders, but `ty` cannot resolve them reliably.

### Type Narrowing in Tests

- `isinstance(event, GroupMessageEvent)` is the correct way to narrow event types in NoneBot2
- Don't use `type(event) is GroupMessageEvent` — it breaks with proxy/wrapper objects

### ESLint Major Version Compatibility

- **`eslint-plugin-react@7.x` is incompatible with ESLint 10.** The plugin calls `context.getFilename()` which was removed in ESLint 10's breaking change to `context.filename`. This causes `TypeError: contextOrFilename.getFilename is not a function` at load time.
- **Fix options**: (a) Pin ESLint to v9 in packages that use `eslint-plugin-react`; (b) Migrate to `@eslint-react/eslint-plugin` (v5+, supports ESLint 10); (c) Wait for `eslint-plugin-react` to release ESLint 10 support.
- **Prevention**: When running `pnpm install`, always check `git diff` on `package.json` files before committing — `pnpm install` can silently bump `^` range dependencies to newer major versions that break compatibility.

### CI Workflow Project References

- When a workspace package is disabled or removed, **all CI workflows that reference it must be updated**. For example, React Doctor's `--project docs,web` flag will fail if `web` has no React source files.
- **Rule**: After any workspace package change (disable, remove, rename), grep all workflow files for references to that package name and update them.

### Markdown Table Alignment (MD060)

- `markdownlint-cli2` v0.22+ enforces MD060 (table column style). The default style `aligned` requires visual pipe alignment, which is unreliable with CJK characters because character display width (2 columns for CJK) differs from character count (1 per CJK char in source).
- **Fix**: Set MD060 style to `consistent` in `.markdownlint.jsonc` — this only requires that each column's pipes appear at the same character position across all rows, without demanding visual alignment. This works correctly for both pure-ASCII and mixed CJK/Latin tables.
- **Do not** disable MD060 entirely — `consistent` style still catches real formatting errors (missing pipes, inconsistent column counts) while avoiding false positives from CJK width mismatches.

### Windows Commands in Bash Hooks

- Husky hooks may run under a Bash environment that sees Windows commands differently from PowerShell. Check that a command can actually start, not only that `command -v` finds it.
- Prefer resolving tool commands once near the top of the hook. For Windows `.cmd` Node shims such as `pnpm.cmd` and `npx.cmd`, invoke them through `cmd.exe /c`; executing the `.cmd` file directly from Bash can silently skip checks or emit misleading `node` errors.
- Do not suppress `git diff --cached` failures when deciding which checks to run. If `git` is unavailable in the hook shell, fail clearly instead of treating the staged file list as empty.

### PowerShell Markdownlint Globs

- When running `markdownlint-cli2` through `pwsh.exe -NoProfile -Command`, pass glob arguments exactly as the shell should see them; incorrectly nested or escaped quotes can turn globs into malformed paths and make Node scan far more than intended. Prefer the Taskfile command or a known-good direct command form before treating a markdownlint timeout as a lint failure.

### Markdownlint Per-Directory Overrides

- `markdownlint-cli2` supports hierarchical configuration: a `.markdownlint.jsonc` file in a subdirectory overrides the root config for files in that directory.
- **Important**: The subdirectory `.markdownlint.jsonc` REPLACES the root rule config, it does not merge. Always include all root settings (e.g., `MD013: false`, `MD033: false`, `MD041: false`, `MD060` config) in the subdirectory config, plus any additional rule suppressions.
- `.github/.markdownlint.jsonc` disables MD022 (blanks-around-headings) and MD032 (blanks-around-lists) for `.github` docs, as CJK content in AGENTS-zh.md frequently triggers these rules without actual formatting issues.

### Husky Hook CLI Resolution

- `npx <bin>` and `pnpm exec <bin>` always re-resolve a package, even when `node_modules/.bin/<bin>` is already present. On a warm cache this still costs a sub-process spawn, an npm registry HEAD, and a lockfile check; on a cold cache it downloads a full tarball. Either cost dominates the per-hook budget for trivial checks like `gitnexus analyze` or `gitmoji --hook`.
- **Resolution order for JS CLIs in Husky hooks**: `node_modules/.bin/<bin>` (devDep shim, zero download) → global `PATH` (`command -v <bin>` and runnable check) → global `.cmd` shim (only if no native found, invoke via `cmd.exe /c`) → `pnpm dlx <bin>` cache → `npx -y <bin>` (last resort, for non-devDeps that must be fetched on demand).
- For devDependencies that are guaranteed by `package.json` (e.g., `gitmoji-cli`, `gitnexus`), the local `node_modules/.bin/<bin>` branch should always succeed once `pnpm install` has run, so the hook never needs to fall back to `npx` in the common path.
- Cache the resolved tool reference in a variable at the top of the hook and reuse it across phases; avoid re-running `command -v` inside loops or per-file logic.
- When using `.cmd` shims (Windows Node shims like `pnpm.cmd`, `npx.cmd`), execute them via `cmd.exe /c <shim> ...` — running the `.cmd` directly from Git Bash can silently exit with misleading "node not found" errors.

### Database Storage Reorganization

- **Unified ORM consolidation**: When migrating from custom SQLAlchemy engines to `nonebot_plugin_orm`, remove ALL custom engine management code (`Base`, `_ENGINES`, `session_for()`, `storage_target()`, `close_engines()`) — do not leave remnants. All data access must go through `orm_crud/` package + `get_session()`.
- **Test rewrite pattern**: Tests that directly manipulated database files (e.g., checking `.db` file existence, using `session_for()` to modify records) MUST be rewritten to mock `orm_crud` functions at the repository module level using `patch.object(repository, "create"/"upsert"/"get_one"/"update"/"list_items"/"delete", ...)`. Follow the pattern in `tests/repositories/test_blocklist.py`.
- **Alembic migration generation**: `nb orm revision` may generate an empty migration (`pass` in both `upgrade()` and `downgrade()`) if the database file already contains tables from previous `create_all` calls. In this case, manually write the migration script with `op.create_table()` / `op.create_index()` operations based on the model definitions, or delete the existing database file first (if not locked by another process).
- **File-to-package conversion**: When converting a single `.py` file (e.g., `json5_store.py`) to a package (`json5_store/`), the `__init__.py` MUST explicitly re-export all public API symbols via `from .submodule import Symbol` and list them in `__all__`. Merely importing the submodule is insufficient — test imports like `from ..database.json5_store import RobustAsyncJSON5DB` will fail without explicit re-exports.
- **Migration script lint**: Alembic-generated migration scripts use `collections.abc.Sequence` only for type annotations. With `from __future__ import annotations` in place, move the `Sequence` import into a `TYPE_CHECKING` block to satisfy ruff's `TC003` rule.
- **Documentation sync**: When deleting or renaming source files, update ALL documentation references (AGENTS.md file tree, architecture diagrams, `apps/docs/` MDX files) — not just code. Use `Grep` to find stale references after structural changes.

### Platform/Adapter/Protocol Table Reorganization

- **Registry table seeding**: When adding database registry tables that mirror Python data structures (like `registry.py`), implement a `seed_registry_tables()` function that upserts metadata on startup. Use `conflict_fields` for idempotent upserts so re-running doesn't create duplicates.
- **Protocol dimension tracking**: When adding a `protocol_id` column to existing tables, make it nullable (`Mapped[str | None]`) since the protocol implementation may not always be determinable at the point of recording (e.g., at event_preprocessor time, the handler hasn't run yet).
- **Unique constraint with nullable columns**: SQLite treats NULL values as distinct in unique constraints, so `(platform_id, adapter_id, protocol_id, ...)` allows multiple records with `protocol_id=NULL` for the same message identity. This is acceptable for message records but should be documented.
- **Migration script rewrite for new deployments**: When the user accepts "new deployment only" strategy, rewrite the initial migration script directly rather than creating a new migration that alters the schema. This keeps the migration history clean for fresh deployments.

### Multi-Database Testing

- **SQLALCHEMY_DATABASE_URL environment variable**: `nonebot_plugin_orm` reads this env var to configure the database backend. In tests, `conftest.py` passes it through to `nonebot.init()` so the same test suite can run on SQLite, PostgreSQL, or MySQL.
- **CI matrix strategy**: Use GitHub Actions matrix with `fail-fast: false` to test all database backends independently. PostgreSQL and MySQL use `services` containers with conditional images (`startsWith(matrix.db, 'postgresql') && 'postgres' || ''`) to avoid starting unnecessary services for SQLite.
- **Migration before tests**: Always run `uv run nb orm upgrade` before running tests on non-SQLite databases, since `ALEMBIC_STARTUP_CHECK=false` only auto-syncs on startup (not during test collection).
- **Test dependency isolation**: Database drivers (`psycopg[binary]`, `aiomysql`) are in the `test` dependency group, not the main dependencies. This keeps production installs lightweight while enabling multi-database testing in dev/CI.

## Docs Site Component Catalog

Complete inventory of all functional components in `apps/docs/`. Each entry covers purpose, inputs/outputs, tech details, and usage examples.

### 1. React UI Components (`src/components/`)

#### 1.1 `GraphView` — Document Relationship Graph

| Field | Detail |
|-------|--------|
| **Full name** | `@/components/graph-view.GraphView` |
| **Purpose** | Renders an interactive force-directed graph of all documentation pages and their cross-references, enabling visual navigation of the doc site structure. |
| **Tech** | `react-force-graph-2d` + `d3-force` (forceCollide, forceLink, forceManyBody). Client-only via `lazy()` + `useSyncExternalStore` mount detection. Hover highlights neighbors; click navigates via `fumadocs-core/framework` router. |
| **Props** | `graph: Graph` where `Graph = { nodes: Node[], links: Link[] }`, `Node = { text: string, description?: string, url: string }`, `Link = { source: string, target: string }` |
| **Output** | Renders a `<canvas>` element (600px height) with SVG tooltip overlay. No return value. |
| **Best practice** | Call `buildGraph()` server-side and pass the result as props. Graph data is static at build time. |
| **Limitations** | Client-only rendering — SSR will skip the graph. Requires `react-force-graph-2d` which bundles d3 (~200KB). |

**Use cases:**

1. **Homepage graph** — Show all docs and their relationships on the landing page:

   ```tsx
   import { GraphView } from '@/components/graph-view';
   import { buildGraph } from '@/lib/build-graph';
   // In server component:
   const graph = await buildGraph();
   return <GraphView graph={graph} />;
   ```

2. **Filtered subgraph** — Pass only nodes matching a tag or section to show a focused view.
3. **Debug linking** — Use the graph to visually verify that all pages are reachable and cross-linked.

---

#### 1.2 `LLMBadge` — AI-Friendly Docs Indicator

| Field | Detail |
|-------|--------|
| **Full name** | `@/components/llm-badge.LLMBadge` |
| **Purpose** | A small icon button that links to `/llms.txt`, signaling that the documentation is available in an LLM-friendly text format. |
| **Tech** | `lucide-react` Bot icon, `fumadocs-ui` button variants, `next/link`. |
| **Props** | `locale?: string` — `'zh'` shows Chinese tooltip, any other value shows English. |
| **Output** | Renders a ghost-variant icon `<Link>` pointing to `/llms.txt`. |

**Use cases:**

1. **Navbar badge** — Add to the docs layout nav bar to indicate LLM-friendly docs availability.
2. **Footer link** — Place in the page footer as a discoverable link.
3. **Custom locale** — Pass `locale="zh"` for Chinese-language tooltip text.

---

#### 1.3 `Provider` — App-Wide Context Provider

| Field | Detail |
|-------|--------|
| **Full name** | `@/components/provider.Provider` |
| **Purpose** | Wraps the app with Fumadocs `RootProvider`, configuring i18n locale switching and the search dialog. |
| **Tech** | `fumadocs-ui/provider/next.RootProvider`, `fumadocs-ui/i18n.i18nProvider`, custom `switchLocale()` path manipulation. Client component. |
| **Props** | `children: ReactNode` |
| **Output** | Provides i18n context + search dialog context to children. |
| **Key behavior** | `switchLocale()` handles 3 cases: default→other (prepend segment), other→default (remove segment), other→other (replace segment). |

**Use cases:**

1. **Root layout** — Wrap `{children}` in `src/app/layout.tsx` with `<Provider>`.
2. **Custom locale logic** — Extend `switchLocale()` for additional locale routing patterns.
3. **Custom search** — Replace `SearchDialog` import to use a different search implementation.

---

#### 1.4 `DefaultSearchDialog` — Full-Text Search

| Field | Detail |
|-------|--------|
| **Full name** | `@/components/search.default` (default export) |
| **Purpose** | Provides a client-side full-text search dialog using FlexSearch static index, with i18n-aware locale filtering. |
| **Tech** | `fumadocs-core/search/client.useDocsSearch` + `flexsearchStaticClient`, `fumadocs-ui/components/dialog/search.*`. |
| **Props** | `SharedProps` from fumadocs (open/close state). |
| **Output** | Renders a modal search dialog with overlay, input, result list, and footer. |

**Use cases:**

1. **Default search** — Passed to `RootProvider` via `search={{ SearchDialog }}` prop.
2. **Standalone search** — Import and render directly in a custom layout.
3. **Locale-aware** — Automatically filters results by current locale via `useI18n()`.

---

### 2. MDX Components (`src/components/mdx.tsx`)

These components are registered in `getMDXComponents()` and available in all `.mdx` files without import.

#### 2.1 `Accordion` / `Accordions` — Collapsible Sections

| Field | Detail |
|-------|--------|
| **Full name** | `fumadocs-ui/components/accordion.Accordion`, `Accordions` |
| **Purpose** | Collapsible FAQ-style sections. `Accordions` wraps multiple `Accordion` items with single/multi expand mode. |
| **Props (Accordions)** | `type: "single" | "multiple"` — single allows only one open at a time. |
| **Props (Accordion)** | `title: string` — header text. Children are the collapsible content. |
| **MDX usage** | `<Accordions type="single"><Accordion title="Q1">Answer</Accordion></Accordions>` |
| **Limitation** | Children must be plain text or inline JSX — Markdown list syntax (`- item`) inside `<Accordion>` causes MDX parse errors. Use prose text instead. |

**Use cases:**

1. **FAQ page** — Wrap Q&A pairs in Accordions for expandable troubleshooting.
2. **Detailed explanations** — Collapse verbose content under a summary title.
3. **Version-specific notes** — Show different instructions per version in separate accordions.

---

#### 2.2 `AutoTypeTable` — Auto-Generated Type Table

| Field | Detail |
|-------|--------|
| **Full name** | `fumadocs-typescript/ui.AutoTypeTable` |
| **Purpose** | Generates a typed property table from TypeScript type definitions in the project, eliminating manual table maintenance. |
| **Tech** | Uses `fumadocs-typescript` generator with file-system cache (`.next/fumadocs-typescript`). |
| **Props** | `Partial<AutoTypeTableProps>` — typically `path: string` pointing to a TypeScript source file. |
| **MDX usage** | `<AutoTypeTable path="./my-types.ts" />` |
| **Limitation** | Requires the TypeScript file to exist at build time. Only works with exported types. |

**Use cases:**

1. **Config reference** — Auto-generate a config options table from the actual TypeScript config interface.
2. **API params** — Document request/response types directly from source.
3. **Component props** — Show prop tables for React components.

---

#### 2.3 `TypeTable` — Manual Type Table

| Field | Detail |
|-------|--------|
| **Full name** | `fumadocs-ui/components/type-table.TypeTable` |
| **Purpose** | Manually define a typed property table with full control over each entry's type, default, and description. |
| **Props** | `type: Record<string, { type: string, default?: string, description: string, required?: boolean }>` |
| **MDX usage** | See `configuration.mdx` for a working example. |
| **Best practice** | Use when the type source is not a TypeScript file (e.g., Python config, environment variables). |

**Use cases:**

1. **Environment variables** — Document `.env` variables with types and defaults.
2. **Python config** — Map Python config fields to a structured table.
3. **Hybrid docs** — Mix auto-generated and manual type tables in the same page.

---

#### 2.4 `Tabs` / `Tab` — Tabbed Content

| Field | Detail |
|-------|--------|
| **Full name** | `fumadocs-ui/components/tabs.Tabs`, `Tab` |
| **Purpose** | Show mutually exclusive content panels, ideal for platform-specific or adapter-specific instructions. |
| **Props (Tabs)** | `items: string[]` — tab labels. |
| **Props (Tab)** | `value: string` — must match an item from `items`. |
| **MDX usage** | `<Tabs items={['OneBot V11', 'Milky']}><Tab value="OneBot V11">...</Tab><Tab value="Milky">...</Tab></Tabs>` |

**Use cases:**

1. **Adapter guide** — Show per-adapter configuration in separate tabs.
2. **OS-specific setup** — Linux/macOS/Windows installation steps.
3. **Runtime mode** — Plugin directory vs Docker deployment instructions.

---

#### 2.5 `Steps` / `Step` — Sequential Steps

| Field | Detail |
|-------|--------|
| **Full name** | `fumadocs-ui/components/steps.Steps`, `Step` |
| **Purpose** | Render numbered sequential steps with automatic numbering and visual progress. |
| **Props** | No required props. Each `<Step>` wraps one step's content (typically a heading + body). |
| **MDX usage** | `<Steps><Step>### Step 1\nContent</Step><Step>### Step 2\nContent</Step></Steps>` |

**Use cases:**

1. **Quick start** — Installation and setup steps.
2. **Deployment** — Step-by-step deployment procedure.
3. **Migration** — Version upgrade migration steps.

---

#### 2.6 `Files` / `Folder` / `File` — Directory Tree

| Field | Detail |
|-------|--------|
| **Full name** | `fumadocs-ui/components/files.Files`, `Folder`, `File` |
| **Purpose** | Visualize a project directory tree with collapsible folders. |
| **Props (Folder)** | `name: string`, `defaultOpen?: boolean` |
| **Props (File)** | `name: string` |
| **MDX usage** | `<Files><Folder name="src" defaultOpen><File name="index.ts" /></Folder></Files>` |

**Use cases:**

1. **Project structure** — Show the source code layout in developer guide.
2. **Config file location** — Highlight where config files live.
3. **New contributor onboarding** — Visual map of the codebase.

---

#### 2.7 `InlineTOC` — Inline Table of Contents

| Field | Detail |
|-------|--------|
| **Full name** | `fumadocs-ui/components/inline-toc.InlineTOC` |
| **Purpose** | Render an inline (non-sidebar) table of contents within the page content. |
| **Props** | Not yet used in current docs. Available for future pages that need in-content navigation. |

---

#### 2.8 `Mermaid` — Diagram Rendering

| Field | Detail |
|-------|--------|
| **Full name** | `@/components/mdx/mermaid.Mermaid` |
| **Purpose** | Render Mermaid diagrams (flowcharts, sequence diagrams, etc.) inside MDX content. |
| **Tech** | Lazy-loads `mermaid` library, renders to SVG, sanitizes with DOMPurify (`securityLevel: 'strict'`). Supports light/dark theme via `next-themes`. Client-only. |
| **Props** | `chart: string` — Mermaid diagram syntax. |
| **MDX usage** | Code fence with `mermaid` language: <code>```mermaid\ngraph TD; A-->B;\n```</code> |
| **Security** | SVG output is sanitized via DOMPurify with `USE_PROFILES: { svg: true, svgFilters: true }`. `htmlLabels: false` prevents inline HTML in labels. |
| **Helper module** | `mermaid-utils.ts` exports `getMermaidConfig()`, `sanitizeMermaidSvg()`, `renderMermaidSvg()`. |

**Use cases:**

1. **Architecture diagram** — Show system component relationships.
2. **Flow chart** — Visualize decision trees or process flows.
3. **Sequence diagram** — Illustrate API call sequences between bot and platform.

---

#### 2.9 `ImageZoom` — Clickable Image Zoom

| Field | Detail |
|-------|--------|
| **Full name** | `fumadocs-ui/components/image-zoom.ImageZoom` |
| **Purpose** | Wraps all `<img>` tags to enable click-to-zoom functionality. |
| **Tech** | Applied globally via `mdx.tsx` — replaces the default `img` renderer. |
| **No explicit usage needed** — all images in MDX automatically get zoom behavior. |

---

#### 2.10 Twoslash — TypeScript Code Hover

| Field | Detail |
|-------|--------|
| **Full name** | `fumadocs-twoslash/ui.*` |
| **Purpose** | Adds hover-to-inspect and inline error tooltips to TypeScript code blocks. |
| **Tech** | `fumadocs-twoslash` + `twoslash`. Registered via `...Twoslash` spread in `getMDXComponents()`. |
| **MDX usage** | Code fence with `twoslash` meta: <code>```ts twoslash\nconst x: string = 1;\n```</code> |

---

### 3. Library Modules (`src/lib/`)

#### 3.1 `source.ts` — Content Source API

| Field | Detail |
|-------|--------|
| **Full name** | `@/lib/source` |
| **Purpose** | Creates the Fumadocs content source loader, providing page tree, search index, and page metadata. |
| **Key exports** | `source` (loader instance), `getPageImage()`, `getPageMarkdownUrl()`, `getLLMText()` |
| **Dependencies** | `collections/server` (generated by `fumadocs-mdx`), `./i18n`, `./shared` |
| **Tech** | `fumadocs-core/source.loader` with `lucideIconsPlugin()` for icon resolution in page tree. |

**Use cases:**

1. **Page enumeration** — `source.getPages()` returns all pages; `source.getPages('zh')` filters by locale.
2. **OG image URL** — `getPageImage(page)` returns the OG image route segments.
3. **LLM text** — `getLLMText(page)` returns markdown-formatted page content for `/llms.txt` routes.

---

#### 3.2 `build-graph.ts` — Document Relationship Graph Builder

| Field | Detail |
|-------|--------|
| **Full name** | `@/lib/build-graph.buildGraph` |
| **Purpose** | Builds the force-graph data (nodes + links) from the page tree and extracted cross-references. |
| **Input** | None (reads from `source` singleton). |
| **Output** | `Promise<Graph>` — `{ nodes: Node[], links: Link[] }` where each node has `id`, `url`, `text`, `description`. |
| **Dependencies** | `@/lib/source`, `@/components/graph-view` (types), `fumadocs-mdx` (ExtractedReference type). |
| **How it works** | Iterates all pages, creates a node per page, then reads `extractedReferences` from MDX post-processing to create links between pages. |

**Use cases:**

1. **Homepage graph** — `const graph = await buildGraph(); <GraphView graph={graph} />`
2. **Link validation** — Check for orphan nodes (pages with no links).
3. **Sitemap generation** — Use node URLs as sitemap entries.

---

#### 3.3 `rss.ts` — RSS Feed Generator

| Field | Detail |
|-------|--------|
| **Full name** | `@/lib/rss.getRSS` |
| **Purpose** | Generates an RSS 2.0 XML feed from the documentation page tree. |
| **Input** | `locale?: string` (default `'en'`) |
| **Output** | `Promise<string>` — RSS 2.0 XML string |
| **Dependencies** | `feed` package, `@/lib/source`, `@/lib/shared` |

**Use cases:**

1. **RSS route** — Used in `src/app/rss.xml/route.ts` and `src/app/zh/rss.xml/route.ts`.
2. **Feed preview** — Generate and inspect feed content during development.
3. **Multi-locale** — Call with `locale='zh'` for Chinese feed.

---

#### 3.4 `i18n.ts` — Internationalization Config

| Field | Detail |
|-------|--------|
| **Full name** | `@/lib/i18n.i18n` |
| **Purpose** | Defines the i18n configuration: supported languages, default locale, and URL behavior. |
| **Config** | `defaultLanguage: "en"`, `languages: ["en", "zh"]`, `hideLocale: "default-locale"` (English URLs omit `/en/` prefix). |
| **Convention** | English: `content/docs/foo.mdx`, Chinese: `content/docs/foo.zh.mdx`. Meta: `meta.json` / `meta.zh.json`. |

---

#### 3.5 `shared.ts` — Shared Constants

| Field | Detail |
|-------|--------|
| **Full name** | `@/lib/shared` |
| **Exports** | `appName: 'Lingchu Bot'`, `docsRoute: '/docs'`, `docsImageRoute: '/og/docs'`, `docsContentRoute: '/llms.mdx/docs'`, `gitConfig: { user, repo, branch }` |

---

#### 3.6 `layout.shared.tsx` — Layout Configuration

| Field | Detail |
|-------|--------|
| **Full name** | `@/lib/layout.shared` |
| **Key exports** | `translations` (i18n UI translations), `baseOptions(locale?)` (nav title, links, GitHub URL) |
| **Dependencies** | `fumadocs-ui/layouts/shared`, `fumadocs-ui/i18n`, `@fumadocs/language/zh-cn`, `./i18n`, `./shared` |

---

#### 3.7 `cn.ts` — Class Name Utility

| Field | Detail |
|-------|--------|
| **Full name** | `@/lib/cn.cn` |
| **Purpose** | Re-exports `tailwind-merge`'s `twMerge` as `cn` for conditional class merging. |
| **Usage** | `className={cn('base-class', condition && 'conditional-class')}` |

---

### 4. Route Handlers (`src/app/`)

| Route | File | Purpose |
|-------|------|---------|
| `/api/search` | `api/search/route.ts` | FlexSearch static index API endpoint |
| `/docs/[[...slug]]` | `docs/[[...slug]]/page.tsx` | Dynamic docs page renderer (en) |
| `/zh/docs/[[...slug]]` | `zh/docs/[[...slug]]/page.tsx` | Dynamic docs page renderer (zh) |
| `/og/docs/[...slug]` | `og/docs/[...slug]/route.tsx` | OG image generation per page |
| `/llms.txt` | `llms.txt/route.ts` | LLM-friendly concise text index |
| `/llms-full.txt` | `llms-full.txt/route.ts` | LLM-friendly full content |
| `/llms.mdx/docs/[[...slug]]` | `llms.mdx/docs/[[...slug]]/route.ts` | Per-page markdown content for LLMs |
| `/rss.xml` | `rss.xml/route.ts` | RSS feed (en) |
| `/zh/rss.xml` | `zh/rss.xml/route.ts` | RSS feed (zh) |
| `/export/epub` | `export/epub/route.ts` | EPUB export (en) |
| `/zh/export/epub` | `zh/export/epub/route.ts` | EPUB export (zh) |

---

### 5. Configuration Files

| File | Purpose |
|------|---------|
| `source.config.ts` | Fumadocs MDX config: remark plugins (AutoTypeTable, MdxFiles, Mermaid), rehype code options (Twoslash, themes), last-modified plugin |
| `next.config.mjs` | Next.js config with Fumadocs static export settings |
| `tsconfig.json` | TypeScript config — extends `@repo/typescript-config/nextjs.json` from the shared `packages/typescript-config/` workspace |
| `vitest.config.ts` | Vitest config: jsdom environment, CSS ignore, path aliases |
| `eslint.config.mjs` | ESLint flat config with Next.js rules |
| `postcss.config.mjs` | PostCSS with `@tailwindcss/postcss` |

## Project Directory Tree

```
lingchu-bot/
├── .agents/                          # Trae/Codex skill definitions
│   └── skills/
│       ├── available-skills/         # Skill routing index
│       ├── engineering-workflow/     # GitNexus, delivery loop, design, frontend quality, issue planning
│       └── tool-workflows/           # Context7 docs, prek/Husky hooks, skill management
├── .claude/                          # Claude Code skill definitions (subset of .agents/)
│   └── skills/
├── .trae/                            # Trae IDE configuration
│   ├── rules/                        # Always-applied rules
│   │   └── git-commit-message.md     # Gitmoji + Conventional Commits spec
│   └── skills/                       # Trae skill definitions (mirror of .agents/)
├── .github/
│   ├── .markdownlint.jsonc            # Per-directory override: disables MD022/MD032 for .github docs
│   └── note/AGENTS-zh.md            # Chinese translation of AGENTS.md
├── .husky/                           # Git hooks (pre-commit, commit-msg, prepare-commit-msg)
├── src/
│   └── plugins/nonebot_plugin_lingchu_bot/   # Core Python plugin
│       ├── __init__.py               # Plugin entry point, matcher registration
│       ├── core/
│       │   ├── async_utils.py        # fire_and_forget helper for discardable background tasks
│       │   ├── config.py             # Plugin config model (Pydantic)
│       │   ├── runtime_config.py     # Runtime configuration helpers
│       │   └── bot_state.py          # Two-tier bot state (global + per-platform) with JSON5 persistence
│       ├── database/
│       │   ├── json5_store/          # JSON5-based key-value store (package)
│       │   ├── models/               # ORM models package (nonebot_plugin_orm)
│       │   │   ├── __init__.py       # Re-exports 11 models + utc_now
│       │   │   ├── message.py       # MessageRecord, AuditRecord, utc_now
│       │   │   ├── blocklist.py     # BlocklistEntry
│       │   │   ├── registry.py      # Platform, Adapter, ProtocolImplementation
│       │   │   └── identity.py      # IdentityUser, PlatformAccount, PlatformIdentityGroup, IdentityMembership, PermissionGrant
│       │   └── orm_crud/             # Async CRUD helpers package
│       │       ├── __init__.py       # Re-exports CRUD functions
│       │       ├── _base.py         # DatabaseError, helpers, session
│       │       ├── _single.py        # create, get_one, update, delete, exists, count, get_or_create, update_or_create
│       │       └── _bulk.py          # upsert, bulk_create, list_items, async_iterate_safe
│       ├── handle/
│       │   ├── menu.py               # Menu system (pages, sections, features, availability)
│       │   └── qq/                   # QQ platform handlers
│       │       ├── commands/         # Shared QQ command definitions (Alconna matchers, triggers)
│       │       │   ├── triggers.py   # Command trigger words (zh/en)
│       │       │   ├── mute.py       # Mute/unmute commands
│       │       │   ├── member.py     # Member management commands
│       │       │   ├── block.py      # Blocklist commands
│       │       │   ├── bot_state.py  # Bot state commands (silence/speak/boot/shutdown)
│       │       │   ├── announcement.py # Announcement command
│       │       │   ├── remote.py     # Remote management commands (8 cross-group commands)
│       │       │   ├── profile.py    # Group profile commands
│       │       │   ├── lifecycle.py  # Bot lifecycle command
│       │       │   ├── kick.py       # Kick command
│       │       │   └── common.py     # Shared command helpers (selected_adapter_handle)
│       │       └── adapters/
│       │           ├── onebot11/     # OneBot V11 protocol handlers
│       │           │   ├── default/  # Default implementation handlers
│       │           │   │   ├── remote.py # Remote management handlers (8 commands)
│       │           │   │   ├── announcement.py # Version-gated announcement handler
│       │           │   │   └── ...   # mute, member, block, kick, profile, menu, lifecycle, test, bot_state
│       │           │   ├── llonebot/ # LLOneBot extensions (announcement)
│       │           │   └── napcat/   # NapCat extensions (announcement, profile)
│       ├── i18n/                     # Babel/gettext translations (en, zh)
│       ├── migrations/                # Alembic database migration scripts
│       ├── platforms/                # Adapter registry and platform-owned permission definitions
│       │   ├── registry.py          # Cross-platform capability & adapter selection
│       │   └── qq/permissions.py    # QQ default identity groups and runtime identity resolution
│       ├── permissions/              # UID identity, platform account, command grant & SUPERUSERS APIs
│       ├── repositories/             # Data access layer
│       │   ├── __init__.py         # Package init
│       │   ├── blocklist.py         # Blocklist repository
│       │   ├── message_store.py     # Message store repository
│       │   ├── permissions.py       # Permission-system ORM repository
│       │   └── registry.py          # Platform/adapter/protocol registry seeding
│       ├── services/                 # Business logic services
│       │   └── message_store.py     # Message storage service
│       └── start/                    # Startup & initialization
│           └── startup.py           # Startup hooks
├── apps/
│   └── docs/                         # Fumadocs documentation site
│       ├── content/docs/             # MDX content
│       │   ├── index.mdx             # Docs landing page (en)
│       │   ├── index.zh.mdx          # Docs landing page (zh)
│       │   ├── meta.json             # Navigation config (en)
│       │   ├── meta.zh.json          # Navigation config (zh)
│       │   ├── project-policy.mdx    # Contribution/security/license policy
│       │   ├── user-guide/           # User-facing documentation
│       │   │   ├── overview.mdx      # Bot overview & capabilities
│       │   │   ├── quick-start.mdx   # Installation & first run
│       │   │   ├── commands.mdx      # Commands overview (links to platform-specific pages)
│       │   │   ├── configuration.mdx # Configuration options
│       │   │   └── troubleshooting.mdx # Common issues & solutions
│       │   ├── platforms/            # Platform-specific documentation (NEW)
│       │   │   ├── index.mdx         # Platforms overview (layer model)
│       │   │   └── qq/               # QQ platform docs
│       │   │       ├── overview.mdx  # QQ platform overview (protocol priority, implementation matrix)
│       │   │       ├── commands.mdx  # Full QQ command reference (incl. remote management)
│       │   │       └── onebot-v11/   # OneBot V11 protocol docs
│       │   │       │   ├── overview.mdx  # Protocol overview
│       │   │       │   ├── default.mdx   # Default implementation
│       │   │       │   ├── napcat.mdx    # NapCat implementation
│       │   │       │   └── llonebot.mdx  # LLOneBot implementation
│       │   └── developer-guide/      # Developer documentation
│       │       ├── introduction.mdx  # Project structure & architecture
│       │       ├── adapter-guide.mdx # Adapter selection & configuration
│       │       ├── message-store.mdx # Message storage service
│       │       ├── workflow.mdx      # Development workflow
│       │       ├── commit-style.mdx  # Commit conventions
│       │       ├── i18n.mdx          # Internationalization guide
│       │       ├── testing-ci.mdx    # Testing & CI pipeline
│       │       └── gitnexus.mdx      # GitNexus code intelligence
│       ├── src/
│       │   ├── app/                  # Next.js App Router
│       │   │   ├── layout.tsx        # Root layout (en)
│       │   │   ├── docs/             # Docs pages & layout
│       │   │   ├── zh/               # Chinese locale pages
│       │   │   ├── api/search/       # Search index API
│       │   │   ├── og/               # OG image generation
│       │   │   ├── llms.txt/         # LLM-friendly text routes
│       │   │   ├── rss.xml/          # RSS feed routes
│       │   │   └── export/epub/      # EPUB export routes
│       │   ├── components/           # React components
│       │   │   ├── mdx.tsx           # MDX component registry
│       │   │   ├── graph-view.tsx    # Document relationship graph
│       │   │   ├── llm-badge.tsx     # AI-friendly docs badge
│       │   │   ├── provider.tsx      # App-wide context provider
│       │   │   ├── search.tsx        # Full-text search dialog
│       │   │   └── mdx/mermaid.tsx   # Mermaid diagram renderer
│       │   ├── lib/                  # Shared logic
│       │   │   ├── source.ts         # Content source API
│       │   │   ├── build-graph.ts    # Graph data builder
│       │   │   ├── rss.ts            # RSS feed generator
│       │   │   ├── i18n.ts           # i18n configuration
│       │   │   ├── locale.ts         # Locale switch helper (extracted from provider.tsx)
│       │   │   ├── shared.ts         # Shared constants
│       │   │   ├── layout.shared.tsx # Layout configuration
│       │   │   └── cn.ts             # Class name utility
│       │   └── __tests__/            # Vitest test files (12 files, 60 tests)
│       ├── source.config.ts          # Fumadocs MDX pipeline config
│       ├── next.config.mjs           # Next.js config
│       ├── vitest.config.ts          # Test config
│       └── eslint.config.mjs         # Lint config
├── packages/
│   ├── eslint-config/                # Shared ESLint configs (base, next, react-internal)
│   ├── typescript-config/            # Shared TS configs (base, nextjs, react-library)
│   └── ui/                           # Shared UI components (button, card, code)
├── docker/                          # Docker runtime support scripts (gunicorn, start.sh)
├── schema/                          # JSON Schemas for config files
│   ├── config.schema.json5         # Schema for config.json5
│   └── bot_state.schema.json5      # Schema for bot_state.json5
├── tools/                           # Standalone utility tools
│   ├── __init__.py
│   └── adapter_loader.py           # Deprecated adapter on-demand loader (Milky, QQ, OneBot V12)
├── tests/                            # Python test suite
│   └── handle/commands/              # Command handler tests
│       ├── test_remote.py            # Remote management command tests
│       ├── test_menu.py              # Menu system tests
│       ├── test_command_triggers.py  # Command trigger catalog tests
│       └── ...                       # mute, member, block, kick, announcement, etc.
├── Dockerfile                        # Container runner (nb-cli generated)
├── docker-compose.yml                # Docker Compose config
├── pyproject.toml                    # Python project config (uv, ruff, pyright, pytest)
├── package.json                      # Monorepo root (pnpm + Turborepo)
├── Taskfile.yml                      # Task runner for CI/local commands
├── prek.toml                         # Prek (Rust pre-commit) config — single source of truth for pre-commit hooks
├── CHANGELOG.md                      # Changelog
├── README-zh.md                      # Chinese README
├── Repository-Policy.md              # Repository policy (English)
├── SECURITY.md                       # Security policy
├── CODE_OF_CONDUCT.md                # Code of conduct
├── CONTRIBUTING.md                   # Contributing guide
└── AGENTS.md                         # This file — project context for AI agents
```

## Core Module Dependencies

```
┌──────────────────────────────────────────────────────────────────┐
│                        apps/docs                                  │
│                                                                   │
│  layout.tsx ──► provider.tsx ──► RootProvider (fumadocs)         │
│       │                           ├── i18n context                │
│       │                           └── search.tsx (FlexSearch)    │
│       │                                                          │
│       ├──► layout.shared.tsx ──► i18n.ts, shared.ts             │
│       │                                                          │
│       └──► docs/[[...slug]]/page.tsx ──► source.ts              │
│                                              ├── build-graph.ts  │
│                                              │     └── graph-view.tsx │
│                                              ├── rss.ts          │
│                                              └── shared.ts       │
│                                                                   │
│  mdx.tsx ──► Accordion, Tabs, Steps, Files, TypeTable,          │
│              AutoTypeTable, Mermaid, Twoslash, ImageZoom         │
│              └── mermaid.tsx ──► mermaid-utils.ts (DOMPurify)   │
│                                                                   │
│  Route handlers:                                                  │
│    /og/*     ──► source.ts (getPageImage)                        │
│    /llms*    ──► source.ts (getLLMText)                          │
│    /rss.xml  ──► rss.ts ──► source.ts                            │
│    /export   ──► fumadocs-epub ──► source.ts                     │
│    /api/search ──► FlexSearch static index                       │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│              Python Plugin (nonebot_plugin_lingchu_bot)           │
│                                                                   │
│  __init__.py ──► core/config.py ──► Pydantic settings            │
│              ──► core/runtime_config.py ──► runtime helpers       │
│              ──► core/async_utils.py ──► fire_and_forget helper    │
│              ──► platforms/registry.py ──► adapter resolution + protocol impls │
│              ──► database/orm_crud/ ──► models/ (records/audit/blocklist + identity + registry tables) │
│              ──► database/json5_store/ ──► JSON5 KV store      │
│              ──► repositories/blocklist.py ──► blocklist data    │
│              ──► repositories/message_store.py ──► data access   │
│              ──► repositories/registry.py ──► seed registry tables │
│              ──► services/message_store.py ──► business logic (platform_id/adapter_id/protocol_id) │
│              ──► start/ ──► startup hooks                        │
│              ──► i18n/ ──► Babel gettext catalogs                │
│                                                                   │
│  handle/menu.py ──► Menu system (pages, features, availability)  │
│                                                                   │
│  handle/qq/                                                       │
│    ├── commands/ ──► shared QQ command definitions                │
│    │   ├── triggers.py ──► command trigger words (zh/en)         │
│    │   ├── remote.py ──► remote management command matchers      │
│    │   └── ... ──► mute, member, block, announcement, etc.       │
│    └── adapters/                                                  │
│        ├── onebot11/default/ ──► OneBot V11 handlers             │
│        │   └── remote.py ──► 8 remote management handlers        │
│        └── onebot11/{llonebot,napcat}/ ──► OneBot extensions     │
└──────────────────────────────────────────────────────────────────┘
```

## Quick Start Guide

### Environment Setup

1. **Prerequisites**: Python 3.13+, Node.js 22+, pnpm 11+, uv (Python package manager)
2. **Clone**: `git clone https://github.com/xinvxueyuan/lingchu-bot.git && cd lingchu-bot`
3. **Install Python deps**: `uv sync --frozen`
4. **Install Node deps**: `pnpm install`
5. **Verify**: `task check && task test`

### Common Commands

| Task | Command |
|------|---------|
| Dev server (docs) | `pnpm --filter docs dev` |
| Build docs | `pnpm turbo run build --filter=docs` |
| Test docs | `pnpm --filter docs test` |
| Lint docs | `pnpm --filter docs lint` |
| Type check docs | `pnpm turbo run check-types --filter=docs` |
| Link validation | `pnpm --filter docs lint:links` |
| Docs CI (local) | `task ci:docs` |
| Test Python | `uv run -m pytest` |
| Lint Python | `uv run -m ruff check .` |
| Full check (all) | `task check && task test` |
| i18n extract | `task i18n` |

### Development Flow

1. Create a feature branch from `dev`
2. Make changes (Python, docs, or both)
3. Run relevant checks from the "Quick Reference" table above
4. Commit with gitmoji + conventional commit format
5. Push and create PR to `dev`

### Contribution Rules

- Follow commit convention: `✨ feat:`, `🐛 fix:`, `📝 docs:`, etc.
- Sync en/zh documentation for any doc changes
- Run `task check && task test` before requesting review
- Update `AGENTS.md` (and `AGENTS-zh.md`) when project structure or conventions change

### Documentation Update Mechanism

When the project structure, components, or conventions change:

1. **AGENTS.md** — Update the Project Directory Tree, Component Catalog, and Lessons Learned sections
2. **AGENTS-zh.md** — Sync the same structural changes to the Chinese version
3. **CLAUDE.md** — Propagate identical structural changes
4. **MDX docs** — Update `content/docs/` pages if user-facing behavior changes
5. **meta.json** — Add new doc pages to the navigation config
6. **i18n** — Run `task i18n` if Python user-facing strings change

> **Rule**: Any PR that modifies project structure, adds/removes components, or changes conventions MUST update AGENTS.md as part of the PR.

### Git Hooks Optimization

- **Pre-commit should conditionally trigger checks by file type (v3 — granularized)**: Use `git diff --cached --name-only --diff-filter=ACMR` to collect staged files, detect file extensions/paths via `has_pattern()`, skip Ruff/Pyright/ty/pytest when no Python changes. For frontend, split into 5 docs categories (CODE/TSX/CONTENT/STYLE/CONFIG) and 2 packages categories (CODE/CONFIG) to derive independent conditions: `NEEDS_LINT` (skip ESLint for pure `.mdx`/`.json` content changes), `NEEDS_TYPE_CHECK` (any frontend change), `NEEDS_REACT_DOCTOR` (only `.tsx` changes), `NEEDS_DOCS_TEST` (skip Vitest for pure `.css` style-only changes) — saves 30-90 seconds depending on change type
- **CI workflows should mirror pre-commit v3 granularization**: The `🧪-ci.yml` workflow uses a `changes` detection job that outputs boolean flags (`python`/`markdown`/`frontend`/`frontend-code`/`frontend-style`/`frontend-content`/`frontend-tsx`) via `git diff --name-only` between PR base or push `HEAD~1`. Downstream jobs use `needs.changes.outputs.<flag> == 'true'` in `if` conditions: `static-analysis` (Python or markdown), `tests` (Python), `docs-check` (any frontend). Within `docs-check`, ESLint runs on `frontend-code || frontend-style` (matches `NEEDS_LINT`), check-types on any frontend (matches `NEEDS_TYPE_CHECK`), Vitest on `frontend-code || frontend-content` (matches `NEEDS_DOCS_TEST`, skips pure `.css`). `auto-format` uses `always()` with `needs.<job>.result != 'failure'` to handle skipped upstream jobs. The `🩺-react-doctor.yml` workflow narrows `paths` to `.tsx` only (matches `NEEDS_REACT_DOCTOR`). This consistency ensures local and CI behavior match.
- **Signed-off-by appending needs trailer block detection**: When existing trailers (e.g., `Closes #`, `BREAKING CHANGE:`, `Reviewed-by:`) are present, append to the same block (no blank line separation); only use blank line separation when no trailers exist
- **Blank line cleanup must not break message structure**: `sed '/^$/N;/^\n$/d'` removes all consecutive blank lines, breaking subject-body-trailer structure; only compress ≥3 consecutive blank lines to 2
- **Duplicate signature detection must ignore trailing whitespace**: `grep -qF` may misjudge due to trailing whitespace differences; strip trailing whitespace with `sed 's/[[:space:]]*$//'` first, then use `grep -qxF` for exact full-line matching
- **Empty message body should not append Signed-off-by**: Empty commit messages are caught by format validation; appending a signature to an empty file is meaningless

### Switching i18n Default Locale

- **Fumadocs language packs**: `@fumadocs/language` exports locale packs for languages it supports (e.g., `zh-cn`, `zh-tw`); English (`en-us`) is built-in by default and does not need a separate import. When switching the default language to English, `layout.shared.tsx` only needs `preset('zh', zhCN())` for Chinese — no English pack import is required. Always check `@fumadocs/language` exports for the current list before assuming a locale is or isn't available.
- **Override locale in test environment rather than changing assertions**: After changing Python `DEFAULT_LOCALE` from `zh_CN` to `en_US`, all tests asserting Chinese translations will fail. The correct approach is to add `"lingchu_locale": "zh_CN"` in `tests/conftest.py`'s `nonebot.init()` to override back to Chinese, avoiding modifying hundreds of test assertions individually, while also validating the locale configuration override mechanism.
- **Fumadocs i18n file naming convention**: Default language MDX files have no suffix (`page.mdx`), non-default language files have a locale suffix (`page.zh.mdx`); same for `meta.json`. When switching the default language, content files must be renamed in bulk.

### Bypassing lru_cache for Multi-Locale Tests

- **Problem**: The i18n module's `_read_configured_locale()` is decorated with `@lru_cache(maxsize=1)`. Once it reads the locale from NoneBot config on first call, the result is cached for the whole session. This prevents running the same test against both `zh_CN` and `en_US` in one pytest session — the second locale never takes effect because the cached value is returned.
- **Solution**: The `configured_locale` fixture in `tests/conftest.py` calls `_read_configured_locale.cache_clear()` to drop the cached value, then `monkeypatch.setattr(...)` replaces the function so it returns the parametrized locale. This lets parametrized tests switch locale per parameter without session-wide caching interference.
- **When to use which fixture**: Use `locale` (no global mutation) for tests that pass `locale=` explicitly to `gettext()`/`ngettext()`. Use `configured_locale` only for tests that depend on `get_configured_locale()` or `_()`, where the cached function would otherwise return the wrong locale.

### CI and Lint Coverage for New Paths

When adding, moving, or renaming files or directories, verify that CI and lint configurations still cover them. Check and update:

1. **Markdown lint** — `markdownlint-cli2` glob patterns in `Taskfile.yml` and `package.json` scripts
2. **ESLint / TypeScript** — `tsconfig.json` includes, `eslint.config` overrides, Vitest coverage paths
3. **Ruff / Pyright / ty** — `pyproject.toml` source paths and exclusion patterns
4. **GitHub Actions** — trigger paths in `on.push.paths` / `on.pull_request.paths`
5. **GitNexus** — re-analyze if new source directories are introduced

Example: adding `.github/note/` required updating the `markdownlint-cli2` glob to include `.github/**/*.md` (already covered), but if the directory had been `.github/notes/` or a new top-level `legal/` dir, the lint command would have silently skipped it.

### Multi-Language File Synchronization

When a file has translated counterparts (e.g., `AGENTS.md` ↔ `.github/note/AGENTS-zh.md`, `CONTRIBUTING.md` ↔ `.github/note/CONTRIBUTING-zh.md`), changes to one version MUST be propagated to all other language versions. This includes:

1. **Content changes** — any substantive edit (new section, updated command, corrected fact) must be reflected in every language version
2. **Structural changes** — adding/removing headings, reordering sections, or changing links must be mirrored
3. **Cross-references** — when a file references another file that was renamed or moved, update the link in all language versions
4. **Lint/CI configs** — when adding new files or directories, update glob patterns and check lists in all relevant configs (see "CI and Lint Coverage for New Paths" above)
5. **Documentation mirrors** — if a command or config snippet appears in `AGENTS.md`, `CONTRIBUTING.md`, `CLAUDE.md`, and `apps/docs/content/docs/`, update all of them

Rule of thumb: **after editing any file, search for its name or key phrases across the entire repo to find all copies and references that need updating.**

### Adapter Directory Structure Refactoring

When reorganizing adapter directories from `handle/qq/onebot/v11/default/group/` to `handle/qq/adapters/onebot11/default/`, several import path issues emerged:

1. **Relative import depth changes**: Moving files from `handle/qq/onebot/v11/default/group/` (6 levels deep) to `handle/qq/adapters/onebot11/default/` (5 levels deep) requires adjusting relative import dots. For example, `from ...i18n` becomes `from ....i18n` when accessing plugin root modules.

2. **Package `__init__.py` exports**: When tests import symbols like `onebot11_menu` or `milkybot_menu_pages` from adapter packages, the package `__init__.py` must explicitly re-export these symbols. Simply importing the module (e.g., `from . import menu`) is insufficient; you must also add `from .menu import onebot11_menu as onebot11_menu` to make the symbol accessible at the package level.

3. **Import sorting with Ruff**: After fixing import paths, run `ruff check` to verify import block sorting. Ruff's `I001` rule enforces alphabetical ordering within import blocks, and multi-line imports must maintain consistent formatting.

4. **Test import paths**: Test files using absolute imports (e.g., `from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import onebot11_menu`) require the target symbols to be explicitly exported in the package's `__init__.py`.

### Pre-Commit Verification Checklist

Before every commit, run the full verification pipeline. Do NOT skip even if you think changes are "only docs" — docs changes can break builds, type checks, and tests too.

**Mandatory sequence:**

1. `task check` — runs all static checks (Ruff lint/format, Markdown lint, ESLint, type check)
2. `task test` — runs Python pytest + docs Vitest
3. `task i18n` — if any user-facing strings changed, re-extract and compile translations
4. `gitnexus_detect_changes()` — verify change scope matches intent
5. Only then commit

**Common mistakes to avoid:**

- Skipping checks "because it's just a doc change" — docs changes can break builds, type generation, and i18n routing
- Forgetting `task i18n` after modifying translatable strings — stale `.po`/`.mo` files cause runtime locale errors
- Committing without running `gitnexus_detect_changes()` — you may miss unintended side effects

### PowerShell Commit Syntax

PowerShell does not support bash heredoc (`<<'EOF'`). For multi-line commit messages in PowerShell, use a temp file:

```powershell
$msg = @"
📝 docs(i18n): 切换默认语言为英文

- body line 1
- body line 2
"@
$msg | Out-File -Encoding utf8 -FilePath $env:TEMP\commit-msg.txt
$env:HUSKY='0'; git commit -F $env:TEMP\commit-msg.txt
Remove-Item $env:TEMP\commit-msg.txt
```

Or use single-line `-m` with `\n` (less readable for long bodies).

### CI Failure Patterns

When pushing to GitHub, check all three CI workflows (not just the one that passed):

1. **pre-commit.ci** — remote CI fallback that runs `end-of-file-fixer`, `trailing-whitespace`, etc. When GitHub Actions API has issues, pre-commit.ci ensures basic checks still run. If it reports "files were modified by this hook", those files lack trailing newlines or have trailing whitespace. Fix locally and push again. Common culprits: `.po`/`.pot` files (Babel output may omit trailing newline), `.turbo/preferences/` JSON files, generated files.
2. **CodeQL / GitHub Pages deploy** — `Requires authentication` errors can be caused by: (a) **GitHub infrastructure incidents** — check [githubstatus.com](https://www.githubstatus.com/) first; (b) **repository permission issues** — if status page is green, then check Settings → Actions → General → Workflow permissions (must be "Read and write") and ensure `id-token: write` is in the workflow's `permissions` block for OIDC-dependent jobs (Pages deploy, CodeQL).
3. **`.next` cache staleness** — after renaming/moving route directories (e.g., `en/` → `zh/`), the `.next/dev/types/validator.ts` cache may reference old paths and cause TypeScript errors. Delete `apps/docs/.next/` and re-run `task check` before committing.

Rule of thumb: **after every push, wait for all CI workflows to complete and investigate failures before moving on.**

### Use Existing Skills Before Manual Work

Before manually running checks or fixing issues, check if a skill already handles it:

- **pre-commit.ci failures** → use the **tool-workflows** hook route (`.agents/skills/tool-workflows/SKILL.md`) to reproduce and fix pre-commit hook failures locally, instead of manually running each hook
- **Code intelligence** → use **GitNexus** skills instead of manual grep/find
- **Library docs** → use **Context7 / find-docs** instead of web search
- **GitHub workflows** → use **GitHub** skills for PR/issue/CI operations

Rule of thumb: **when a CI check fails or you need to do something repetitive, first check `.agents/skills/` for an existing skill that automates it.**

### React Doctor Integration

- **CLI auto-generated files need manual customization**: `npx react-doctor@latest install` creates a GitHub Actions workflow and npm script, but they won't match project conventions. After running the CLI, always customize: emoji workflow name, pinned action SHAs, path filters for trigger, `project` scoping for monorepos, and `blocking` level.
- **Avoid `millionco/react-doctor@v2` action until upstream fixes land**: The action has known bugs — detached HEAD causing diff fallback, ANSI escape codes leaking into PR comments (upstream PR #80 pending). Use CLI directly (`npx react-doctor@latest`) with `NO_COLOR=1` env var instead. Re-evaluate once upstream releases a fix.
- **`--fail-on error` not `warning` in CI**: React Doctor's `blocking: warning` causes CI to fail on any warning (exit code 1). Use `--fail-on error` to only block on errors; warnings should be informational. In pre-commit hooks, same principle — block on errors only.
- **`doctor.config.ts` should document rule overrides**: When setting rules to `warn`/`off`, add a comment explaining why (e.g., fumadocs-generated exports that are framework-required but flagged as unused). This prevents future contributors from blindly re-enabling them.
- **SVG elements must use `createElementNS`**: Even in test code, `document.createElement('svg')` is incorrect — use `document.createElementNS('http://www.w3.org/2000/svg', 'svg')`. Linters (Edge Tools, hint) flag this, and it affects SVG rendering behavior.
- **`useMDXComponents` vs `getMDXComponents`**: Fumadocs MDX convention exports `useMDXComponents` for the MDX provider pattern (`providerImportSource` in `source.config.ts`). Even if the project currently passes `getMDXComponents()` explicitly via `components` prop, `useMDXComponents` should be kept as it's the standard fumadocs entry point for automatic MDX component resolution. Suppress `deslop/unused-export` in `doctor.config.ts` for framework-required re-exports.

### Verify Framework Syntax Against Official Docs

When writing MDX content for Fumadocs (or any framework), **never assume syntax** — always verify against official documentation and the project's actual setup. Examples:

- Fumadocs uses `<Callout>` JSX component for admonitions, **not** GitHub-style `>[!NOTE]` blockquotes. The `>[!NOTE]` syntax renders as a plain blockquote, not a styled callout.
- Before using any framework-specific component or syntax in MDX, check: (1) the framework's official docs via Context7 / find-docs, (2) existing usage in the project's content files, (3) the MDX component provider setup (e.g., `source.config.ts`, `mdx.tsx`).

Rule of thumb: **if you haven't seen the syntax used in the project's existing content files, verify it against official docs before writing it.**

### OneBot V11 Handler Consolidation & Adapter Deprecation

- **Code duplication across 5+ OneBot V11 handler files** was solved by centralizing shared helpers and constants in `onebot11/default/common.py` (`bot_self_id_safe()`, `bot_id()`, `default_block_reason()`, `default_admin_reason()`, `check_self_target()`, `store_block_record()`, `check_target_privilege()`, `check_bot_privilege()`, `record_command_audit()`; constants `QQ_PLATFORM_ID`, `ONEBOT_V11_ADAPTER_ID`, `MUTE_DURATION_MIN`, `MUTE_DURATION_MAX`).
- **Missing audit trail** was solved by adding `record_command_audit()` — every management command now records operator, target, action, and reason after successful execution.
- **Missing privilege checks** were solved by adding `check_target_privilege()` (prevents operating on admins/owners) and `check_bot_privilege()` (prevents calling APIs the bot lacks permission for).
- **Adapter deprecation** (Milky, QQ, OneBot V12) was solved by removing them from `platforms/registry.py` and the startup hook flow (`handle/qq/adapters/__init__.py`, `handle/menu.py`), while preserving source files with `DEPRECATED = True` markers and deprecation docstrings.
- **Reuse need** was solved by the standalone `tools/adapter_loader.py` module, which provides `load_deprecated_adapter()`, `load_and_init_deprecated_adapter()`, and `list_deprecated_adapters()` for on-demand loading without participating in the normal startup flow.
- **Key lesson**: When deprecating adapters, move them out of the startup flow but keep source code with deprecation markers; provide a standalone loader tool for on-demand access. When consolidating duplicated handler logic, extract shared helpers into a single `common.py` module rather than leaving copies in each handler file.

### Permission API Integration & Deprecation Enforcement
- Permission system now actively verifies user roles via OneBot V11 `get_group_member_info` API when event data is incomplete, ensuring access control is enforced.
- Deprecated adapters (`~milky`, `~qq`, `~onebot.v12`) now trigger `PlatformAdapterDeprecatedError` with clear guidance, instead of being treated as "unknown".
- Platform permission modules are discovered through `PlatformProfile.permission_module` field in the registry, eliminating hardcoded module paths in `permissions/platforms.py`.
- Key lesson: when deprecating features, provide clear exit-time feedback rather than silent removal; when permission gates rely on passive event data, add active API verification as a fallback.

### CI Type-Checking for Optional Dependencies & i18n Maintenance
- When moving dependencies to `[project.optional-dependencies]` (e.g., `deprecated-adapters`), the CI test jobs must install them with `uv sync --frozen --extra deprecated-adapters` — otherwise test files importing those packages fail with `ImportError`.
- Pyright/ty exclude lists in `pyproject.toml` must include deprecated adapter source directories (e.g., `src/.../handle/qq/adapters/milky`) — otherwise type-checking fails on `reportMissingImports` for packages not installed in the static-analysis environment.
- **`pybabel update` behavior**: Automatically marks removed strings as obsolete (`#~` prefix) and adds `fuzzy` flags to entries with similar msgids. After running `pybabel update`, manually review fuzzy entries, remove the `fuzzy` flag, and correct translations.
- **Stale msgid handling**: When function signatures change (e.g., removing a `reason` parameter from a format string), the old msgid becomes stale. `pybabel update` detects the similarity and creates a fuzzy entry, but the msgstr must be manually updated to match the new msgid.
- **Key lesson**: When deprecating code that has i18n strings, run `task i18n` after code changes to extract/update translations. Check for fuzzy entries and obsolete entries. When excluding directories from type-checking, add them to both `[tool.pyright]` and `[tool.ty.src]` exclude lists.

### OneBot V11 Image API File Field Format
- NapCat / OneBot V11 图片类 API（如 `set_group_portrait`）的 `file` 字段要求 `http(s)://`、`base64://` 或 `file://` 格式，直接传入裸本地路径（如 `C:\...` 或 `/tmp/...`）会被拒绝（`retcode=1200`, `file字段可能格式不正确`）。
- **Fix**: 将本地文件读取为 bytes，base64 编码后以 `base64://<encoded>` 格式传入。选择 `base64://` 而非 `file://` 的原因：bot 与 NapCat 可能运行在不同容器/文件系统中，`base64://` 在所有部署场景下都能工作。
- **Async file I/O**: 在 async 函数中读取文件应使用 `await asyncio.to_thread(path.read_bytes)` 避免 `ASYNC240` 违规；直接调用 `path.read_bytes()` 会被 ruff 标记。
- **Test pattern**: 测试涉及文件读取的函数时，使用 `tmp_path` fixture 创建真实临时文件（`tmp_path / "test.png"` + `write_bytes(b"...")`），而非指向不存在的路径（如 `Path("/tmp/test.png")`）。
- **Key lesson**: 调用 OneBot V11 图片/文件类 API 时，务必将 `file` 字段转换为协议要求的格式；测试断言应验证格式前缀（`base64://`）而非裸路径字符串。

### Pending Rollbacks

Rule suppressions and temporary workarounds that should be reverted once the triggering condition changes. Review this section periodically (e.g., when updating dependencies or refactoring).

| What | Where | Why suppressed | Rollback condition |
|------|-------|---------------|-------------------|
| Pyright/ty exclude `src/.../adapters/milky` | `pyproject.toml` `[tool.pyright]` and `[tool.ty.src]` | Milky adapter moved to optional dependency; static-analysis env doesn't install it, causing `reportMissingImports` | **Rollback condition met**: Milky adapter has been fully deleted; remove this entry from `pyproject.toml` exclude lists |
| `deslop/unused-export: "off"` | `doctor.config.ts` | `useMDXComponents` in `mdx.tsx` is a framework-required re-export but currently unused (no `providerImportSource` in `source.config.ts`) | Remove this suppression once `useMDXComponents` is actually consumed (e.g., after adding `providerImportSource` to `source.config.ts` or importing it elsewhere) |
| CLI instead of `millionco/react-doctor@v2` action | `.github/workflows/🩺-react-doctor.yml` | Upstream action has bugs: detached HEAD, ANSI leak in PR comments (PR #80 pending) | Switch back to the action once upstream releases a fix (monitor PR #80) |

### Blocklist Kick Behavior: reject_add_request=False

When kicking blocked users from groups, the `reject_add_request` parameter is set to `False` (not `True`). This allows previously blocked users to request re-joining the group after being unblocked or after their block expires. If the business requirement changes to permanently prevent re-joining, update `_kick_blocked_user()` in `handle/qq/adapters/onebot11/default/block.py` and corresponding test assertions.

- **Non-component exports break Fast Refresh**: Utility functions (`getMermaidConfig`, `sanitizeMermaidSvg`, `renderMermaidSvg`) exported from a component file (`mermaid.tsx`) trigger `react-doctor/only-export-components`. Extract them to a separate non-component module (e.g., `mermaid-utils.ts`) and import from there. Update test imports accordingly.
- **`/llms.txt` is a route handler, not a static file**: When linking to Next.js route handlers from components, use `<Link>` (not plain `<a>`) — they're internal routes that benefit from client-side navigation.

### Use CLI Auto-Fix Tools Before Manual Edits

When lint or type-check tools report mechanical issues (import sorting, unused imports, formatting, simple style violations), **always prefer CLI auto-fix flags over manual one-by-one edits**. This saves significant time and avoids human error.

| Tool | Auto-fix command | What it fixes |
|------|------------------|---------------|
| Ruff | `uv run -m ruff check --fix .` | Import sorting (I001), unused imports (F401), unused variables, simple style violations |
| Ruff format | `uv run -m ruff format .` | Code formatting (line length, whitespace, quotes) |
| Markdownlint | `pnpm exec markdownlint-cli2 --fix {{.MD_GLOB}}` | Markdown formatting (MD060, MD009, etc.) |
| ESLint | `pnpm --filter docs lint --fix` | JS/TS lint issues (unused vars, formatting) |
| Prek | `prek run --all-files` | Runs all pre-commit auto-fixers in sequence |

<Callout type="warn" title="What auto-fix CANNOT do">

Auto-fix tools handle **mechanical** issues only. They cannot fix:
- Logic errors (TRY300 — move return to else block requires understanding control flow)
- Complexity issues (PLR0911, PLR0913, C901 — require extracting helper functions)
- Type mismatches (Pyright/ty — require understanding the intended type)
- Boolean positional args (FBT001/FBT002 — require deciding keyword-only vs positional)

For these, manually refactor after running auto-fix. Use `# noqa: <rule>` comments for cases where the rule is intentionally violated (e.g., `PLR0913` for handlers with many required params, following the `block.py` pattern).

</Callout>

**Workflow:**
1. Run `uv run -m ruff check --fix .` first — fixes imports and simple style issues
2. Run `uv run -m ruff format .` — applies formatting
3. Run `uv run -m pyright .` and `uv run -m ty check` — identify remaining type/logic issues
4. Manually fix only what auto-fix cannot handle (complexity, logic, type mismatches)
5. Re-run `task check` to verify all issues are resolved

**Rule of thumb**: If you find yourself manually fixing more than 2-3 instances of the same rule, stop and check if there's an auto-fix flag for it. Never manually fix I001 (import sorting) or F401 (unused imports) — always use `ruff check --fix`.

### Remote Management Commands (OneBot V11 only)

The 8 remote management commands (`远程禁言`, `远程解禁`, `远程全体禁言`, `远程全体解禁`, `远程踢出`, `远程拉黑`, `远程删黑`, `远程公告`) are OneBot V11 only. They are defined in `handle/qq/commands/remote.py` (Alconna matchers) and implemented in `handle/qq/adapters/onebot11/default/remote.py` (handlers).

Key behaviors:
- **Group ID resolution**: `<群号|群名称>` accepts `int` (direct), numeric `str` (parsed to int), or non-numeric `str` (fuzzy matched via `get_group_list`). Exact name match takes priority; substring containment is fallback. Multiple matches trigger `cmd_matcher.finish` asking for a more precise identifier.
- **Context validation**: Before executing, the bot checks it is in the target group, has admin role (for most commands), the target user is in the group, and the target is not the bot or sender.
- **Remote kick requires blocklist**: `远程踢出` only works on users already in the blocklist. Use `远程拉黑` first.
- **Remote announcement version gating**: Requires `LLOneBot >= 7.12.0` or `NapCat.Onebot >= 4.18.0`. The menu hides this command for unsupported implementations.

### Menu System Architecture

The menu system in `handle/menu.py` uses a layered `MenuPage` → `MenuSection` → `MenuFeature` → `MenuAvailability` model. When adding new commands:

1. Add the command trigger to `COMMAND_TRIGGERS` in `handle/qq/commands/triggers.py` (both zh and en).
2. Add a `MenuFeature` entry to `MENU_FEATURES` in `handle/menu.py` with the correct `command_key`, `section_id`, `summary`, `usage`, `platform_capability`, and `availability` tuple.
3. If creating a new menu page (top-level category like `remote-management`), add a `MenuPage` entry to `MENU_PAGES` and ensure it has a `command` field for the submenu trigger.
4. Update `EXPECTED_TRIGGERS` in `tests/handle/commands/test_command_triggers.py` to include the new trigger.
5. Update menu tests in `tests/handle/commands/test_menu.py` to cover the new feature's visibility under different adapter/implementation contexts.
6. Update `apps/docs/content/docs/platforms/qq/commands.mdx` (and `.zh.mdx`) with the new command reference.

### Docs Site Structure: Platform → Protocol → Implementation

The docs site (`apps/docs/content/docs/`) separates platform-specific documentation into a dedicated `platforms/` section:

```
platforms/
├── index.mdx              # Layer model overview (platform → protocol → implementation)
└── qq/                    # QQ platform
    ├── overview.mdx       # Protocol priority, implementation matrix
    ├── commands.mdx       # Full QQ command reference (incl. remote management)
    └── onebot-v11/        # OneBot V11 protocol
        ├── overview.mdx   # Protocol overview, runtime detection
        ├── default.mdx    # Default implementation (core commands + remote management)
        ├── napcat.mdx     # NapCat extensions (announcement + avatar)
        └── llonebot.mdx   # LLOneBot extensions (announcement)
```

The `user-guide/commands.mdx` is now a high-level overview that links to the platform-specific pages instead of duplicating command details. When adding new commands or changing availability:

1. Update `platforms/qq/commands.mdx` (and `.zh.mdx`) with the full command reference
2. Update the relevant implementation page (e.g., `platforms/qq/onebot-v11/napcat.mdx`) if the command is implementation-specific
3. Update `user-guide/commands.mdx` only if the high-level menu structure or filtering rules change
4. Update `developer-guide/introduction.mdx` if the project source structure changes

### Docs CI and Unit Test Coverage

When adding CI checks or unit tests for the docs site (`apps/docs/`), several pitfalls emerged:

1. **MDX table `|` breaks inline code spans**: Inside markdown table cells, `<群号|群名称>` is parsed as three table columns (`<群号`, `群名称>`), which exposes the `<...>` as JSX and causes "Unexpected end of file in name" build errors. Replace `|` with `或` / `_or_` (matching existing style, e.g., `<用户ID或@提及>`). This applies to both `.mdx` and `.zh.mdx` files.

2. **`fumadocs-mdx` node loader cannot handle image assets**: The `lint:links` script uses `register()` from `fumadocs-mdx/node` to load MDX files for link validation. When an MDX file imports a `.png`/`.jpg`/`.svg`, the loader's `load` hook calls `nextLoad`, reaching Node's default loader which throws `ERR_UNKNOWN_FILE_EXTENSION`. Fix by registering a `load` hook via `module.registerHooks()` (Node.js 23+) from `node:module` that returns `export default undefined;` for image file extensions. Add this at the top of `scripts/lint.mts` before importing `fumadocs-mdx/node`.

3. **`next-validate-link` URL resolution from root index pages**: Root index pages (e.g., `platforms/index.mdx`) have a URL without a trailing slash (`/docs/platforms`), so relative links like `./qq` resolve to `/docs/qq` instead of `/docs/platforms/qq`. Use absolute URLs (`/docs/platforms/qq/overview`) for links from root index pages. Directory links (e.g., `./onebot-v11`) must include a specific page suffix (`./onebot-v11/overview`) — bare directory links fail validation.

4. **Extract shared functions for testability**: When a function (e.g., `switchLocale` in `provider.tsx`) is defined inside a React component file, unit tests either can't import it or must duplicate the logic (which drifts from the real implementation). Extract such functions to a dedicated module (e.g., `src/lib/locale.ts`) and import from both the component and the test. This ensures tests verify the real export, not a stale copy.

5. **Mock `collections/server` in vitest to prevent MDX loading**: Tests that import from `src/lib/source.ts` transitively load MDX collection files via the `collections/server` alias, which vitest cannot parse as JavaScript (error: "Failed to parse source for import analysis"). Add `vi.mock('collections/server', () => ({ docs: { toFumadocsSource: () => ({}) } }))` at the top of the test file to stub the collection and prevent MDX file loading.

### GitHub Actions SHA Pinning Best Practices

- **Prefer commit SHA over annotated tag object SHA**: When pinning GitHub Actions to a version tag, the `git/refs/tags/{tag}` API returns the annotated tag object SHA, not the commit SHA. Use `git/tags/{sha}` to dereference annotated tags to their commit SHA. Pinning to the commit SHA is the documented best practice — it ensures the pin points to the actual code that was reviewed, not an intermediate Git object that could be re-created.
- **Don't trust comments over actual SHAs**: When auditing action pin versions, comments like `# pinned from actions/checkout@v6.0.3` may be stale. Always resolve the actual SHA via the GitHub API to verify it matches the claimed release tag.
- **Dependabot auto-maintains action pins**: Configure `package-ecosystem: "github-actions"` in `dependabot.yml` to automatically open PRs when actions release new versions. Use `groups` with `update-types: ["minor", "patch"]` to batch low-risk updates.

### Workflow Filename and Name Conventions

- **Use emoji-prefix + kebab-case for all workflow filenames**: All workflow files in `.github/workflows/` follow the pattern `<emoji>-<kebab-case-name>.yml` (e.g., `🧪-ci.yml`, `🩺-react-doctor.yml`). This makes workflows visually identifiable in file listings and the GitHub Actions UI.
- **Workflow `name:` field uses English**: The `name:` field appears in the GitHub Actions UI and should be in English for universal readability. Format: `<emoji> <English Name>` (e.g., `name: 📚 Docs Deploy`).
- **Keep filename emoji and `name:` emoji consistent**: The emoji in the filename should match the emoji in the `name:` field.
- **Search for filename references before renaming**: When renaming a workflow file, grep the entire repo for the old filename (including `.yml` extension) to find all references. Check AGENTS.md, CLAUDE.md, AGENTS-zh.md, MDX docs, skill files, and the workflow file itself (self-references in `paths:` triggers).

### .github Config Style Unification

- **English comments in all .github config files**: All YAML config files in `.github/` use English comments for consistency. This includes `dependabot.yml`, `labeler.yml`, `auto_assign.yml`, etc.
- **Remove broken `yaml-language-server: $schema=` lines**: If a config file has a `# yaml-language-server: $schema=` comment with an empty or invalid URL, remove the line. Only add the schema comment if a valid JSON schema URL exists.
- **Dependabot monorepo configuration**: Use `directories` (plural, supports glob patterns) instead of `directory` (singular) for npm ecosystems in pnpm/Turborepo monorepos. Use `groups` with `patterns` and `update-types` to merge minor/patch updates into a single PR across all workspace directories.

### Async Conversion: Fire-and-Forget Tasks and Async I/O

- **Fire-and-forget background tasks must retain strong references**: store scheduled tasks in a module-level `set` and attach done-callbacks that log exceptions via `logger.exception` and discard the reference. Without a strong reference, Python's garbage collector may cancel pending tasks before they complete.
- **Discardable sync operations block the event loop**: audit/telemetry DB writes and image cache writes inside async functions block the event loop. Convert DB writes to `fire_and_forget` (so they run as background tasks) and file I/O to `aiofiles` (`aiofiles.open` for read/write).
- **Prefer `asyncio.gather(..., return_exceptions=True)` over sequential `await` loops** for independent startup operations (registry seeding, superuser grants). Log per-item failures instead of aborting the whole batch — one failing item should not block the rest.
- **Async file I/O pattern**: when converting sync file I/O to async, use `aiofiles.os.makedirs`/`aiofiles.os.replace`/`aiofiles.os.unlink` for path operations and `aiofiles.open` for read/write, mirroring the pattern in `database/json5_store/_async_db.py`.
- **Keep sync variants of file-ensure functions for import-time use**: there is no event loop available at module load, so sync variants (e.g., `ensure_json5_dict_file_sync`) must remain for module-level callers; async variants (e.g., `ensure_json5_dict_file_async`) are for runtime callers inside `async def` functions.

### Database Module Splitting & Config Simplification

- **Test patch target updates**: When splitting a single module (e.g., `orm_crud.py`) into a package (e.g., `orm_crud/` with `_base.py`, `_single.py`, `_bulk.py`), all test `patch.object()` targets must be updated from module-level to sub-module-level. For example, `patch("...orm_crud.select", ...)` becomes `patch("...orm_crud._single.select", ...)`. Failing to update patch targets causes `AttributeError` at test time because the symbol is no longer on the package `__init__` — it's on the sub-module.
- **`nonebot_plugin_orm` model discovery with packages**: `nonebot_plugin_orm` discovers ORM models by scanning module paths. When converting `models.py` to a `models/` package, model discovery still works as long as `models/__init__.py` explicitly imports all model classes (e.g., `from .message import MessageRecord, AuditRecord`). Without explicit imports in `__init__.py`, the ORM will not register the tables and migrations will be empty.
- **`ensure_json5_dict_file_async` vs `write_json5_dict_file_async`**: `ensure_json5_dict_file_async` only creates a file if it does not already exist (idempotent ensure). For overwriting an existing file with new content (e.g., `bot_state.py` persisting state changes), use `write_json5_dict_file_async` instead — it unconditionally writes the file. Using `ensure_*` when you need `write_*` silently keeps stale data.
- **Removing backward-compatibility aliases is a breaking change**: Simplifying `RuntimeConfig.lingchu_adapter` to a single alias (removing `LINGCHUAdapter` and `LINGCHU_ADAPTER`) cleans up the config but breaks any user who referenced the old alias names in their `.env` or `config.json5`. Document the removal in the changelog and migration guide; only do this in pre-1.0 or when the project accepts breaking changes (see Agent Preferences: "pre-planning development stage").
