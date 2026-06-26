<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **lingchu-bot** (3697 symbols, 7169 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
- Project-local skills: `.agents/skills/`
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
- **Prek is hook source of truth**: `prek.toml` is the only pre-commit hook configuration. Do not reintroduce `.pre-commit-config.yaml`.
- **Version sync**: Use `Taskfile.yml` task `ci:version:write-config` to write both `src/plugins/nonebot_plugin_lingchu_bot/core/config.py` and root `package.json`.
- **Skills exclusion sync**: When changing skills exclusion patterns in `pyproject.toml`, sync the corresponding `prek.toml` comments/patterns.

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
| Runtime config | `config.json5`, `bot_state.json5`, `menu.json5`, schema text in `core/schemas.py` |
| Triggers | `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/commands/triggers.py` |
| Agent context | `AGENTS.md`, `CLAUDE.md`, `.github/note/AGENTS-zh.md` |

For handle, QQ command, adapter handler, matcher, `command_key`, menu, trigger, permission, or config-coupled work, use `.agents/skills/engineering-workflow/references/delivery-loop/references/handle-feature-workflow.md`.

### Command And Menu Rules

- Group command trigger words are locale-exclusive. Do not register Chinese and English triggers at the same time for the same matcher. Use `get_configured_locale()` and keep inactive language aliases out.
- Menus fail closed. Hide commands the current identity or implementation cannot execute.
- `MENU_FEATURES.command_key` is the shared command identifier for permission checks, menu filtering, and handler decorators.
- When adding commands, update triggers, `MENU_FEATURES`, tests, and QQ command-reference docs together.
- The remote management commands are OneBot V11 only and implemented under `handle/qq/adapters/onebot11/default/remote.py`.

### State And Config Rules

- `core/bot_state.py` persists `bot_state.json5` through localstore.
- `is_handle_active(platform_id)` resolves global AND platform state.
- `is_silent_mode(platform_id)` resolves global OR platform state.
- `selected_adapter_handle()` supports `bypass_gate` and `bypass_silent`.
- "闭嘴"/"说话" bypass silent mode but not shutdown gate.
- "开机"/"关机" bypass both gate and silent mode.
- `install_schemas()` must run before runtime JSON5 files reference schema basenames. Its failure is logged and non-fatal.

### Repository API Style

- Use frozen dataclass request objects for write/audit APIs with coupled fields.
- Use `CommandAudit` for command audit payloads, then call `record_audit_fire_and_forget()` or `record_command_audit()`.
- Do not add long parameter lists for platform, adapter, bot, group, target, reason, and duration; create a request object.
- Use `fire_and_forget(coro, *, name="...")` only for discardable background work whose result is not needed by the caller.

## T — Tools

### Skills And MCPs

| Need | Route |
| --- | --- |
| Current library, framework, SDK, API, CLI, or cloud docs | Context7 via `tool-workflows`: resolve library ID, then query docs with the full user question |
| OpenAI product/API docs | `openai-docs`, official docs only |
| Architecture, impact, refactor, review, frontend quality, issue planning | `.agents/skills/engineering-workflow/SKILL.md` |
| Live Lingchu / NapCat / QQ runtime failures | `.agents/skills/interactive-runtime-debugging/SKILL.md` |
| Hooks, Prek, Husky, skill management | `.agents/skills/tool-workflows/SKILL.md` |
| OneBot V11 / NapCat API signatures | NapCat API MCP before writing adapter calls |
| GitHub PRs, issues, CI, publishing | GitHub skills |

### Development Commands

Python:

```bash
uv run -m ruff check . --output-format=github
uv run -m ruff check --fix .
uv run -m ruff format --check .
uv run -m ruff format .
uv run -m pyright .
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
| Python source only | Ruff check + Ruff format check + Pyright + ty + relevant pytest |
| Docs site only | `pnpm --filter docs lint` + docs tests + Playwright hook smoke + docs type check + link lint when content changes |
| Markdown only | `pnpm exec markdownlint-cli2` |
| i18n strings | `task i18n` + relevant pytest |
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
- Structural alignment excludes the GitNexus marker block, which is generated by `gitnexus analyze`. Preserve marker comments and other angle-bracket locator tags exactly so CLIs can find their managed ranges.
- Do not embed large generated inventories in agent context. Link to canonical docs or inspect live files.
- After structural source changes, update developer docs and search for stale references.

#### Adapter And API Boundaries

- Same-named adapter APIs can return different shapes. OneBot V11 APIs often return `dict`; inspect installed adapter source before writing access patterns.
- Deprecated Milky, QQ, and OneBot V12 source has been fully removed from the project, including any on-demand loading utility.
- OneBot V11 group `event.get_session_id()` can include both group and user IDs. Group-scoped history must use `group_id` as `conversation_id`.
- For OneBot V11 image APIs, verify file field format against current adapter and NapCat docs before changing calls.

#### Testing And Typing

- When changing function signatures, grep all callers, update fixtures, and run Ruff, Pyright, ty, and pytest.
- Do not shadow gettext helper `_` with throwaway locals in gettext-heavy handlers.
- In tests, side-effect exceptions must match the production `except` clause.
- Use `isinstance(event, GroupMessageEvent)` for NoneBot event narrowing.
- Mock adapter return shapes according to the real API shape.
- `assert_called_once_with()` is exact; for optional kwargs, assert presence through `mock.call_args.kwargs`.

#### Docs Site And Frontend

- `eslint-plugin-react@7.x` is incompatible with ESLint 10; pin ESLint 9 or migrate to `@eslint-react/eslint-plugin`.
- MDX table cells cannot contain raw `|` inside inline code like `<群号|群名称>`; use wording such as `<群号或群名称>`.
- Fumadocs link validation needs absolute URLs from root index pages.
- Mock `collections/server` in Vitest tests that import `src/lib/source.ts`.
- Extract shared functions from component files when tests need to import them.
- Utility exports from component files can break React Fast Refresh; move them to non-component modules.
- `/llms.txt` is a route handler; link internally with Next.js `Link`.
- Docker services must not bind Playwright webServer port `3100`; use ports outside the CI range such as `6100:3000`.
- `next typegen` may clear `apps/docs/.source/server.ts` (and `browser.ts`) to 0 bytes after the first `fumadocs-mdx` call. The `docs:check-types` script MUST run `fumadocs-mdx` a second time after `next typegen` to repopulate the collections exports, otherwise `tsc --noEmit` fails with `TS2305: Module '"collections/server"' has no exported member 'docs'`. Use `fumadocs-mdx && next typegen && fumadocs-mdx && tsc --noEmit`.

#### Database And Runtime Files

- All data access goes through `nonebot_plugin_orm` and `database/orm_crud/`; do not reintroduce custom engine management.
- Package conversions need explicit `__init__.py` re-exports.
- Alembic model packages must import all models so discovery works.
- Run migrations before non-SQLite tests.
- `ensure_json5_dict_file_async()` only creates missing files; use `write_json5_dict_file_async()` to overwrite.
- Runtime config defaults must be JSON-serializable; dump Pydantic defaults with `mode="json"` when needed.

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

#### Pending Rollbacks

| What | Where | Why | Rollback condition |
| --- | --- | --- | --- |
| `deslop/unused-export: "off"` | `doctor.config.ts` | `useMDXComponents` is a framework-required re-export but currently unused | Remove after `useMDXComponents` is consumed |
| React Doctor CLI instead of action | `.github/workflows/🩺-react-doctor.yml` | Upstream action bugs: detached HEAD and ANSI leak | Switch back after upstream releases a fix |
