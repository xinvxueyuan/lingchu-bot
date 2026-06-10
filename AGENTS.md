<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **lingchu-bot** (2303 symbols, 4646 relationships, 193 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

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
- **openai-docs**: Use for OpenAI product/API questions; prefer official OpenAI docs.

### Code Intelligence And Git

- **GitNexus skills**: Use `.claude/skills/gitnexus/*` or `.agents/skills/gitnexus/*` for architecture exploration, debugging, impact analysis, refactoring, PR review, and CLI operations. Follow the GitNexus requirements above before editing symbols or committing.
- **prek**: Use `.claude/skills/prek/SKILL.md` or `.agents/skills/prek/SKILL.md` when setting up or running hook checks with `prek`.
- **GitHub skills**: Use for GitHub repository, issue, pull request, review-comment, CI, and publish/PR workflows.

### Frontend, Browser, And Deployment

- **Browser / Playwright / Chrome**: Use Browser for local in-app browser checks, Playwright for terminal-driven browser automation, and Chrome only when existing user Chrome state is required.
- **Vercel skills**: Use for Next.js, React best practices, shadcn/ui, AI SDK, deployments, Vercel CLI/API, storage, auth, payments, cron, routing middleware, functions, workflow, and verification tasks.
- **Cloudflare skills**: Use for Workers, Wrangler, Durable Objects, Agents SDK, MCP servers, sandbox SDK, and Cloudflare platform work.

### Artifacts And Media

- **Documents / Presentations / Spreadsheets / PDF**: Use for `.docx`, slide decks, spreadsheet files, and PDF tasks where rendering or file-format behavior matters.
- **imagegen**: Use for raster image generation or edits when visuals are requested.

### Skill Authoring

- **skill-creator**: Use when creating or updating Codex skills. Required skill folders contain `SKILL.md`; optional resources include `scripts/`, `references/`, `assets/`, and `agents/openai.yaml`.
- **skill-installer / plugin-creator**: Use when installing skills or scaffolding Codex plugins.

Project-local skill indexes are available at `.agents/skills/available-skills/SKILL.md` and `.claude/skills/available-skills/SKILL.md`.

# Project Context

> English | [中文](.github/note/AGENTS-zh.md)

## Overview

Lingchu Bot is a NoneBot2-based group management bot. The monorepo contains a Python backend plugin (`nonebot-plugin-lingchu-bot`) and a Next.js documentation site (`apps/docs`).

## Tech Stack

### Python Backend

- Python 3.13, managed by `uv`
- NoneBot2 with Milky adapter
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
│   ├── handle/         # Command handlers (mute, group settings/actions, etc.)
│   ├── i18n/           # Babel/gettext translations
│   └── utils/          # General command tools
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

### Python

```bash
uv sync --frozen                    # Install dependencies
# No committed root bot.py; load src/plugins from an existing NoneBot project
# or use Docker, whose build generates /tmp/bot.py via nb-cli.
docker compose up --build           # Run with the container runner
uv run -m ruff check . --output-format=github  # Lint
uv run -m ruff format --check .     # Format check
uv run -m pyright .                 # Type check (Pyright)
uv run -m ty check --output-format github  # Type check (ty)
uv run -m pytest                    # Run tests
```

### Documentation Site

```bash
pnpm --filter docs dev              # Dev server
pnpm --filter docs lint             # ESLint
pnpm --filter docs test             # Vitest
pnpm turbo run build --filter=docs  # Production build
```

### Markdown

```bash
pnpm exec markdownlint-cli2 "apps/**/*.md" "packages/**/*.md" "!**/node_modules/**" "!**/out/**" "README.md" "CHANGELOG.md" "CONTRIBUTING.md" "CODE_OF_CONDUCT.md" "Repository-Policy.md" ".github/**/*.md"
```

### Task Runner (Taskfile)

```bash
task install                        # Install all dependencies
task up                             # Update all dependencies
task check                          # All static checks (lint + format + markdown + type check)
task test                           # All tests (Python + Docs)
task format                         # Format all code
task fix                            # Auto-fix all linting and type issues
task build                          # Build all workspaces
task ci                             # Full local CI sequence
task i18n                           # Extract, update and compile i18n
```

## Git Hooks

- **pre-commit**: Conditional checks — Prek auto-fix (always) → Ruff lint/format (on Python changes) → Pyright/ty (on Python changes) → pytest (on Python changes) → Docs ESLint/type-check/Vitest (on docs changes) → Gitnexus analyze (always, non-blocking)
- **commit-msg**: gitmoji + Conventional Commits format validation + auto-append Signed-off-by (with trailer block detection)
- **prepare-commit-msg**: Interactive gitmoji commit message via `pnpm exec gitmoji --hook`
- Set `$env:HUSKY='0'` to skip hooks when needed (e.g., automated commits)

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

- **Static Analysis**: Ruff + Markdown + Turborepo lint
- **Tests & Type Check**: Pyright + ty + pytest + docs test
- **Auto Format**: On push to main/dev, auto-fix and commit
- **Docs Deploy**: Build and deploy to GitHub Pages

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

### Adapter API Differences

Same-named APIs return different types across adapters:

| API | OneBot V11 | Milky |
|-----|-----------|-------|
| `get_group_member_info` | `dict` (use `.get("card")`) | `Member` model (use `.card`) |
| `set_group_ban` | `set_group_ban(group_id, user_id, duration)` | `set_group_member_mute(group_id, user_id, duration)` |

Always verify the return type by inspecting the adapter source in `.venv/Lib/site-packages/nonebot/adapters/` before writing access patterns.

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

1. **pre-commit.ci** — runs `end-of-file-fixer`, `trailing-whitespace`, etc. If it reports "files were modified by this hook", those files lack trailing newlines or have trailing whitespace. Fix locally and push again. Common culprits: `.po`/`.pot` files (Babel output may omit trailing newline), `.turbo/preferences/` JSON files, generated files.
2. **CodeQL / GitHub Pages deploy** — `Requires authentication` errors are **repository permission issues**, not code issues. Check: Settings → Actions → General → Workflow permissions (must be "Read and write"), and ensure `id-token: write` is in the workflow's `permissions` block for OIDC-dependent jobs (Pages deploy, CodeQL).
3. **`.next` cache staleness** — after renaming/moving route directories (e.g., `en/` → `zh/`), the `.next/dev/types/validator.ts` cache may reference old paths and cause TypeScript errors. Delete `apps/docs/.next/` and re-run `task check` before committing.

Rule of thumb: **after every push, wait for all CI workflows to complete and investigate failures before moving on.**

### Use Existing Skills Before Manual Work

Before manually running checks or fixing issues, check if a skill already handles it:

- **pre-commit.ci failures** → use the **prek** skill (`.agents/skills/prek/SKILL.md`) to reproduce and fix pre-commit hook failures locally, instead of manually running each hook
- **Code intelligence** → use **GitNexus** skills instead of manual grep/find
- **Library docs** → use **Context7 / find-docs** instead of web search
- **GitHub workflows** → use **GitHub** skills for PR/issue/CI operations

Rule of thumb: **when a CI check fails or you need to do something repetitive, first check `.agents/skills/` and `.claude/skills/` for an existing skill that automates it.**
