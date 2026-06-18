<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **lingchu-bot** (2578 symbols, 5084 relationships, 216 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
- NoneBot2 with OneBot V11, Milky, and QQ adapters
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
│   ├── database/       # JSON5 store, ORM CRUD helpers
│   ├── handle/         # Platform/protocol/implementation command handlers
│   │   └── qq/{group,onebot/v11,milky/v1_2}/    # QQ group handlers
│   ├── i18n/           # Babel/gettext translations
│   ├── platforms/      # Adapter registry, permission presets & resolution
│   ├── repositories/   # Data access layer
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
| Docs site only | `pnpm --filter docs lint` + `pnpm --filter docs test` + `tsc --noEmit` |
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

- **🧪 CI**: Static analysis (Ruff + Markdown + Turborepo lint), tests & type check (Pyright + ty + pytest + docs test), auto-format on push to main/dev
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
4. **Docs** — `apps/docs/content/docs/` (update command docs if behavior changes)

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

### Adapter API Differences

Same-named APIs return different types across adapters:

| API | OneBot V11 | Milky |
|-----|-----------|-------|
| `get_group_member_info` | `dict` (use `.get("card")`) | `Member` model (use `.card`) |
| `set_group_ban` | `set_group_ban(group_id, user_id, duration)` | `set_group_member_mute(group_id, user_id, duration)` |

The project uses `platforms/registry.py` to unify all adapters (OneBot V11, Milky, QQ, OneBot V12) under a single "QQ" platform profile. QQ group command code lives under `handle/qq/`: shared command definitions in `handle/qq/commands/`, OneBot V11 handlers in `handle/qq/adapters/onebot11/{default,llonebot,napcat}/`, and Milky handlers in `handle/qq/adapters/milky/{default,llbot}/`. Always verify the return type by inspecting the adapter source in `.venv/Lib/site-packages/nonebot/adapters/` before writing access patterns.

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

### Verify Framework Syntax Against Official Docs

When writing MDX content for Fumadocs (or any framework), **never assume syntax** — always verify against official documentation and the project's actual setup. Examples:

- Fumadocs uses `<Callout>` JSX component for admonitions, **not** GitHub-style `>[!NOTE]` blockquotes. The `>[!NOTE]` syntax renders as a plain blockquote, not a styled callout.
- Before using any framework-specific component or syntax in MDX, check: (1) the framework's official docs via Context7 / find-docs, (2) existing usage in the project's content files, (3) the MDX component provider setup (e.g., `source.config.ts`, `mdx.tsx`).

Rule of thumb: **if you haven't seen the syntax used in the project's existing content files, verify it against official docs before writing it.**

### Pending Rollbacks

| Suppressed Rule | Location | Reason | Remove When |
|----------------|----------|--------|-------------|
| `deslop/unused-export` | `apps/docs/doctor.config.ts` | `useMDXComponents` export is required by fumadocs MDX provider for future component customization, but currently unused | `useMDXComponents` is actually utilized in MDX rendering (e.g., custom code blocks, callouts, or admonitions) |

- **`/llms.txt` is a route handler, not a static file**: When linking to Next.js route handlers from components, use `<Link>` (not plain `<a>`) — they're internal routes that benefit from client-side navigation.

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
