<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **lingchu-bot** (3241 symbols, 6306 relationships, 271 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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

- **Context7 / find-docs**: Use for current documentation for libraries, frameworks, SDKs, APIs, CLIs, and cloud services. Start with `resolve-library-id` unless the user provides an exact `/org/project` ID, then query docs with the full user question. Prefer this over web search for developer docs.
- **openai-docs**: Use for OpenAI product/API questions; prefer official OpenAI docs. (Routing-only — no local SKILL.md; loaded from Codex platform skills at runtime.)

### Code Intelligence And Git

- **GitNexus skills**: Use `.agents/skills/gitnexus/*` for architecture exploration, debugging, impact analysis, refactoring, PR review, and CLI operations. Follow the GitNexus requirements above before editing symbols or committing.
- **prek**: Use `.agents/skills/prek/SKILL.md` when setting up or running hook checks with `prek`.
- **GitHub skills**: Use for GitHub repository, issue, pull request, review-comment, CI, and publish/PR workflows.

### Development Workflow

- **delivery-loop**: Use `.agents/skills/delivery-loop/SKILL.md` for disciplined debugging, TDD, and code review loops. Routes to debug-investigation, TDD, or change-review references based on the task.
- **issue-planning**: Use `.agents/skills/issue-planning/SKILL.md` for PRDs, issue breakdown, triage, and refactor plans. Integrates with GitHub MCP tools for issue management.
- **design-prototyping**: Use `.agents/skills/design-prototyping/SKILL.md` for interface design exploration, design grilling, and throwaway prototypes before committing to implementation.

### Frontend And Docs Site

- **frontend-quality**: Use `.agents/skills/frontend-quality/SKILL.md` for React diagnostics, visual polish, accessibility, and health checks on the docs site (`apps/docs`). Includes react-doctor and frontend-polish references.
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

```
lingchu-bot/
├── src/plugins/nonebot_plugin_lingchu_bot/   # Core NoneBot plugin
│   ├── core/           # Config, platform info
│   ├── database/       # JSON5 store package, ORM models (records/audit/blocklist + registry) & CRUD helpers
│   ├── handle/         # Platform/protocol/implementation command handlers
│   │   └── qq/{group,onebot/v11,milky/v1_2}/    # QQ group handlers
│   ├── i18n/           # Babel/gettext translations
│   ├── migrations/     # Alembic database migration scripts
│   ├── platforms/      # Adapter registry and platform-owned permission definitions
│   │   └── qq/permissions.py # QQ default identity groups and runtime identity resolution
│   ├── permissions/    # UID identity, platform account, command grant & SUPERUSERS APIs
│   ├── repositories/   # Data access layer
│   │   ├── blocklist.py     # Blocklist repository
│   │   ├── message_store.py # Message store repository
│   │   ├── permissions.py   # Permission-system ORM repository
│   │   ├── registry.py      # Platform/adapter/protocol registry seeding
│   │   └── user_mapping.py  # UID/platform account binding compatibility entrypoint
│   ├── services/       # Business logic services
│   └── start/          # Startup & initialization
├── apps/docs/          # Fumadocs documentation site
│   ├── content/docs/   # MDX content (en + zh)
│   ├── src/
│   │   ├── app/        # Next.js App Router pages & routes
│   │   ├── components/ # React components (graph-view, mdx, mermaid)
│   │   ├── lib/        # Shared logic (source, rss, build-graph, layout)
│   │   └── __tests__/  # Vitest unit tests
│   └── source.config.ts # Fumadocs MDX config
├── packages/           # Shared frontend packages
├── tools/                           # Standalone utility tools
│   ├── __init__.py
│   └── adapter_loader.py           # Deprecated adapter on-demand loader (Milky, QQ, OneBot V12)
├── Dockerfile          # Container runner generation via nb-cli
├── pyproject.toml      # Python project config
├── package.json        # Monorepo root (pnpm + Turborepo)
└── Taskfile.yml        # Task runner for CI/local commands
```

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

- **pre-commit**: Conditional checks — Prek auto-fix (always) → Ruff lint/format (on Python changes) → Pyright/ty (on Python changes) → pytest (on Python changes) → Docs ESLint/type-check/Vitest (on docs changes) → React Doctor (on docs changes, prefers global/local install, falls back to `pnpm dlx` cache, last resort `npx -y`) → Gitnexus analyze (always, non-blocking, prefers `node_modules/.bin/gitnexus` for zero download)
- **commit-msg**: gitmoji + Conventional Commits format validation + auto-append Signed-off-by (with trailer block detection)
- **prepare-commit-msg**: Interactive gitmoji commit message via direct `node_modules/.bin/gitmoji --hook` (zero pnpm/npx overhead; falls back to npx / global gitmoji if local missing)
- **CLI resolution order** (all hooks): local `node_modules/.bin/<bin>` → global PATH → global `.cmd` shim → `pnpm dlx` cache (last resort: `npx -y` for non-devDeps)
- Set `$env:HUSKY='0'` to skip hooks when needed (e.g., automated commits)

## Agent Preferences

These rules are injected as context for every conversation. Treat them as hard constraints.

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
| `context7-mcp/` | Looking up library/framework docs, API references, code examples | Context7 MCP integration for up-to-date documentation retrieval. |
| `delivery-loop/` | Debugging, TDD, code review, implementation verification | Disciplined feedback loops: debug-investigation, TDD, change-review. |
| `frontend-quality/` | React diagnostics, visual polish, accessibility, health checks | React Doctor integration and frontend polish checklist for the docs site. |
| `issue-planning/` | PRDs, issue breakdown, triage, refactor plans | Turn conversation into trackable work via GitHub Issues. |
| `design-prototyping/` | Interface design, design grilling, throwaway prototypes | Explore and harden designs before committing to implementation. |
| `gitnexus/gitnexus-cli/` | Running GitNexus CLI commands (analyze, status, clean, wiki) | CLI task reference for GitNexus operations. |
| `gitnexus/gitnexus-debugging/` | Debugging bugs, tracing errors, "why does X fail?" | Scientific debugging workflow: hypothesis → instrument → reproduce → analyze → fix → verify. |
| `gitnexus/gitnexus-exploring/` | Understanding architecture, "how does X work?" | Code exploration via knowledge graph: execution flows, symbol relationships. |
| `gitnexus/gitnexus-guide/` | Questions about GitNexus tools/schema/workflow | Quick reference for all GitNexus MCP tools, resources, and graph schema. |
| `gitnexus/gitnexus-impact-analysis/` | "What breaks if I change X?", pre-edit safety check | Blast radius analysis: upstream/downstream impact at depth 1/2/3. |
| `gitnexus/gitnexus-refactoring/` | Renaming, extracting, splitting, moving code | Multi-file coordinated rename using knowledge graph + text search. |
| `gitnexus/gitnexus-pr-review/` | Reviewing pull requests, assessing merge risk | PR review with knowledge-graph-aware change analysis. |
| `prek/` | Setting up or running Git hooks with `prek` | `prek` (Rust `pre-commit` alternative) configuration, installation, and workflow guide. |

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

- **🧪 CI**: Static analysis (Ruff + Markdown + Turborepo lint), tests & type check (Pyright + ty + pytest + docs test), auto-format on push to main/dev. Test jobs install `--extra deprecated-adapters` so test files importing optional dependencies (Milky adapter) can resolve.
- **👷 CI-builds**: Build verification on Python/package changes
- **📚 Docs Deploy**: Build and deploy to GitHub Pages on push to main/dev
- **🩺 React Doctor**: React codebase health check on PRs (uses CLI, not the action — see Lessons Learned)
- **🧹 Clear Workflow**: Stale workflow cleanup
- **🏷️ Issues Top**: Issue triage automation

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

The project uses `platforms/registry.py` to unify adapters under a single "QQ" platform profile. Only OneBot V11 is now active; Milky, QQ, and OneBot V12 are deprecated and removed from the startup flow, but their source files are preserved with `DEPRECATED = True` markers and can be loaded on demand via `tools/adapter_loader.py`. QQ group command code lives under `handle/qq/`: shared command definitions in `handle/qq/commands/`, OneBot V11 handlers in `handle/qq/adapters/onebot11/{default,llonebot,napcat}/`, and (deprecated) Milky handlers in `handle/qq/adapters/milky/{default,llbot}/`. Always verify the return type by inspecting the adapter source in `.venv/Lib/site-packages/nonebot/adapters/` before writing access patterns.

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

### Git Hooks Optimization

- Pre-commit hooks run conditionally based on changed file types — Python changes trigger Ruff + Pyright/ty + pytest; docs changes trigger ESLint + tsc + Vitest
- GitNexus analyze runs on every pre-commit but is non-blocking — stale index warnings should prompt a manual `npx gitnexus analyze`

### Windows Commands in Bash Hooks

- Husky hooks may run under a Bash environment that sees Windows commands differently from PowerShell. Check that a command can actually start, not only that `command -v` finds it.
- Prefer resolving tool commands once near the top of the hook. For Windows `.cmd` Node shims such as `pnpm.cmd` and `npx.cmd`, invoke them through `cmd.exe /c`; executing the `.cmd` file directly from Bash can silently skip checks or emit misleading `node` errors.
- Do not suppress `git diff --cached` failures when deciding which checks to run. If `git` is unavailable in the hook shell, fail clearly instead of treating the staged file list as empty.

### PowerShell Markdownlint Globs

- When running `markdownlint-cli2` through `pwsh.exe -NoProfile -Command`, pass glob arguments exactly as the shell should see them; incorrectly nested or escaped quotes can turn globs into malformed paths and make Node scan far more than intended. Prefer the Taskfile command or a known-good direct command form before treating a markdownlint timeout as a lint failure.

### Husky Hook CLI Resolution

- `npx <bin>` and `pnpm exec <bin>` always re-resolve a package, even when `node_modules/.bin/<bin>` is already present. On a warm cache this still costs a sub-process spawn, an npm registry HEAD, and a lockfile check; on a cold cache it downloads a full tarball. Either cost dominates the per-hook budget for trivial checks like `gitnexus analyze` or `gitmoji --hook`.
- **Resolution order for JS CLIs in Husky hooks**: `node_modules/.bin/<bin>` (devDep shim, zero download) → global `PATH` (`command -v <bin>` and runnable check) → global `.cmd` shim (only if no native found, invoke via `cmd.exe /c`) → `pnpm dlx <bin>` cache → `npx -y <bin>` (last resort, for non-devDeps that must be fetched on demand).
- For devDependencies that are guaranteed by `package.json` (e.g., `gitmoji-cli`, `gitnexus`), the local `node_modules/.bin/<bin>` branch should always succeed once `pnpm install` has run, so the hook never needs to fall back to `npx` in the common path.
- Cache the resolved tool reference in a variable at the top of the hook and reuse it across phases; avoid re-running `command -v` inside loops or per-file logic.
- When using `.cmd` shims (Windows Node shims like `pnpm.cmd`, `npx.cmd`), execute them via `cmd.exe /c <shim> ...` — running the `.cmd` directly from Git Bash can silently exit with misleading "node not found" errors.

### Type Narrowing in Tests

- `isinstance(event, GroupMessageEvent)` is the correct way to narrow event types in NoneBot2
- Don't use `type(event) is GroupMessageEvent` — it breaks with proxy/wrapper objects

### i18n Locale Consistency

- When changing i18n settings in tests, override locale in `conftest.py` instead of modifying individual test assertions
- This maintains test environment consistency and avoids cascading assertion changes

### Fumadocs i18n File Naming

- Default language files have no suffix (e.g., `gitnexus.mdx`)
- Non-default language files use `.{locale}.mdx` suffix (e.g., `gitnexus.zh.mdx`)
- `@fumadocs/language` exports supported language packages; English is built-in default (no need to import separately)

### Bypassing lru_cache for Multi-Locale Tests

- **Problem**: The i18n module's `_read_configured_locale()` is decorated with `@lru_cache(maxsize=1)`. Once it reads the locale from NoneBot config on first call, the result is cached for the whole session. This prevents running the same test against both `zh_CN` and `en_US` in one pytest session — the second locale never takes effect because the cached value is returned.
- **Solution**: The `configured_locale` fixture in `tests/conftest.py` calls `_read_configured_locale.cache_clear()` to drop the cached value, then `monkeypatch.setattr(...)` replaces the function so it returns the parametrized locale. This lets parametrized tests switch locale per parameter without session-wide caching interference.
- **When to use which fixture**: Use `locale` (no global mutation) for tests that pass `locale=` explicitly to `gettext()`/`ngettext()`. Use `configured_locale` only for tests that depend on `get_configured_locale()` or `_()`, where the cached function would otherwise return the wrong locale.

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

### Pending Rollbacks

| Suppressed Rule | Location | Reason | Remove When |
|----------------|----------|--------|-------------|
| Pyright/ty exclude of `src/.../adapters/milky` | `pyproject.toml` `[tool.pyright]` and `[tool.ty.src]` | Milky adapter moved to optional deps; not installed in static-analysis env, causing `reportMissingImports` | Remove exclude when Milky adapter is fully deleted or when static-analysis env installs `--extra deprecated-adapters` |
| `deslop/unused-export` | `apps/docs/doctor.config.ts` | `useMDXComponents` export is required by fumadocs MDX provider for future component customization, but currently unused | `useMDXComponents` is actually utilized in MDX rendering (e.g., custom code blocks, callouts, or admonitions) |

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
    ├── onebot-v11/        # OneBot V11 protocol
    │   ├── overview.mdx   # Protocol overview, runtime detection
    │   ├── default.mdx    # Default implementation (core commands + remote management)
    │   ├── napcat.mdx     # NapCat extensions (announcement + avatar)
    │   └── llonebot.mdx   # LLOneBot extensions (announcement)
    └── milky/             # Milky protocol
        ├── overview.mdx   # Protocol overview, API differences from OneBot V11
        ├── default.mdx    # Default implementation
        └── llbot.mdx      # LLBot extensions (text-only announcement)
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

### Database Storage Reorganization

- **Unified ORM consolidation**: When migrating from custom SQLAlchemy engines to `nonebot_plugin_orm`, remove ALL custom engine management code (`Base`, `_ENGINES`, `session_for()`, `storage_target()`, `close_engines()`) — do not leave remnants. All data access must go through `orm_crud.py` + `get_session()`.
- **Test rewrite pattern**: Tests that directly manipulated database files (e.g., checking `.db` file existence, using `session_for()` to modify records) MUST be rewritten to mock `orm_crud` functions at the repository module level using `patch.object(repository, "create"/"upsert"/"get_one"/"update"/"list_items"/"delete", ...)`. Follow the pattern in `tests/database/test_blocklist.py`.
- **Alembic migration generation**: `nb orm revision` may generate an empty migration (`pass` in both `upgrade()` and `downgrade()`) if the database file already contains tables from previous `create_all` calls. In this case, manually write the migration script with `op.create_table()` / `op.create_index()` operations based on the model definitions, or delete the existing database file first (if not locked by another process).
- **File-to-package conversion**: When converting a single `.py` file (e.g., `json5_store.py`) to a package (`json5_store/`), the `__init__.py` MUST explicitly re-export all public API symbols via `from .submodule import Symbol` and list them in `__all__`. Merely importing the submodule is insufficient — test imports like `from ..database.json5_store import RobustAsyncJSON5DB` will fail without explicit re-exports.
- **Migration script lint**: Alembic-generated migration scripts use `collections.abc.Sequence` only for type annotations. With `from __future__ import annotations` in place, move the `Sequence` import into a `TYPE_CHECKING` block to satisfy ruff's `TC003` rule.
- **Documentation sync**: When deleting or renaming source files, update ALL documentation references (AGENTS.md file tree, architecture diagrams, `apps/docs/` MDX files) — not just code. Use `Grep` to find stale references after structural changes.

### Platform/Adapter/Protocol Table Reorganization

- **Registry table seeding**: When adding database registry tables that mirror Python data structures (like `registry.py`), implement a `seed_registry_tables()` function that upserts metadata on startup. Use `conflict_fields` for idempotent upserts so re-running doesn't create duplicates.
- **Protocol dimension tracking**: When adding a `protocol_id` column to existing tables, make it nullable (`Mapped[str | None]`) since the protocol implementation may not always be determinable at the point of recording (e.g., at event_preprocessor time, the handler hasn't run yet).
- **Unique constraint with nullable columns**: SQLite treats NULL values as distinct in unique constraints, so `(platform_id, adapter_id, protocol_id, ...)` allows multiple records with `protocol_id=NULL` for the same message identity. This is acceptable for message records but should be documented.
- **Migration script rewrite for new deployments**: When the user accepts "new deployment only" strategy, rewrite the initial migration script directly rather than creating a new migration that alters the schema. This keeps the migration history clean for fresh deployments.

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

# Claude Code Behavioral Guidelines

These guidelines are specific to Claude Code. They bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
