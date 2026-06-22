<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **lingchu-bot** (3223 symbols, 6266 relationships, 269 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
| Understand architecture / "How does X work?" | `.agents/skills/engineering-workflow/references/gitnexus/gitnexus-exploring/guide.md` |
| Blast radius / "What breaks if I change X?" | `.agents/skills/engineering-workflow/references/gitnexus/gitnexus-impact-analysis/guide.md` |
| Trace bugs / "Why is X failing?" | `.agents/skills/engineering-workflow/references/gitnexus/gitnexus-debugging/guide.md` |
| Rename / extract / split / refactor | `.agents/skills/engineering-workflow/references/gitnexus/gitnexus-refactoring/guide.md` |
| Tools, resources, schema reference | `.agents/skills/engineering-workflow/references/gitnexus/gitnexus-guide/guide.md` |
| Index, status, clean, wiki CLI commands | `.agents/skills/engineering-workflow/references/gitnexus/gitnexus-cli/guide.md` |

<!-- gitnexus:end -->

## Available Agent Skills

This repo can use the current Codex skill set when a task matches the skill trigger. Keep this section as a compact routing index; load the corresponding `SKILL.md` only when needed.

### Documentation Lookup

- **tool-workflows**：使用 `.agents/skills/tool-workflows/SKILL.md` 处理 Context7/find-docs、prek/Husky hook 和项目 skill 管理。查询当前文档时，除非用户提供精确 `/org/project` ID，否则先 `resolve-library-id`，再用用户完整问题查询文档。
- **openai-docs**: Use for OpenAI product/API questions; prefer official OpenAI docs. (Routing-only — no local SKILL.md; loaded from Codex platform skills at runtime.)

### Code Intelligence And Git

- **engineering-workflow**：使用 `.agents/skills/engineering-workflow/SKILL.md` 处理 GitNexus 架构探索、调试、影响分析、重构、PR review、CLI 操作、交付循环、前端质量、设计原型和议题规划。编辑符号或提交前遵守上面的 GitNexus 要求。
- **GitHub skills**: Use for GitHub repository, issue, pull request, review-comment, CI, and publish/PR workflows.

### Development Workflow

- **engineering-workflow**：通过聚焦 reference 路由纪律化调试、TDD、代码审查、PRD、issue 拆分、triage、重构计划、界面设计探索、设计 grill 和一次性原型。

### Frontend And Docs Site

- **engineering-workflow**：使用其中的 frontend-quality 路由处理 docs 站点（`apps/docs`）的 React 诊断、视觉打磨、可访问性和健康检查。
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

## Project Context

> [English](../../AGENTS.md) | 中文

## Overview

Lingchu Bot 是一个基于 NoneBot2 的群管机器人。本 monorepo 包含 Python 后端插件（`nonebot-plugin-lingchu-bot`）和 Next.js 文档站（`apps/docs`）。

## Tech Stack

### Python Backend

- Python 3.13，由 `uv` 管理
- NoneBot2 + OneBot V11 适配器（Milky、QQ、OneBot V12 已停维，可通过 `tools/adapter_loader.py` 按需加载）
- `nonebot-plugin-alconna` 命令解析
- `nonebot-plugin-orm`（aiosqlite）异步数据库
- `nonebot-plugin-localstore` 文件存储
- Ruff（lint + format）、Pyright、ty（类型检查）、pytest（测试）

### Documentation Site (`apps/docs`)

- Next.js 16 + Fumadocs 16（静态导出）
- React 19、Tailwind CSS 4、TypeScript 6
- Vitest + @testing-library/react（单元测试）、ESLint（lint）
- 功能：i18n（zh/en）、RSS、Mermaid、Twoslash、EPUB 导出、LLM 友好文本（`/llms.txt`、`/llms-full.txt`）、文档关系图
- 所有 server components、route handlers 和 lib 函数均为 async
- Turborepo workspace、pnpm 包管理器

## Project Structure

```text
├── src/plugins/nonebot_plugin_lingchu_bot/   # Core NoneBot plugin
│   ├── core/           # Config, platform info, two-tier bot state (global + per-platform) with JSON5 persistence
│   ├── database/       # JSON5 store package, ORM models package (records/audit/blocklist + identity + registry) & CRUD helpers package
│   ├── handle/         # 平台/协议/实现命令处理器
│   │   └── qq/         # QQ 平台处理器
│   │       ├── commands/           # 共享命令定义（Alconna matchers、触发词）
│   │       └── adapters/           # 协议特定处理器
│   │           └── onebot11/{default,llonebot,napcat}/  # OneBot V11 处理器
│   ├── menu.py         # 菜单系统（页面、功能、可用性）
│   ├── i18n/           # Babel/gettext translations
│   ├── migrations/     # Alembic database migration scripts
│   ├── platforms/      # 适配器注册表和平台自有权限定义
│   │   └── qq/permissions.py # QQ 默认身份组与运行时身份解析
│   ├── permissions/    # UID 身份、平台账号、命令授权与 SUPERUSERS API
│   ├── repositories/   # Data access layer
│   │   ├── __init__.py      # Package init
│   │   ├── blocklist.py     # Blocklist repository
│   │   ├── message_store.py # Message store repository
│   │   ├── permissions.py   # Permission-system ORM repository
│   │   └── registry.py      # Platform/adapter/protocol registry seeding
│   ├── services/       # Business logic services
│   │   └── message_store.py # Message storage service
│   └── start/          # Startup & initialization
│       └── startup.py  # Startup hooks
├── apps/docs/          # Fumadocs documentation site
│   ├── content/docs/   # MDX content (zh + en)
│   ├── src/
│   │   ├── app/        # Next.js App Router pages & routes
│   │   ├── components/ # React components (graph-view, mdx, mermaid)
│   │   ├── lib/        # Shared logic (source, rss, build-graph, layout)
│   │   └── __tests__/  # Vitest unit tests
│   └── source.config.ts # Fumadocs MDX config
├── packages/           # Shared frontend packages
├── schema/             # JSON Schemas for config files (config.schema.json5, bot_state.schema.json5)
├── tools/                           # Standalone utility tools
│   ├── __init__.py
│   └── adapter_loader.py           # Deprecated adapter on-demand loader (Milky, QQ, OneBot V12)
├── Dockerfile          # Container runner generation via nb-cli
├── pyproject.toml      # Python project config
├── package.json        # Monorepo root (pnpm + Turborepo)
└── Taskfile.yml        # Task runner for CI/local commands
```

## Development Commands

> 开发时使用颗粒度命令获取更快反馈。仅在提交前运行 `task check` / `task test` 做完整验证。

### Python — Lint & Format

```bash
uv run -m ruff check . --output-format=github   # 仅 lint
uv run -m ruff check --fix .                     # 自动修复 lint 问题
uv run -m ruff format --check .                  # 仅格式检查
uv run -m ruff format .                          # 应用格式化
```

### Python — Type Check

```bash
uv run -m pyright .                              # Pyright 类型检查
uv run -m ty check --output-format github        # ty 类型检查
```

### Python — Test

```bash
uv run -m pytest                                 # 全部测试
uv run -m pytest tests/handle/commands/group/    # 指定测试目录
uv run -m pytest -k "test_mute"                  # 按关键字筛选
uv run -m pytest --lf                            # 重跑上次失败的测试
```

### Python — 多语言测试

`tests/conftest.py` 提供两个参数化 fixture 和一个标记，用于在单个 pytest 会话中测试 `zh_CN` 和 `en_US` 两种 locale：

| Fixture | 是否修改全局状态 | 适用场景 |
|---------|------------------|----------|
| `locale` | 否 — 仅返回 locale 字符串 | 测试显式传入 `locale=` 参数调用 gettext 辅助函数（如 `gettext(msg, locale=locale)`） |
| `configured_locale` | 是 — 调用 `_read_configured_locale.cache_clear()` 并 monkeypatch 使其返回参数化 locale | 测试依赖 `get_configured_locale()` 或 `_()` 简写（无显式 locale 参数） |

- **`i18n` 标记**：在 `pytest_configure()` 中通过 `config.addinivalue_line("markers", ...)` 注册。用 `@pytest.mark.i18n` 标记多语言测试，可通过 `-m i18n` 筛选。

**示例：**

```python
@pytest.mark.i18n
def test_gettext_explicit(locale):
    """使用 `locale` fixture — 不修改全局状态。"""
    assert gettext("禁言", locale=locale)  # 显式传入 locale


@pytest.mark.i18n
def test_configured_locale(configured_locale):
    """使用 `configured_locale` fixture — patch 缓存的 locale。"""
    assert _("禁言")  # 经 get_configured_locale() 读取
```

> **为什么需要两个 fixture？** `_read_configured_locale()` 被 `@lru_cache(maxsize=1)` 装饰，首次调用后结果会在整个会话中缓存。`configured_locale` fixture 清除该缓存并 monkeypatch 该函数，使每个参数化 locale 生效。详见"绕过 lru_cache 进行多语言测试"经验。

### Docs Site — Lint & Type Check

```bash
pnpm --filter docs lint                          # ESLint（docs 站点）
pnpm turbo run check-types                       # TypeScript 类型检查（所有工作区）
pnpm --filter docs exec tsc --noEmit             # TypeScript 检查（仅 docs）
```

### Docs Site — Test

```bash
pnpm --filter docs test                          # Vitest（docs 站点）
pnpm --filter docs run test:e2e:hook             # Playwright Chromium 冒烟测试
pnpm --filter docs run test:e2e                  # Playwright 全部配置浏览器
```

### Docs Site — Dev & Build

```bash
pnpm --filter docs dev                           # 开发服务器
pnpm turbo run build --filter=docs               # 生产构建
```

### Markdown Lint

```bash
pnpm exec markdownlint-cli2 {{.MD_GLOB}}         # 检查（MD_GLOB 见 Taskfile.yml）
pnpm exec markdownlint-cli2 --fix {{.MD_GLOB}}   # 自动修复
```

### i18n

```bash
task i18n                                        # 提取 + 更新 + 编译翻译
```

### Task Runner — Full Verification

```bash
task check                                       # 全部静态检查（ruff lint + format + markdown + ESLint + pyright + ty + tsc）
task test                                        # 全部测试（pytest + Vitest）
task ci                                          # check + test + build
```

### Quick Reference: What to Run When

| What changed          | Minimum checks before commit                                                      |
| --------------------- | --------------------------------------------------------------------------------- |
| Python source only    | `ruff check` + `ruff format --check` + `pyright` + `ty check` + `pytest`         |
| Docs site only        | `pnpm --filter docs lint` + `pnpm --filter docs test` + `pnpm --filter docs run test:e2e:hook` + `pnpm turbo run check-types --filter=docs` + `pnpm --filter docs lint:links` |
| Markdown only         | `markdownlint-cli2`                                                               |
| i18n strings          | `task i18n` + `pytest`                                                            |
| Mixed / unsure        | `task check && task test`                                                          |

## Git Hooks

- **pre-commit**: 条件触发检查（v3 — 颗粒度化）— Prek auto-fix（始终）→ Markdownlint via `markdownlint-cli2`（`.md` 变更时，使用与 `Taskfile.yml` 的 `MD_GLOB` 相同的 glob）→ Ruff lint/format（Python 变更时）→ Pyright/ty（Python 变更时）→ pytest（Python 变更时）→ ESLint via `pnpm turbo run lint`（代码/样式/配置变更时 — `NEEDS_LINT`：docs `.ts`/`.tsx`/`.mjs`/`.mts`/`.css`/配置，packages `.ts`/`.tsx`/`.mjs`/`.mts`/`.js`/`.css`；纯 `.mdx`/`.json` 内容变更跳过）→ check-types via `pnpm turbo run check-types`（任意前端变更时 — `NEEDS_TYPE_CHECK`）→ Docs Vitest（docs 代码/内容/配置变更时 — `NEEDS_DOCS_TEST`；纯 `.css` 样式变更跳过）→ Docs Playwright Chromium 冒烟测试（任意 docs 变更时）→ React Doctor（仅 `.tsx` 变更时 — `NEEDS_REACT_DOCTOR`，优先全局/本地安装，回退到 `pnpm dlx` 缓存，最终兜底 `npx -y`）→ Gitnexus analyze（始终，非阻断，优先 `node_modules/.bin/gitnexus` 直接调用，零下载）
- **commit-msg**: gitmoji + Conventional Commits 格式校验 + 自动追加 Signed-off-by（含 trailer 块检测）
- **prepare-commit-msg**: 通过 `node_modules/.bin/gitmoji --hook` 直接启动交互式 gitmoji（零 pnpm/npx 开销；若本地缺失则回退 npx / 全局 gitmoji）
- **CLI 解析顺序**（所有 hooks 统一）：本地 `node_modules/.bin/<bin>` → 全局 PATH → 全局 `.cmd` shim → `pnpm dlx` 缓存（对非 devDep 工具的最终兜底：`npx -y`）
- Set `$env:HUSKY='0'` to skip hooks when needed (e.g., automated commits)

## Agent Preferences

以下规则作为上下文注入每次对话，视为硬约束。

- **未经用户明确指示不得提交或推送** — 绝不自动提交、自动推送，或假设用户在完成任务后需要提交。等待用户明确要求。
- **持久偏好写入 AGENTS.md** — memory 文件和会话上下文都是临时的；AGENTS.md 是项目级规则和用户偏好的唯一真实来源。当用户说"记住这个"或表达偏好时，写到这里。
- **Pre 策划开发阶段** — 本项目仍处于 Pre 策划 / 早期开发阶段；当严重破坏性变更能简化架构或推进目标产品方向时，可以接受这类变更。
- **优先使用颗粒度检查而非完整 `task check`** — 使用上方的 Quick Reference 表，只运行与变更相关的检查。完整 `task check && task test` 用于提交前验证，而非每一步中间操作。
- **使用不加载配置文件的 PowerShell** — 在自动化中显式调用 PowerShell 时，使用 `pwsh.exe -NoProfile`，避免用户配置脚本拖慢命令或污染输出。
- **同步中英文文档** — 编辑 AGENTS.md 时，始终将相同的结构变更同步到 `.github/note/AGENTS-zh.md`，反之亦然。
- **同步 AGENTS.md 和 CLAUDE.md** — 这两个文件共享相同的结构和内容（GitNexus 块、项目上下文、开发命令、经验教训等）。编辑任一文件时，始终将相同的结构变更同步到另一个。唯一允许的差异是 Claude Code 行为准则段落，仅存在于 `CLAUDE.md` 中。

## AI 上下文注入地图

所有向 AI 编码代理注入上下文的文件和目录。使用此地图了解每个注入点的作用和加载时机，避免重复读取。

### 根级文件

| 文件 | 加载时机 | 用途 |
|------|----------|------|
| `AGENTS.md` | 每次对话（Trae、Codex） | 项目规则、约定、开发命令、经验教训的唯一真实来源。也包含 GitNexus 配置块。 |
| `CLAUDE.md` | 每次对话（Claude Code） | 与 `AGENTS.md` 相同角色，但面向 Claude Code。包含 GitNexus 块、项目上下文、开发命令和行为准则（简洁优先、精准修改、目标驱动执行）。大部分内容与 `AGENTS.md` 重复。 |

### Trae IDE 规则（`.trae/rules/`）

| 文件                           | 加载时机       | 用途                                                     |
| ------------------------------ | -------------- | -------------------------------------------------------- |
| `.trae/rules/git-commit-message.md` | 始终应用（Trae） | Gitmoji + Conventional Commits 格式规范。通过正则校验强制执行提交信息格式。 |

### 技能目录

技能**按需加载** — 仅当用户任务匹配触发条件时加载，不会注入每次对话。

#### `.agents/skills/`（Trae / Codex）

| 技能                           | 触发条件                                       | 用途                                                                                                     |
| ------------------------------ | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `available-skills/`            | 选择加载哪个技能时                             | 所有可用技能的紧凑路由索引。列出项目本地、编码、前端、云、制品和技能创作技能。                             |
| `engineering-workflow/`        | 代码理解、GitNexus、调试、TDD、review、前端质量、设计和议题规划 | 合并后的工程入口，包含 GitNexus、delivery-loop、design-prototyping、frontend-quality 和 issue-planning reference。 |
| `tool-workflows/`              | 文档查询、hooks、prek/Husky 和 skill 维护       | 合并后的工具入口，包含 Context7 文档、仓库 hooks 和 skill 管理 reference。                                |

### 跨语言对应文件

| 文件                      | 用途                                                                   |
| ------------------------- | ---------------------------------------------------------------------- |
| `.github/note/AGENTS-zh.md` | `AGENTS.md` 的中文翻译。必须与结构变更保持同步。                       |

### 自动注入的内容

仅以下内容在**每次**对话中自动注入，无需显式加载：

1. **`AGENTS.md`**（Claude Code 中为 `CLAUDE.md`）— 完整文件内容
2. **`.trae/rules/git-commit-message.md`** — 仅 Trae，始终应用
3. **技能描述** — 每个 `SKILL.md` frontmatter 中的 `description` 字段列在工具的 `available_skills` 中，但完整的 `SKILL.md` 内容仅在技能被调用时加载

其他所有内容（技能文件、参考文档、清单）仅在匹配任务触发技能时**按需加载**。

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
- **🎭 Playwright**: Docs E2E workflow for `apps/docs` and `packages` changes. It installs Playwright browsers with system dependencies, runs `pnpm --filter docs run test:e2e`, and uploads HTML report / trace artifacts.
- **👷 CI-builds**: Build verification on Python/package changes
- **📚 Docs Deploy**: Build and deploy to GitHub Pages on push to main/dev
- **🩺 React Doctor**: React codebase health check on PRs (uses CLI, not the action — see Lessons Learned)
- **🧹 Clear Workflow**: Stale workflow cleanup
- **🏷️ Issues Top**: Issue triage automation

## Engineering Conventions

### `fire_and_forget` 辅助函数

- **位置**：`src/plugins/nonebot_plugin_lingchu_bot/core/async_utils.py`
- **签名**：`fire_and_forget(coro, *, name="fire_and_forget")`
- **适用场景**：可丢弃的后台操作（审计日志、遥测、缓存写入），调用者不需要其结果。该辅助函数将协程调度为 `asyncio.Task`，在模块级 set 中跟踪，并通过 done-callback 中的 `logger.exception` 记录异常。
- **不适用场景**：调用者需要结果的操作，或函数返回前必须完成的操作。这些情况下直接使用 `await`。
- **引用管理**：辅助函数将任务存储在模块级 set 中，防止 Python GC 过早取消；done-callback 在记录任何异常后移除引用。

### 结构化请求对象

- **仓储 API**：需要多项关联字段的写入/审计 API 优先使用冻结 dataclass 请求对象。例如 `repositories/blocklist.py` 中的 `BlocklistUpsert` 和 `repositories/message_store.py` 中的 `AuditEvent`。
- **命令审计**：命令审计载荷使用 `handle/qq/adapters/onebot11/default/common.py` 中的 `CommandAudit`，再传给 `record_audit_fire_and_forget()` 或 `record_command_audit()`。
- **不要新增长参数列表**：如果新 helper 需要 platform、adapter、bot、group、target、reason、duration 等多个耦合字段，定义请求对象，而不是继续扩展函数签名。

### 命令处理器状态控制（静默模式与处理门控）

- **位置**：`src/plugins/nonebot_plugin_lingchu_bot/core/bot_state.py`
- **两层状态模型**：维护全局状态加按平台覆盖的 `handle_active`（门控，默认 `True`）和 `silent_mode`（默认 `False`）标志。状态通过 `get_plugin_data_dir()` 持久化到插件数据目录的 `bot_state.json5` 文件。
- **解析语义**：
  - `is_handle_active(platform_id)`：全局 AND 平台 —— 全局 OFF 时禁用所有平台。
  - `is_silent_mode(platform_id)`：全局 OR 平台 —— 全局 ON 时静默所有平台。
  - 两个函数现在都要求传入 `platform_id` 参数。
- **`selected_adapter_handle` 参数**：`handle/qq/commands/common.py` 中的装饰器接受 `bypass_gate: bool = False` 和 `bypass_silent: bool = False` 关键字参数。它通过 `get_platform_profile` 从 `adapter_id` 解析 `platform_id`。两个绕过标志均为 `False`（默认）时，handler 被 `_state_wrapper` 包装，同时强制处理门控和静默模式。
- **`_state_wrapper`**：接受 `platform_id`、`check_gate` 和 `check_silent` 参数。包装器链顺序：`_state_wrapper`（最外层）→ `_permission_wrapper` → `func`。`_state_wrapper` 先检查门控（处理未激活时提前返回），再检查静默模式（静默时路由到 `_silent_call`）。
- **`_silent_call`**：临时将 `command.finish` 替换为不发送消息的版本（抛出 `FinishedException`），使 handler 执行其逻辑但不发送响应消息。原始 `finish` 在 `finally` 块中恢复。
- **命令控制全局状态**：4 个命令（"闭嘴"/"说话"/"开机"/"关机"）通过 `set_global_silent_mode()` 和 `set_global_handle_active()` 函数控制全局状态。
- **命令绕过设置**：
  - "闭嘴"/"说话"（静默/解除）使用 `bypass_silent=True` —— 始终响应，但在机器人关机（门控关闭）时禁用。
  - "开机"/"关机"（启动/关闭）同时使用 `bypass_gate=True` 和 `bypass_silent=True` —— 必须始终能工作以从任何状态恢复机器人。
- **菜单**："bot-control" 页面被替换为 "system-management" / "系统管理" 顶层页面，包含子页面 "silent-mode" / "静默模式" 和 "handle-gate" / "开关机"。

### 配置管理

- **Pre-commit hooks**：`prek.toml` 是 pre-commit hook 配置的唯一真实来源。已移除遗留的 `.pre-commit-config.yaml` —— 不要重新引入。
- **版本同步**：`Taskfile.yml` 的 `ci:version:write-config` 任务将项目版本写入 `src/plugins/nonebot_plugin_lingchu_bot/core/config.py`（Python `__version__`）和 `apps/docs/package.json`（`version` 字段）。升级版本时运行此任务，而非手动编辑文件。
- **JSON Schemas**：仓库根目录的 `schema/` 目录包含用于校验 JSON5 配置文件的 JSON Schema 文件：`config.schema.json5`（对应 `config.json5`）和 `bot_state.schema.json5`（对应 `bot_state.json5`）。支持 `$schema` 注释的编辑器可引用这些文件获得自动补全和校验。
- **Skills 排除列表同步**：`pyproject.toml` 中的 skills 排除列表有注释标注 "skills 排除列表同步至 prek.toml" —— 更新一个配置的排除模式时，需同步另一个。

## Lessons Learned

> **时效性警示**：以下经验反映的是编写时代码库和依赖的状态。在依赖任何经验之前，请先验证其是否仍然成立——API 会变、包会新增导出、CI 配置也会演进。当经验过时时，应更新或删除，而非传播过时假设。

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

群命令触发词按 locale 互斥启用。不要为同一个 matcher 同时注册中文和英文命令触发词。应通过 i18n locale 解析辅助（`LINGCHU_LOCALE`、`lc_locale`、`locale` 经 `get_configured_locale()`）在命令注册时选择一种触发语言，并确保未选中的语言不会进入 `aliases`。

### Layered Menu Commands

将菜单分类升级为独立命令时，注册分类 matcher 前必须审计它是否与现有功能命令别名冲突。顶层 `菜单` / `menu` 应保持为索引入口，并与分类页分别测试，这样功能过滤断言才会落在实际渲染功能行的页面上。

### Permission System Boundaries

平台默认身份组定义在 `platforms/qq/permissions.py` 等平台模块中；核心 `permissions/` 包只消费 seed 和运行时解析器，不应硬编码平台角色树。命令权限检查、菜单过滤和 handler 装饰器都使用 `MENU_FEATURES.command_key` 作为共享命令标识。菜单应 fail closed，隐藏当前身份不可执行的命令。SUPERUSERS 可以通过公开异步 API CRUD 自定义平台身份组和成员关系，但 builtin 平台组由平台模块 seed，不应被管理接口覆盖。

### Adapter API Differences

Same-named APIs return different types across adapters:

| API | OneBot V11 | Milky |
| --- | ---------- | ----- |
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

- 许多 handler 会把 gettext helper 导入为 `_`。不要在这些函数里把 `_` 当作一次性局部变量使用（例如 `deleted, _ = ...`），否则会遮蔽 gettext helper，并让后续 `await _("...")` 在运行时失败。可改用 `result = ...; deleted = result[0]`，或在 gettext 密集作用域外使用更明确的未使用变量名。

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

- 作为 Python 包导入的目录片段必须是合法 Python 标识符，这样运行时导入和静态工具都能解析。协议版本目录优先使用带字母前缀的形式，例如 `v1_2` 而不是 `1_2`；`importlib` 可能能加载数字开头的文件夹，但 `ty` 无法可靠解析。

### ESLint 主版本兼容性

- **`eslint-plugin-react@7.x` 与 ESLint 10 不兼容。** 该插件调用 `context.getFilename()`，而 ESLint 10 的破坏性变更将其移除，改为 `context.filename`。这会在加载时引发 `TypeError: contextOrFilename.getFilename is not a function`。
- **修复方案**：(a) 在使用 `eslint-plugin-react` 的包中将 ESLint 固定到 v9；(b) 迁移到 `@eslint-react/eslint-plugin`（v5+，支持 ESLint 10）；(c) 等待 `eslint-plugin-react` 发布对 ESLint 10 的支持。
- **预防**：运行 `pnpm install` 后，提交前务必检查 `package.json` 文件的 `git diff` —— `pnpm install` 可能会静默地将 `^` 范围依赖升级到更新的主版本，从而破坏兼容性。

### CI 工作流项目引用

- 当工作区包被禁用或移除时，**所有引用它的 CI 工作流都必须更新**。例如，React Doctor 的 `--project docs,web` 标志在 `web` 没有 React 源码时会失败。
- **规则**：任何工作区包变更（禁用、移除、重命名）后，grep 所有工作流文件查找对该包名的引用并更新。

### Markdown 表格对齐（MD060）

- `markdownlint-cli2` v0.22+ 强制执行 MD060（表格列样式）。默认样式 `aligned` 要求视觉上的管道符对齐，但对 CJK 字符并不可靠，因为字符显示宽度（CJK 为 2 列）与字符数（源码中每个 CJK 字符为 1）不一致。
- **修复**：在 `.markdownlint.jsonc` 中将 MD060 样式设为 `consistent` —— 这只要求每列的管道符在所有行的相同字符位置出现，不要求视觉对齐。这对纯 ASCII 和 CJK/拉丁混合表格都能正确工作。
- **不要**完全禁用 MD060 —— `consistent` 样式仍能捕获真正的格式错误（缺失管道符、列数不一致），同时避免 CJK 宽度不匹配导致的误报。

### Git Hooks Optimization

- **Pre-commit 应按变更文件类型条件触发检查（v3 — 颗粒度化）**：用 `git diff --cached --name-only --diff-filter=ACMR` 收集暂存文件，通过 `has_pattern()` 检测文件后缀/路径，无 Python 变更时跳过 Ruff/Pyright/ty/pytest。前端变更拆分为 docs 5 类（CODE/TSX/CONTENT/STYLE/CONFIG）和 packages 2 类（CODE/CONFIG），派生独立条件：`NEEDS_LINT`（纯 `.mdx`/`.json` 内容变更跳过 ESLint）、`NEEDS_TYPE_CHECK`（任意前端变更）、`NEEDS_REACT_DOCTOR`（仅 `.tsx` 变更）、`NEEDS_DOCS_TEST`（纯 `.css` 样式变更跳过 Vitest），并在任意 docs 变更时运行 `test:e2e:hook`，视变更类型可节省 30-90 秒，同时保留 docs 导航冒烟测试
- **CI workflows 应与 pre-commit v3 颗粒度化保持一致**：`🧪-ci.yml` workflow 使用 `changes` 检测 job，通过 `git diff --name-only`（PR 对比 base，push 对比 `HEAD~1`）输出布尔标志（`python`/`markdown`/`frontend`/`frontend-code`/`frontend-style`/`frontend-content`/`frontend-tsx`）。下游 job 在 `if` 条件中使用 `needs.changes.outputs.<flag> == 'true'`：`static-analysis`（Python 或 markdown）、`tests`（Python）、`docs-check`（任意前端）。`docs-check` 内部，ESLint 在 `frontend-code || frontend-style` 时运行（对应 `NEEDS_LINT`），check-types 在任意前端变更时运行（对应 `NEEDS_TYPE_CHECK`），Vitest 在 `frontend-code || frontend-content` 时运行（对应 `NEEDS_DOCS_TEST`，跳过纯 `.css`）。`auto-format` 使用 `always()` 配合 `needs.<job>.result != 'failure'` 处理被跳过的上游 job。`🩺-react-doctor.yml` workflow 将 `paths` 收窄为仅 `.tsx`（对应 `NEEDS_REACT_DOCTOR`）。一致性确保本地与 CI 行为匹配。
- **Signed-off-by 追加需检测 trailer 块**：已有 trailer（如 `Closes #`、`BREAKING CHANGE:`、`Reviewed-by:`）时应追加到同一块（无空行分隔），无 trailer 时才用空行分隔
- **空行清理不能破坏消息结构**：`sed '/^$/N;/^\n$/d'` 会删除所有连续空行，破坏 subject-body-trailer 结构；应仅压缩 ≥3 连续空行为 2 个
- **重复签名检测需忽略尾部空白**：`grep -qF` 可能因行尾空白差异误判，应先 `sed 's/[[:space:]]*$//'` 去尾空白再 `grep -qxF` 精确整行匹配
- **空消息体不应追加 Signed-off-by**：空提交消息由格式校验拦截即可，追加签名到空文件无意义

### Windows Commands in Bash Hooks

- Husky hook 可能运行在 Bash 环境中，这时 Windows 命令与 PowerShell 中的表现不同。不要只判断 `command -v` 能找到命令，还要确认命令能实际启动。
- Hook 顶部应集中解析工具命令。对于 `pnpm.cmd`、`npx.cmd` 这类 Windows `.cmd` Node shim，应通过 `cmd.exe /c` 调用；在 Bash 中直接执行 `.cmd` 文件可能静默跳过检查，或输出误导性的 `node` 错误。
- 用暂存区文件决定检查范围时，不要吞掉 `git diff --cached` 失败。如果 hook shell 中没有可用的 `git`，应明确失败，而不是把暂存文件列表当成空。

### PowerShell Markdownlint Glob

- 通过 `pwsh.exe -NoProfile -Command` 运行 `markdownlint-cli2` 时，glob 参数必须按目标 shell 实际接收的形式传入；错误的嵌套或转义引号会把 glob 变成异常路径，让 Node 扫描远超预期的内容。将 markdownlint 超时视为 lint 失败前，优先使用 Taskfile 命令或已验证的直接命令形式。

### Markdownlint 按目录覆盖

- `markdownlint-cli2` 支持分层配置：子目录中的 `.markdownlint.jsonc` 文件覆盖该目录下文件的根配置。
- **重要**：子目录的 `.markdownlint.jsonc` 会**替换**（而非合并）根配置的规则。必须在子目录配置中包含所有根设置（如 `MD013: false`、`MD033: false`、`MD041: false`、`MD060` 配置），再加上额外的规则抑制。
- `.github/.markdownlint.jsonc` 为 `.github` 文档禁用了 MD022（标题周围空行）和 MD032（列表周围空行），因为 AGENTS-zh.md 中的 CJK 内容频繁触发这些规则但并无实际格式问题。

### Husky Hook 中的 CLI 解析

- `npx <bin>` 和 `pnpm exec <bin>` 总会重新解析包，即使 `node_modules/.bin/<bin>` 已经存在。在热缓存中仍需付出子进程启动、npm 注册表 HEAD 请求、lockfile 检查的开销；冷缓存时更会下载完整 tarball。这两种开销对 `gitnexus analyze`、`gitmoji --hook` 这类轻量检查来说都会成为 hook 时长的主要瓶颈。
- **Husky hook 中 JS CLI 的解析顺序**：`node_modules/.bin/<bin>`（devDep shim，零下载）→ 全局 `PATH`（`command -v <bin>` 加可运行性检查）→ 全局 `.cmd` shim（仅在没有原生时通过 `cmd.exe /c` 调用）→ `pnpm dlx <bin>` 缓存 → `npx -y <bin>`（最后兜底，仅用于必须按需拉取的非 devDep）。
- 对 `package.json` 已保证的 devDep（如 `gitmoji-cli`、`gitnexus`），只要 `pnpm install` 已执行，本地 `node_modules/.bin/<bin>` 分支应始终命中，常见路径下完全不需要回退到 `npx`。
- 在 hook 顶部把解析后的工具引用缓存到变量中，在多个阶段复用；避免在循环或逐文件逻辑里重复调用 `command -v`。
- 使用 `.cmd` shim（Windows Node shim，如 `pnpm.cmd`、`npx.cmd`）时，必须通过 `cmd.exe /c <shim> ...` 调用 —— 在 Git Bash 中直接运行 `.cmd` 可能静默退出并报误导性的 `node` 错误。

### Switching i18n Default Locale

- **Fumadocs 语言包**：`@fumadocs/language` 导出其支持的语言包（如 `zh-cn`、`zh-tw`）；英语（`en-us`）默认内置，无需单独导入。切换默认语言为英语时，`layout.shared.tsx` 只需 `preset('zh', zhCN())` 加载中文语言包，无需导入英语包。在假设某个 locale 是否可用之前，务必检查 `@fumadocs/language` 当前的导出列表。
- **测试环境覆盖 locale 而非改断言**：将 Python `DEFAULT_LOCALE` 从 `zh_CN` 改为 `en_US` 后，所有断言中文翻译的测试会失败。正确做法是在 `tests/conftest.py` 的 `nonebot.init()` 中加 `"lingchu_locale": "zh_CN"` 覆盖回中文，避免逐个修改数百条测试断言，同时验证了 locale 配置覆盖机制。
- **Fumadocs i18n 文件命名约定**：默认语言的 MDX 文件不加后缀（`page.mdx`），非默认语言加 locale 后缀（`page.zh.mdx`）；`meta.json` 同理。切换默认语言时需批量重命名内容文件。

### 绕过 lru_cache 进行多语言测试

- **问题**：i18n 模块的 `_read_configured_locale()` 被 `@lru_cache(maxsize=1)` 装饰。首次从 NoneBot 配置读取 locale 后，结果会在整个会话中缓存。这导致无法在单个 pytest 会话中对同一测试同时验证 `zh_CN` 和 `en_US` —— 第二个 locale 永远不会生效，因为会返回缓存值。
- **解决方案**：`tests/conftest.py` 中的 `configured_locale` fixture 调用 `_read_configured_locale.cache_clear()` 丢弃缓存值，再通过 `monkeypatch.setattr(...)` 替换该函数使其返回参数化 locale。这样参数化测试可以按参数切换 locale，不受会话级缓存干扰。
- **何时用哪个 fixture**：测试显式向 `gettext()`/`ngettext()` 传入 `locale=` 时用 `locale`（不修改全局状态）。仅当测试依赖 `get_configured_locale()` 或 `_()` 时才用 `configured_locale`，否则缓存函数会返回错误的 locale。

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

### React Doctor 集成

- **CLI 自动生成的文件需要手动定制**：`npx react-doctor@latest install` 会创建 GitHub Actions 工作流和 npm 脚本，但不会匹配项目规范。运行 CLI 后务必定制：emoji 工作流名称、固定 action SHA、触发路径过滤、monorepo 的 `project` 作用域、`blocking` 级别。
- **避免使用 `millionco/react-doctor@v2` action 直至上游修复发布**：该 action 存在已知 bug——detached HEAD 导致 diff 回退、ANSI 转义码泄漏到 PR 评论（上游 PR #80 待合并）。改用 CLI 直接运行（`npx react-doctor@latest`）并设置 `NO_COLOR=1` 环境变量。上游修复发布后重新评估。
- **CI 中使用 `--fail-on error` 而非 `warning`**：React Doctor 的 `blocking: warning` 会导致任何 warning 都使 CI 失败（退出码 1）。使用 `--fail-on error` 仅在错误级别阻断；warning 应为信息性提示。pre-commit hook 同理——仅阻断错误。
- **`doctor.config.ts` 应记录规则覆盖原因**：将规则设为 `warn`/`off` 时，添加注释说明原因（如 fumadocs 生成的导出是框架必需的但被标记为未使用）。这防止后续贡献者盲目重新启用。
- **SVG 元素必须使用 `createElementNS`**：即使在测试代码中，`document.createElement('svg')` 也是错误的——应使用 `document.createElementNS('http://www.w3.org/2000/svg', 'svg')`。Linter（Edge Tools、hint）会标记此问题，且影响 SVG 渲染行为。
- **`useMDXComponents` vs `getMDXComponents`**：Fumadocs MDX 约定导出 `useMDXComponents` 用于 MDX provider 模式（`source.config.ts` 中的 `providerImportSource`）。即使项目当前通过 `components` prop 显式传递 `getMDXComponents()`，也应保留 `useMDXComponents`，因为它是 fumadocs 自动 MDX 组件解析的标准入口点。在 `doctor.config.ts` 中抑制 `deslop/unused-export` 以处理框架必需的重导出。

### 查询官方文档验证框架语法

为 Fumadocs（或任何框架）编写 MDX 内容时，**绝不假设语法** — 始终对照官方文档和项目实际配置进行验证。示例：

- Fumadocs 使用 `<Callout>` JSX 组件做提示框，**不是** GitHub 风格的 `>[!NOTE]` 引用块。`>[!NOTE]` 语法只会渲染为普通引用块，而非带样式的提示框。
- 在 MDX 中使用任何框架特有的组件或语法前，检查：(1) 通过 Context7 / find-docs 查阅框架官方文档，(2) 项目内容文件中的已有用法，(3) MDX 组件提供者配置（如 `source.config.ts`、`mdx.tsx`）。

经验法则：**如果在项目现有内容文件中没见过该语法，先查官方文档再写。**

### OneBot V11 处理器收口与适配器停维

- **5+ 个 OneBot V11 handler 文件中的代码重复**通过将共享辅助函数和常量收口到 `onebot11/default/common.py` 解决（`bot_self_id_safe()`、`bot_id()`、`default_block_reason()`、`default_admin_reason()`、`check_self_target()`、`store_block_record()`、`check_target_privilege()`、`check_bot_privilege()`、`record_command_audit()`；常量 `QQ_PLATFORM_ID`、`ONEBOT_V11_ADAPTER_ID`、`MUTE_DURATION_MIN`、`MUTE_DURATION_MAX`）。
- **缺少审计记录**通过新增 `record_command_audit()` 解决 —— 每个管理命令在执行成功后都会记录操作者、目标、动作和原因。
- **缺少权限预检**通过新增 `check_target_privilege()`（防止对管理员/群主操作）和 `check_bot_privilege()`（防止调用机器人无权限的 API）解决。
- **适配器停维**（Milky、QQ、OneBot V12）通过从 `platforms/registry.py` 和启动钩子流程（`handle/qq/adapters/__init__.py`、`handle/menu.py`）中移除来解决，同时保留源码文件并添加 `DEPRECATED = True` 标记和停维说明 docstring。
- **复用需求**通过独立的 `tools/adapter_loader.py` 模块解决，提供 `load_deprecated_adapter()`、`load_and_init_deprecated_adapter()` 和 `list_deprecated_adapters()` 用于按需加载，不参与正常启动流程。
- **关键经验**：停维适配器时，应将其移出启动流程但保留源码并添加停维标记；提供独立的加载工具用于按需访问。收口重复 handler 逻辑时，应将共享辅助函数提取到单一 `common.py` 模块，而非在各 handler 文件中保留副本。

### 权限 API 集成与停维强制提示

- 权限系统现在通过 OneBot V11 `get_group_member_info` API 主动验证用户角色，确保门禁生效。
- 停维适配器（`~milky`、`~qq`、`~onebot.v12`）现在触发 `PlatformAdapterDeprecatedError` 并提供清晰指引，而非被当作"未知"处理。
- 平台权限模块通过注册表中的 `PlatformProfile.permission_module` 字段动态发现，消除了 `permissions/platforms.py` 中的硬编码模块路径。
- 关键经验：停维功能时应提供清晰的退出时反馈而非静默移除；权限门禁依赖被动事件数据时，应添加主动 API 验证作为回退。

### CI 可选依赖类型检查与 i18n 维护
- 将依赖移至 `[project.optional-dependencies]`（如 `deprecated-adapters`）后，CI 测试任务必须使用 `uv sync --frozen --extra deprecated-adapters` 安装——否则导入这些包的测试文件会因 `ImportError` 失败。
- `pyproject.toml` 中的 Pyright/ty 排除列表必须包含停维适配器源码目录（如 `src/.../handle/qq/adapters/milky`）——否则类型检查会因静态分析环境中未安装的包而报 `reportMissingImports` 错误。
- **`pybabel update` 行为**：自动将已删除的字符串标记为废弃（`#~` 前缀），并为相似 msgid 的条目添加 `fuzzy` 标记。运行 `pybabel update` 后，需手动检查 fuzzy 条目，移除 `fuzzy` 标记并修正翻译。
- **过期 msgid 处理**：当函数签名变更（如从格式字符串中移除 `reason` 参数）时，旧 msgid 变为过期。`pybabel update` 会检测相似性并创建 fuzzy 条目，但 msgstr 必须手动更新以匹配新 msgid。
- **关键经验**：停维含 i18n 字符串的代码时，代码变更后须运行 `task i18n` 提取/更新翻译。检查 fuzzy 条目和废弃条目。从类型检查中排除目录时，须同时添加到 `[tool.pyright]` 和 `[tool.ty.src]` 排除列表。

### OneBot V11 图片类 API 文件字段格式
- NapCat / OneBot V11 图片类 API（如 `set_group_portrait`）的 `file` 字段要求 `http(s)://`、`base64://` 或 `file://` 格式，直接传入裸本地路径（如 `C:\...` 或 `/tmp/...`）会被拒绝（`retcode=1200`, `file字段可能格式不正确`）。
- **修复**：将本地文件读取为 bytes，base64 编码后以 `base64://<encoded>` 格式传入。选择 `base64://` 而非 `file://` 的原因：bot 与 NapCat 可能运行在不同容器/文件系统中，`base64://` 在所有部署场景下都能工作。
- **异步文件 I/O**：在 async 函数中读取文件应使用 `await asyncio.to_thread(path.read_bytes)` 避免 `ASYNC240` 违规；直接调用 `path.read_bytes()` 会被 ruff 标记。
- **测试模式**：测试涉及文件读取的函数时，使用 `tmp_path` fixture 创建真实临时文件（`tmp_path / "test.png"` + `write_bytes(b"...")`），而非指向不存在的路径（如 `Path("/tmp/test.png")`）。
- **关键经验**：调用 OneBot V11 图片/文件类 API 时，务必将 `file` 字段转换为协议要求的格式；测试断言应验证格式前缀（`base64://`）而非裸路径字符串。

### 待回退变更

规则抑制和临时变通方案，在触发条件改变后应予回退。定期审查此节（如更新依赖或重构时）。

| 内容                                                    | 位置                                   | 抑制原因                                                                                                                             | 回退条件                                                                                                     |
| ------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| Pyright/ty 排除 `src/.../adapters/milky` | `pyproject.toml` `[tool.pyright]` 和 `[tool.ty.src]` | Milky 适配器移至可选依赖；静态分析环境未安装，导致 `reportMissingImports` | **回退条件已满足**：Milky 适配器已完全删除，需从 `pyproject.toml` 排除列表中移除该条目 |
| `deslop/unused-export: "off"`                           | `doctor.config.ts`                     | `mdx.tsx` 中的 `useMDXComponents` 是框架必需的重导出，但当前未被消费（`source.config.ts` 未配置 `providerImportSource`）               | 当 `useMDXComponents` 被实际消费后移除此抑制（如添加 `providerImportSource` 到 `source.config.ts` 或在其他地方导入它） |
| 使用 CLI 而非 `millionco/react-doctor@v2` action        | `.github/workflows/🩺-react-doctor.yml`   | 上游 action 存在 bug：detached HEAD、ANSI 泄漏到 PR 评论（PR #80 待合并）                                                             | 上游修复发布后切换回 action（关注 PR #80）                                                                     |

- **非组件导出破坏 Fast Refresh**：从组件文件（`mermaid.tsx`）导出工具函数（`getMermaidConfig`、`sanitizeMermaidSvg`、`renderMermaidSvg`）会触发 `react-doctor/only-export-components`。应将它们提取到独立的非组件模块（如 `mermaid-utils.ts`）并从那里导入。同时更新测试导入。
- **`/llms.txt` 是路由处理器而非静态文件**：从组件链接到 Next.js 路由处理器时，应使用 `<Link>`（而非普通 `<a>`）——它们是内部路由，可受益于客户端导航。

### 黑名单踢出行为：reject_add_request=False

从群中踢出黑名单用户时，`reject_add_request` 参数设为 `False`（而非 `True`）。这允许被拉黑的用户在解除拉黑或拉黑过期后重新申请加入群。如果业务需求变更为永久禁止重新加入，需更新 `handle/qq/adapters/onebot11/default/block.py` 中的 `_kick_blocked_user()` 及相应测试断言。

### 优先使用 CLI 自动修复工具

当 lint 或类型检查工具报告机械性问题（导入排序、未使用导入、格式化、简单样式违规）时，**始终优先使用 CLI 自动修复标志，而非逐条手动编辑**。这能节省大量时间并避免人为错误。

| 工具 | 自动修复命令 | 修复内容 |
|------|--------------|----------|
| Ruff | `uv run -m ruff check --fix .` | 导入排序（I001）、未使用导入（F401）、未使用变量、简单样式违规 |
| Ruff format | `uv run -m ruff format .` | 代码格式化（行长度、空白、引号） |
| Markdownlint | `pnpm exec markdownlint-cli2 --fix {{.MD_GLOB}}` | Markdown 格式化（MD060、MD009 等） |
| ESLint | `pnpm --filter docs lint --fix` | JS/TS lint 问题（未使用变量、格式化） |
| Prek | `prek run --all-files` | 依次运行所有 pre-commit 自动修复器 |

<Callout type="warn" title="自动修复无法处理的内容">

自动修复工具仅处理**机械性**问题。它们无法修复：
- 逻辑错误（TRY300 —— 将 return 移到 else 块需要理解控制流）
- 复杂度问题（PLR0911、PLR0913、C901 —— 需要提取辅助函数）
- 类型不匹配（Pyright/ty —— 需要理解预期类型）
- 布尔位置参数（FBT001/FBT002 —— 需要决定关键字专用 vs 位置参数）

对于这些，运行自动修复后手动重构。对于故意违反规则的情况，使用 `# noqa: <rule>` 注释（例如，对于有许多必需参数的 handler，遵循 `block.py` 模式使用 `PLR0913`）。

</Callout>

**工作流：**
1. 先运行 `uv run -m ruff check --fix .` —— 修复导入和简单样式问题
2. 运行 `uv run -m ruff format .` —— 应用格式化
3. 运行 `uv run -m pyright .` 和 `uv run -m ty check` —— 识别剩余的类型/逻辑问题
4. 仅手动修复自动修复无法处理的内容（复杂度、逻辑、类型不匹配）
5. 重新运行 `task check` 验证所有问题已解决

**经验法则**：如果发现自己手动修复同一规则超过 2-3 处，停下来检查是否有对应的自动修复标志。绝不要手动修复 I001（导入排序）或 F401（未使用导入）—— 始终使用 `ruff check --fix`。

### 远程管理命令（仅 OneBot V11）

8 个远程管理命令（`远程禁言`、`远程解禁`、`远程全体禁言`、`远程全体解禁`、`远程踢出`、`远程拉黑`、`远程删黑`、`远程公告`）仅支持 OneBot V11。它们定义在 `handle/qq/commands/remote.py`（Alconna matchers）中，实现于 `handle/qq/adapters/onebot11/default/remote.py`（handlers）。

关键行为：
- **群号解析**：`<群号|群名称>` 接受 `int`（直接）、数字 `str`（解析为 int）或非数字 `str`（通过 `get_group_list` 模糊匹配）。精确名称匹配优先；子串包含为回退。多个匹配时触发 `cmd_matcher.finish` 要求更精确的标识符。
- **上下文校验**：执行前，机器人检查自己在目标群中、具有管理员角色（对大多数命令）、目标用户在群中，且目标不是机器人或发送者。
- **远程踢出需要黑名单**：`远程踢出` 仅对已在黑名单中的用户生效。需先使用 `远程拉黑`。
- **远程公告版本门控**：需要 `LLOneBot >= 7.12.0` 或 `NapCat.Onebot >= 4.18.0`。菜单对不支持的实现隐藏此命令。

### 菜单系统架构

`handle/menu.py` 中的菜单系统使用分层模型 `MenuPage` → `MenuSection` → `MenuFeature` → `MenuAvailability`。添加新命令时：

1. 将命令触发词添加到 `handle/qq/commands/triggers.py` 的 `COMMAND_TRIGGERS` 中（zh 和 en 都要）。
2. 在 `handle/menu.py` 的 `MENU_FEATURES` 中添加 `MenuFeature` 条目，包含正确的 `command_key`、`section_id`、`summary`、`usage`、`platform_capability` 和 `availability` 元组。
3. 如果创建新菜单页（如 `remote-management` 这样的顶层分类），在 `MENU_PAGES` 中添加 `MenuPage` 条目，并确保它有用于子菜单触发词的 `command` 字段。
4. 更新 `tests/handle/commands/test_command_triggers.py` 中的 `EXPECTED_TRIGGERS` 以包含新触发词。
5. 更新 `tests/handle/commands/test_menu.py` 中的菜单测试，覆盖新功能在不同适配器/实现上下文下的可见性。
6. 更新 `apps/docs/content/docs/platforms/qq/commands.mdx`（及 `.zh.mdx`）中的新命令参考。

### 文档站点结构：平台 → 协议 → 实现

文档站点（`apps/docs/content/docs/`）将平台特定文档分离到专门的 `platforms/` 节：

```text
platforms/
├── index.mdx              # 层模型概览（平台 → 协议 → 实现）
└── qq/                    # QQ 平台
    ├── overview.mdx       # 协议优先级、实现矩阵
    ├── commands.mdx       # 完整 QQ 命令参考（含远程管理）
    └── onebot-v11/        # OneBot V11 协议
        ├── overview.mdx   # 协议概览、运行时检测
        ├── default.mdx    # 默认实现（核心命令 + 远程管理）
        ├── napcat.mdx     # NapCat 扩展（公告 + 头像）
        └── llonebot.mdx   # LLOneBot 扩展（公告）
```

`user-guide/commands.mdx` 现在是高层概览，链接到平台特定页面而非重复命令详情。添加新命令或更改可用性时：

1. 更新 `platforms/qq/commands.mdx`（及 `.zh.mdx`）的完整命令参考
2. 如果命令是实现特定的，更新相关实现页面（如 `platforms/qq/onebot-v11/napcat.mdx`）
3. 仅在高层菜单结构或过滤规则变更时更新 `user-guide/commands.mdx`
4. 如果项目源码结构变更，更新 `developer-guide/introduction.mdx`

### Docs CI 和单元测试覆盖

为文档站点（`apps/docs/`）添加 CI 检查或单元测试时，出现过以下陷阱：

1. **MDX 表格中的 `|` 破坏内联代码跨度**：在 markdown 表格单元格内，`<群号|群名称>` 会被解析为三个表格列（`<群号`、`群名称>`），从而将 `<...>` 暴露为 JSX 并导致 "Unexpected end of file in name" 构建错误。应将 `|` 替换为 `或` / `_or_`（与现有风格一致，如 `<用户ID或@提及>`）。此规则同时适用于 `.mdx` 和 `.zh.mdx` 文件。

2. **`fumadocs-mdx` node loader 无法处理图片资源**：`lint:links` 脚本使用 `fumadocs-mdx/node` 的 `register()` 加载 MDX 文件以进行链接验证。当 MDX 文件导入 `.png`/`.jpg`/`.svg` 时，loader 的 `load` 钩子会调用 `nextLoad`，到达 Node 默认加载器并抛出 `ERR_UNKNOWN_FILE_EXTENSION`。解决方法是通过 `node:module` 的 `module.registerHooks()`（Node.js 23+）注册一个 `load` 钩子，对图片文件扩展名返回 `export default undefined;`。在 `scripts/lint.mts` 顶部、导入 `fumadocs-mdx/node` 之前添加此钩子。

3. **`next-validate-link` 从根索引页的 URL 解析**：根索引页（如 `platforms/index.mdx`）的 URL 没有尾部斜杠（`/docs/platforms`），因此相对链接如 `./qq` 会解析为 `/docs/qq` 而非 `/docs/platforms/qq`。从根索引页链接时应使用绝对 URL（如 `/docs/platforms/qq/overview`）。目录链接（如 `./onebot-v11`）必须包含具体页面后缀（`./onebot-v11/overview`）——纯目录链接无法通过验证。

4. **提取共享函数以提高可测试性**：当函数（如 `provider.tsx` 中的 `switchLocale`）定义在 React 组件文件内时，单元测试要么无法导入它，要么必须复制逻辑（从而偏离真实实现）。应将此类函数提取到独立模块（如 `src/lib/locale.ts`），组件和测试都从该模块导入。这确保测试验证的是真实导出，而非过时副本。

5. **在 vitest 中 mock `collections/server` 以防止 MDX 加载**：从 `src/lib/source.ts` 导入的测试会通过 `collections/server` 别名传递加载 MDX 集合文件，vitest 无法将其解析为 JavaScript（错误："Failed to parse source for import analysis"）。在测试文件顶部添加 `vi.mock('collections/server', () => ({ docs: { toFumadocsSource: () => ({}) } }))` 来 stub 集合并阻止 MDX 文件加载。

### 数据库存储重组

- **统一 ORM 合并**：从自定义 SQLAlchemy 引擎迁移到 `nonebot_plugin_orm` 时，必须移除所有自定义引擎管理代码（`Base`、`_ENGINES`、`session_for()`、`storage_target()`、`close_engines()`）——不要遗留残余。所有数据访问必须通过 `orm_crud/` 包 + `get_session()` 进行。
- **测试重写模式**：直接操作数据库文件的测试（如检查 `.db` 文件是否存在、使用 `session_for()` 修改记录）必须重写为在仓储模块级别 mock `orm_crud` 函数，使用 `patch.object(repository, "create"/"upsert"/"get_one"/"update"/"list_items"/"delete", ...)`。参照 `tests/repositories/test_blocklist.py` 的模式。
- **Alembic 迁移脚本生成**：如果数据库文件已包含之前 `create_all` 创建的表，`nb orm revision` 可能生成空迁移（`upgrade()` 和 `downgrade()` 中均为 `pass`）。此时需根据模型定义手动编写迁移脚本，包含 `op.create_table()` / `op.create_index()` 操作，或先删除现有数据库文件（若未被其他进程锁定）。
- **单文件转包**：将单个 `.py` 文件（如 `json5_store.py`）转为包（`json5_store/`）时，`__init__.py` 必须通过 `from .submodule import Symbol` 显式重新导出所有公共 API 符号，并在 `__all__` 中列出。仅导入子模块是不够的——`from ..database.json5_store import RobustAsyncJSON5DB` 等测试导入在没有显式重导出时会失败。
- **迁移脚本 lint**：Alembic 生成的迁移脚本中 `collections.abc.Sequence` 仅用于类型注解。在已有 `from __future__ import annotations` 的情况下，将 `Sequence` 导入移至 `TYPE_CHECKING` 块以满足 ruff 的 `TC003` 规则。
- **文档同步**：删除或重命名源文件时，必须更新所有文档引用（AGENTS.md 文件树、架构图、`apps/docs/` MDX 文件）——不仅是代码。使用 `Grep` 在结构变更后查找过期引用。

### 平台/适配器/协议表重组

- **注册表数据播种**：当添加与 Python 数据结构对应的数据库注册表（如 `registry.py`）时，应实现 `seed_registry_tables()` 函数在启动时执行 upsert。使用 `conflict_fields` 实现幂等 upsert，确保重复运行不会产生重复记录。
- **协议维度追踪**：为现有表添加 `protocol_id` 列时，应设为可空（`Mapped[str | None]`），因为在记录时协议实现并不总能确定（例如在 event_preprocessor 阶段，处理器尚未运行）。
- **可空列的唯一约束**：SQLite 在唯一约束中将 NULL 视为不同值，因此 `(platform_id, adapter_id, protocol_id, ...)` 允许同一消息标识存在多条 `protocol_id=NULL` 的记录。这对消息记录可接受，但应记录在文档中。
- **新部署的迁移脚本重写**：当用户接受"仅新部署"策略时，直接重写初始迁移脚本，而非创建修改 schema 的新迁移。这能保持新部署的迁移历史整洁。

### 多数据库测试

- **SQLALCHEMY_DATABASE_URL 环境变量**：`nonebot_plugin_orm` 读取此环境变量来配置数据库后端。在测试中，`conftest.py` 将其传递给 `nonebot.init()`，使同一测试套件可在 SQLite、PostgreSQL 或 MySQL 上运行。
- **CI 矩阵策略**：使用 GitHub Actions 矩阵并设置 `fail-fast: false`，独立测试所有数据库后端。PostgreSQL 和 MySQL 使用 `services` 容器，通过条件镜像（`startsWith(matrix.db, 'postgresql') && 'postgres' || ''`）避免为 SQLite 启动不必要的服务。
- **测试前迁移**：在非 SQLite 数据库上运行测试前，务必执行 `uv run nb orm upgrade`，因为 `ALEMBIC_STARTUP_CHECK=false` 仅在启动时自动同步（不会在测试收集期间同步）。
- **测试依赖隔离**：数据库驱动（`psycopg[binary]`、`aiomysql`）位于 `test` 依赖组中，而非主依赖。这使生产安装保持轻量，同时在开发/CI 中支持多数据库测试。

### Mock 调用签名灵活性

- `assert_called_once_with(...)` 是精确匹配：只要实际调用的 kwargs 与预期不完全一致就会失败，包括某个 kwarg 的"存在 vs 不存在"差异。当业务代码改为条件性包含某个 kwarg（例如 `if image_path is not None: call_api(..., image=image_path)`）时，测试断言必须精确镜像该契约 —— 若生产代码路径完全不传 `image`，则绝不能断言 `image=None`。
- 仅做"存在性"检查时，使用 `assert "kwarg" in mock.call_args.kwargs` 替代 `assert_called_once_with`，或者先取出实际 kwargs 再用实际值重新断言。
- 新增同时混用 fixtures 和 `@pytest.mark.parametrize` 值的测试时，总形参数量务必 ≤ 5，以满足 `ruff` 的 `PLR0913` 规则。将相关的 parametrize 值合并到单个元组中（例如 `scenario: tuple[tuple[str, str], type]`），然后在函数体内解包使用。

### GitHub Actions SHA 固定最佳实践

- **优先使用 commit SHA 而非 annotated tag 对象 SHA**：固定 GitHub Actions 到版本标签时，`git/refs/tags/{tag}` API 返回的是 annotated tag 对象 SHA，而非 commit SHA。使用 `git/tags/{sha}` 将 annotated tag 解引用为 commit SHA。固定到 commit SHA 是文档推荐的最佳实践——确保 pin 指向实际被审查的代码，而非可能被重新创建的中间 Git 对象。
- **不要相信注释而要验证实际 SHA**：审查 action pin 版本时，`# pinned from actions/checkout@v6.0.3` 等注释可能已过时。始终通过 GitHub API 解析实际 SHA，验证其与声称的 release tag 匹配。
- **Dependabot 自动维护 action pin**：在 `dependabot.yml` 中配置 `package-ecosystem: "github-actions"`，当 action 发布新版本时自动开 PR。使用 `groups` + `update-types: ["minor", "patch"]` 批量处理低风险更新。

### 工作流文件名与名称约定

- **所有工作流文件名使用 emoji 前缀 + kebab-case**：`.github/workflows/` 下所有工作流文件遵循 `<emoji>-<kebab-case-name>.yml` 模式（如 `🧪-ci.yml`、`🩺-react-doctor.yml`）。这使工作流在文件列表和 GitHub Actions UI 中视觉可辨。
- **工作流 `name:` 字段使用英文**：`name:` 字段出现在 GitHub Actions UI 中，应使用英文以便通用可读。格式：`<emoji> <English Name>`（如 `name: 📚 Docs Deploy`）。
- **文件名 emoji 与 `name:` emoji 保持一致**：文件名中的 emoji 应与 `name:` 字段中的 emoji 匹配。
- **重命名前搜索文件名引用**：重命名工作流文件时，grep 整个仓库查找旧文件名（含 `.yml` 扩展名）以找到所有引用。检查 AGENTS.md、CLAUDE.md、AGENTS-zh.md、MDX 文档、skill 文件，以及工作流文件本身（`paths:` 触发器中的自引用）。

### .github 配置风格统一

- **所有 .github 配置文件使用英文注释**：`.github/` 下所有 YAML 配置文件统一使用英文注释。包括 `dependabot.yml`、`labeler.yml`、`auto_assign.yml` 等。
- **移除损坏的 `yaml-language-server: $schema=` 行**：如果配置文件有 `# yaml-language-server: $schema=` 注释但 URL 为空或无效，移除该行。仅在存在有效 JSON schema URL 时才添加 schema 注释。
- **Dependabot monorepo 配置**：pnpm/Turborepo monorepo 的 npm 生态使用 `directories`（复数，支持 glob 模式）而非 `directory`（单数）。使用 `groups` + `patterns` + `update-types` 将次版本/补丁更新合并为单个 PR，跨所有工作区目录。

### 异步转换：Fire-and-Forget 任务与异步 I/O

- **Fire-and-forget 后台任务必须保留强引用**：将调度的任务存储在模块级 `set` 中，并附加 done-callback 通过 `logger.exception` 记录异常并丢弃引用。若无强引用，Python 垃圾回收器可能在任务完成前将其取消。
- **可丢弃的同步操作会阻塞事件循环**：async 函数中的审计/遥测 DB 写入和图片缓存写入会阻塞事件循环。将 DB 写入转换为 `fire_and_forget`（作为后台任务运行），文件 I/O 转换为 `aiofiles`（`aiofiles.open` 用于读写）。
- **优先使用 `asyncio.gather(..., return_exceptions=True)` 而非顺序 `await` 循环**：用于独立的启动操作（注册表播种、超级用户授权）。记录每项失败而非中止整批——一项失败不应阻塞其余项。
- **异步文件 I/O 模式**：将同步文件 I/O 转换为异步时，使用 `aiofiles.os.makedirs`/`aiofiles.os.replace`/`aiofiles.os.unlink` 进行路径操作，`aiofiles.open` 进行读写，参照 `database/json5_store/_async_db.py` 的模式。
- **为导入时使用保留同步变体**：模块加载时没有事件循环可用，因此同步变体（如 `ensure_json5_dict_file_sync`）必须保留供模块级调用者使用；异步变体（如 `ensure_json5_dict_file_async`）供 `async def` 函数内的运行时调用者使用。

### 数据库模块拆分与配置简化

- **测试 patch 目标更新**：将单个模块（如 `orm_crud.py`）拆分为包（如 `orm_crud/`，含 `_base.py`、`_single.py`、`_bulk.py`）时，所有测试中的 `patch.object()` 目标必须从模块级更新到子模块级。例如 `patch("...orm_crud.select", ...)` 需改为 `patch("...orm_crud._single.select", ...)`。未更新 patch 目标会导致测试时 `AttributeError`，因为符号不再在包 `__init__` 上——它在子模块上。
- **`nonebot_plugin_orm` 包目录模型发现**：`nonebot_plugin_orm` 通过扫描模块路径发现 ORM 模型。将 `models.py` 转为 `models/` 包时，只要 `models/__init__.py` 显式导入所有模型类（如 `from .message import MessageRecord, AuditRecord`），模型发现仍然有效。若 `__init__.py` 中缺少显式导入，ORM 将不会注册表，迁移脚本将为空。
- **`ensure_json5_dict_file_async` 与 `write_json5_dict_file_async` 的区别**：`ensure_json5_dict_file_async` 仅在文件不存在时创建（幂等 ensure）。需要覆盖已有文件内容时（如 `bot_state.py` 持久化状态变更），应使用 `write_json5_dict_file_async`——它无条件写入文件。在需要 `write_*` 时误用 `ensure_*` 会静默保留过期数据。
- **移除向后兼容别名是破坏性变更**：将 `RuntimeConfig.lingchu_adapter` 简化为单一别名（移除 `LINGCHUAdapter` 和 `LINGCHU_ADAPTER`）能清理配置，但会破坏在 `.env` 或 `config.json5` 中引用旧别名名的用户。需在 changelog 和迁移指南中记录该移除；仅在 pre-1.0 或项目接受破坏性变更时执行（参见 Agent Preferences："pre-planning development stage"）。
