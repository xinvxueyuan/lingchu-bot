<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **lingchu-bot** (3695 symbols, 6462 relationships, 286 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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

- **GitNexus skills**: Use `.claude/skills/gitnexus/*` or `.agents/skills/gitnexus/*` for architecture exploration, debugging, impact analysis, refactoring, PR review, and CLI operations. Follow the GitNexus requirements above before editing symbols or committing.
- **prek**: Use `.claude/skills/prek/SKILL.md` or `.agents/skills/prek/SKILL.md` when setting up or running hook checks with `prek`.
- **GitHub skills**: Use for GitHub repository, issue, pull request, review-comment, CI, and publish/PR workflows.

### Frontend, Browser, And Deployment

- **Browser / Playwright / Chrome**: Use Browser for local in-app browser checks, Playwright for terminal-driven browser automation, and Chrome only when existing user Chrome state is required. (Routing-only — no local SKILL.md; loaded from Codex platform skills at runtime.)
- **Vercel skills**: Use for Next.js, React best practices, shadcn/ui, AI SDK, deployments, Vercel CLI/API, storage, auth, payments, cron, routing middleware, functions, workflow, and verification tasks. (Routing-only — no local SKILL.md; loaded from Codex platform skills at runtime.)
- **Cloudflare skills**: Use for Workers, Wrangler, Durable Objects, Agents SDK, MCP servers, sandbox SDK, and Cloudflare platform work. (Routing-only — no local SKILL.md; loaded from Codex platform skills at runtime.)

### Artifacts And Media

- **Documents / Presentations / Spreadsheets / PDF**: Use for `.docx`, slide decks, spreadsheet files, and PDF tasks where rendering or file-format behavior matters. (Routing-only — no local SKILL.md; loaded from Codex platform skills at runtime.)
- **imagegen**: Use for raster image generation or edits when visuals are requested. (Routing-only — no local SKILL.md; loaded from Codex platform skills at runtime.)

### Skill Authoring

- **skill-creator**: Use when creating or updating Codex skills. Required skill folders contain `SKILL.md`; optional resources include `scripts/`, `references/`, `assets/`, and `agents/openai.yaml`.
- **skill-installer / plugin-creator**: Use when installing skills or scaffolding Codex plugins. (Routing-only — no local SKILL.md; loaded from Codex platform skills at runtime.)

Project-local skill indexes are available at `.agents/skills/available-skills/SKILL.md` and `.claude/skills/available-skills/SKILL.md`.

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

> See the [Project Directory Tree](#project-directory-tree) section below for the complete annotated tree with file-level descriptions.

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

- **Always check git workspace status before committing** — before any commit, run `git status` and `git diff` to verify all necessary changes are tracked, no unintended files are staged, and the working tree is clean. Never commit blindly.
- **No commits or pushes without explicit user instruction** — never auto-commit, auto-push, or assume the user wants a commit after finishing a task. Wait for the user to say so.
- **Write persistent preferences into AGENTS.md** — memory files and session context are ephemeral; AGENTS.md is the single source of truth for project-level rules and user preferences. When the user says "remember this" or expresses a preference, add it here.
- **Prefer granular checks over full `task check`** — use the Quick Reference table above to run only the checks relevant to what changed. Full `task check && task test` is for pre-commit verification, not for every intermediate step.
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
| `gitnexus/gitnexus-cli/` | Running GitNexus CLI commands (analyze, status, clean, wiki) | CLI task reference for GitNexus operations. |
| `gitnexus/gitnexus-debugging/` | Debugging bugs, tracing errors, "why does X fail?" | Scientific debugging workflow: hypothesis → instrument → reproduce → analyze → fix → verify. |
| `gitnexus/gitnexus-exploring/` | Understanding architecture, "how does X work?" | Code exploration via knowledge graph: execution flows, symbol relationships. |
| `gitnexus/gitnexus-guide/` | Questions about GitNexus tools/schema/workflow | Quick reference for all GitNexus MCP tools, resources, and graph schema. |
| `gitnexus/gitnexus-impact-analysis/` | "What breaks if I change X?", pre-edit safety check | Blast radius analysis: upstream/downstream impact at depth 1/2/3. |
| `gitnexus/gitnexus-refactoring/` | Renaming, extracting, splitting, moving code | Multi-file coordinated rename using knowledge graph + text search. |
| `gitnexus/gitnexus-pr-review/` | Reviewing pull requests, assessing merge risk | PR review with knowledge-graph-aware change analysis. |
| `hf-cli/` | Hugging Face Hub operations (models, datasets, spaces, buckets, endpoints, jobs) | Full CLI reference for `hf` command — auth, upload/download, cache, repos, papers, collections, endpoints, jobs. |
| `prek/` | Setting up or running Git hooks with `prek` | `prek` (Rust `pre-commit` alternative) configuration, installation, and workflow guide. |
| `react-doctor/` | Finishing React features, fixing bugs, `/doctor`, scanning/triaging React code | React codebase health scanner (security, performance, correctness, architecture). Outputs 0–100 score. Includes rule explanation and configuration reference. |

#### `.claude/skills/` (Claude Code)

Subset of `.agents/skills/` — contains `available-skills/`, all `gitnexus/*` skills (including `gitnexus-pr-review`), `prek/`, `hf-cli/`, and `react-doctor/`.

#### `.trae/skills/` (Trae IDE)

Mirror of `.agents/skills/` — contains the same full set of skills. Used by Trae IDE's skill loading mechanism.

#### `skills/` (Shared)

Mirror of `.agents/skills/` — contains the same full set of skills. Shared across all agent platforms.

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
- **� React Doctor**: React codebase health check on PRs (uses CLI, not the action — see Lessons Learned)
- **� Clear Workflow**: Stale workflow cleanup
- **🏷️ Issues Top**: Issue triage automation

## Lessons Learned

> **Timeliness warning**: Lessons below reflect the state of the codebase and dependencies at the time they were written. Before relying on any lesson, verify it still holds — APIs change, packages add exports, and CI configs evolve. When a lesson becomes outdated, update or remove it rather than propagating stale assumptions.

### Cross-Cutting Change Checklist

When modifying business logic (especially adapter-layer code), changes MUST propagate to all affected areas **before considering the task done**:

1. **Source code** — `src/plugins/nonebot_plugin_lingchu_bot/`
2. **Tests** — `tests/` (add/update tests for new behavior, remove tests for deleted behavior)
3. **i18n** — `src/plugins/nonebot_plugin_lingchu_bot/i18n/` (run `task i18n` if user-facing strings change)
4. **Docs** — `apps/docs/content/docs/` (update command docs if behavior changes)
5. **Menu** — `src/plugins/nonebot_plugin_lingchu_bot/handle/menu.py` (update `MENU_FEATURES` when adding/removing/modifying command handlers: command key, usage text, summary, availability)

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

The project uses `platforms/registry.py` to unify all adapters (OneBot V11, Milky, QQ, OneBot V12) under a single "QQ" platform profile. QQ group command code lives under `handle/qq/`: shared command definitions in `handle/qq/group/`, OneBot V11 handlers in `handle/qq/onebot/v11/{default,llonebot,napcat}/group/`, and Milky 1.2 handlers in `handle/qq/milky/v1_2/{default,llbot}/group/`. Always verify the return type by inspecting the adapter source in `.venv/Lib/site-packages/nonebot/adapters/` before writing access patterns.

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

### Husky Hook CLI Resolution

- `npx <bin>` and `pnpm exec <bin>` always re-resolve a package, even when `node_modules/.bin/<bin>` is already present. On a warm cache this still costs a sub-process spawn, an npm registry HEAD, and a lockfile check; on a cold cache it downloads a full tarball. Either cost dominates the per-hook budget for trivial checks like `gitnexus analyze` or `gitmoji --hook`.
- **Resolution order for JS CLIs in Husky hooks**: `node_modules/.bin/<bin>` (devDep shim, zero download) → global `PATH` (`command -v <bin>` and runnable check) → global `.cmd` shim (only if no native found, invoke via `cmd.exe /c`) → `pnpm dlx <bin>` cache → `npx -y <bin>` (last resort, for non-devDeps that must be fetched on demand).
- For devDependencies that are guaranteed by `package.json` (e.g., `gitmoji-cli`, `gitnexus`), the local `node_modules/.bin/<bin>` branch should always succeed once `pnpm install` has run, so the hook never needs to fall back to `npx` in the common path.
- Cache the resolved tool reference in a variable at the top of the hook and reuse it across phases; avoid re-running `command -v` inside loops or per-file logic.
- When using `.cmd` shims (Windows Node shims like `pnpm.cmd`, `npx.cmd`), execute them via `cmd.exe /c <shim> ...` — running the `.cmd` directly from Git Bash can silently exit with misleading "node not found" errors.

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
| `vitest.config.ts` | Vitest config: jsdom environment, CSS ignore, path aliases |
| `eslint.config.mjs` | ESLint flat config with Next.js rules |
| `postcss.config.mjs` | PostCSS with `@tailwindcss/postcss` |

## Project Directory Tree

```
lingchu-bot/
├── .agents/                          # Trae/Codex skill definitions
│   └── skills/
│       ├── available-skills/         # Skill routing index
│       ├── gitnexus/                 # GitNexus skills (exploring, debugging, impact, refactoring, CLI, guide, pr-review)
│       ├── hf-cli/                   # Hugging Face Hub CLI skill
│       ├── prek/                     # Prek (Rust pre-commit alternative) skill
│       └── react-doctor/             # React codebase health scanner
├── .claude/                          # Claude Code skill definitions (subset of .agents/)
│   └── skills/
├── .trae/                            # Trae IDE configuration
│   ├── rules/                        # Always-applied rules
│   │   └── git-commit-message.md     # Gitmoji + Conventional Commits spec
│   └── skills/                       # Trae skill definitions (mirror of .agents/)
├── .github/
│   └── note/AGENTS-zh.md            # Chinese translation of AGENTS.md
├── .husky/                           # Git hooks (pre-commit, commit-msg, prepare-commit-msg)
├── src/
│   └── plugins/nonebot_plugin_lingchu_bot/   # Core Python plugin
│       ├── __init__.py               # Plugin entry point, matcher registration
│       ├── core/
│       │   ├── config.py             # Plugin config model (Pydantic)
│       │   ├── runtime_config.py     # Runtime configuration helpers
│       │   └── sub_plugins.py        # Sub-plugin loader
│       ├── database/
│       │   ├── json5_store.py        # JSON5-based key-value store
│       │   ├── message_storage.py    # Message persistence service
│       │   ├── models.py             # ORM models (aiosqlite)
│       │   └── orm_crud.py           # Async CRUD helpers
│       ├── handle/
│       │   └── qq/                   # QQ platform handlers
│       │       ├── group/            # Shared group command definitions
│       │       ├── onebot/v11/
│       │       │   ├── default/group/   # OneBot V11 shared handlers
│       │       │   ├── llonebot/group/  # LLOneBot extensions
│       │       │   └── napcat/group/    # NapCat extensions
│       │       └── milky/v1_2/
│       │           ├── default/group/   # Milky 1.2 shared handlers
│       │           └── llbot/group/     # LLBot extensions
│       ├── i18n/                     # Babel/gettext translations (en, zh)
│       ├── platforms/                # Adapter-to-platform registry & resolution
│       │   └── registry.py          # Cross-platform capability & adapter selection
│       ├── repositories/             # Data access layer
│       │   └── message_store.py     # Message store repository
│       ├── services/                 # Business logic services
│       │   └── messagestore.py      # Message storage service
│       └── start/                    # Startup & initialization
│           ├── bootstrap.py         # Bootstrap sequence
│           ├── initialize.py        # Plugin initialization
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
│       │   │   ├── commands.mdx      # Command reference
│       │   │   ├── configuration.mdx # Configuration options
│       │   │   └── troubleshooting.mdx # Common issues & solutions
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
├── tests/                            # Python test suite
├── skills/                           # Shared skill definitions (mirror of .agents/)
├── Dockerfile                        # Container runner (nb-cli generated)
├── pyproject.toml                    # Python project config (uv, ruff, pyright, pytest)
├── package.json                      # Monorepo root (pnpm + Turborepo)
├── Taskfile.yml                      # Task runner for CI/local commands
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
│              ──► core/sub_plugins.py ──► platform handlers       │
│              ──► platforms/registry.py ──► adapter resolution     │
│              ──► database/orm_crud.py ──► models.py (aiosqlite)  │
│              ──► database/json5_store.py ──► JSON5 KV store      │
│              ──► database/message_storage.py ──► message hooks   │
│              ──► repositories/message_store.py ──► data access   │
│              ──► services/messagestore.py ──► business logic     │
│              ──► start/ ──► bootstrap, initialize, startup       │
│              ──► i18n/ ──► Babel gettext catalogs                │
│                                                                   │
│  handle/qq/                                                       │
│    ├── group/ ──► shared QQ group command definitions             │
│    ├── onebot/v11/default/group/ ──► OneBot V11 handlers         │
│    ├── onebot/v11/{llonebot,napcat}/group/ ──► OneBot extensions │
│    ├── milky/v1_2/default/group/ ──► Milky 1.2 handlers           │
│    └── milky/v1_2/llbot/group/ ──► LLBot extensions               │
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

- **Pre-commit should conditionally trigger checks by file type**: Use `git diff --cached --name-only --diff-filter=ACMR` to collect staged files, detect file extensions/paths via `has_pattern()`, skip Ruff/Pyright/ty/pytest when no Python changes, skip ESLint/type-check/Vitest when no docs changes — saves 30-60 seconds
- **Signed-off-by appending needs trailer block detection**: When existing trailers (e.g., `Closes #`, `BREAKING CHANGE:`, `Reviewed-by:`) are present, append to the same block (no blank line separation); only use blank line separation when no trailers exist
- **Blank line cleanup must not break message structure**: `sed '/^$/N;/^\n$/d'` removes all consecutive blank lines, breaking subject-body-trailer structure; only compress ≥3 consecutive blank lines to 2
- **Duplicate signature detection must ignore trailing whitespace**: `grep -qF` may misjudge due to trailing whitespace differences; strip trailing whitespace with `sed 's/[[:space:]]*$//'` first, then use `grep -qxF` for exact full-line matching
- **Empty message body should not append Signed-off-by**: Empty commit messages are caught by format validation; appending a signature to an empty file is meaningless

### Switching i18n Default Locale

- **Fumadocs language packs**: `@fumadocs/language` exports locale packs for languages it supports (e.g., `zh-cn`, `zh-tw`); English (`en-us`) is built-in by default and does not need a separate import. When switching the default language to English, `layout.shared.tsx` only needs `preset('zh', zhCN())` for Chinese — no English pack import is required. Always check `@fumadocs/language` exports for the current list before assuming a locale is or isn't available.
- **Override locale in test environment rather than changing assertions**: After changing Python `DEFAULT_LOCALE` from `zh_CN` to `en_US`, all tests asserting Chinese translations will fail. The correct approach is to add `"lingchu_locale": "zh_CN"` in `tests/conftest.py`'s `nonebot.init()` to override back to Chinese, avoiding modifying hundreds of test assertions individually, while also validating the locale configuration override mechanism.
- **Fumadocs i18n file naming convention**: Default language MDX files have no suffix (`page.mdx`), non-default language files have a locale suffix (`page.zh.mdx`); same for `meta.json`. When switching the default language, content files must be renamed in bulk.

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

- **pre-commit.ci failures** → use the **prek** skill (`.agents/skills/prek/SKILL.md`) to reproduce and fix pre-commit hook failures locally, instead of manually running each hook
- **Code intelligence** → use **GitNexus** skills instead of manual grep/find
- **Library docs** → use **Context7 / find-docs** instead of web search
- **GitHub workflows** → use **GitHub** skills for PR/issue/CI operations

Rule of thumb: **when a CI check fails or you need to do something repetitive, first check `.agents/skills/` and `.claude/skills/` for an existing skill that automates it.**

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

### Pending Rollbacks

Rule suppressions and temporary workarounds that should be reverted once the triggering condition changes. Review this section periodically (e.g., when updating dependencies or refactoring).

| What | Where | Why suppressed | Rollback condition |
|------|-------|---------------|-------------------|
| `deslop/unused-export: "off"` | `doctor.config.ts` | `useMDXComponents` in `mdx.tsx` is a framework-required re-export but currently unused (no `providerImportSource` in `source.config.ts`) | Remove this suppression once `useMDXComponents` is actually consumed (e.g., after adding `providerImportSource` to `source.config.ts` or importing it elsewhere) |
| CLI instead of `millionco/react-doctor@v2` action | `.github/workflows/react-doctor.yml` | Upstream action has bugs: detached HEAD, ANSI leak in PR comments (PR #80 pending) | Switch back to the action once upstream releases a fix (monitor PR #80) |

- **Non-component exports break Fast Refresh**: Utility functions (`getMermaidConfig`, `sanitizeMermaidSvg`, `renderMermaidSvg`) exported from a component file (`mermaid.tsx`) trigger `react-doctor/only-export-components`. Extract them to a separate non-component module (e.g., `mermaid-utils.ts`) and import from there. Update test imports accordingly.
- **`/llms.txt` is a route handler, not a static file**: When linking to Next.js route handlers from components, use `<Link>` (not plain `<a>`) — they're internal routes that benefit from client-side navigation.
