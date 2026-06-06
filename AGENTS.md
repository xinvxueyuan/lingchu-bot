<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **lingchu-bot** (1982 symbols, 4076 relationships, 166 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
- Features: i18n (zh/en), RSS, Mermaid, Twoslash, EPUB export, LLM-friendly text (`/llms.txt`, `/llms-full.txt`), document relationship graph
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
│   ├── content/docs/   # MDX content (zh + en)
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
pnpm exec markdownlint-cli2 "apps/**/*.md" "packages/**/*.md" "!**/node_modules/**" "!**/out/**" "README.md" "CONTRIBUTING.md" "CODE_OF_CONDUCT.md" ".github/**/*.md"
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

- **pre-commit**: Runs `prek` (lint/format checks) + `gitnexus analyze` (auto-refresh code index)
- **prepare-commit-msg**: Interactive gitmoji commit message via `pnpm exec gitmoji --hook`
- Set `$env:HUSKY='0'` to skip hooks when needed (e.g., automated commits)

## Architecture Decisions

- All server components and route handlers in `apps/docs` are async functions
- `baseOptions()`, `buildGraph()`, `getRSS()` return Promises
- i18n uses `hideLocale: 'default-locale'` — default locale (zh) omits prefix in URLs
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
