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
| -------- | ----- |
| `gitnexus://repo/lingchu-bot/context` | Codebase overview, check index freshness |
| `gitnexus://repo/lingchu-bot/clusters` | All functional areas |
| `gitnexus://repo/lingchu-bot/processes` | All execution flows |
| `gitnexus://repo/lingchu-bot/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
| ---- | -------------------- |
| Understand architecture / "How does X work?" | `.agents/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.agents/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.agents/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.agents/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.agents/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.agents/skills/gitnexus/gitnexus-cli/SKILL.md` |

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
│   ├── core/           # Config, platform info
│   ├── database/       # JSON5 store package, ORM models (records/audit/blocklist + registry) & CRUD helpers
│   ├── handle/         # Platform/protocol/implementation command handlers
│   │   └── qq/{group,onebot/v11,milky/v1_2}/    # QQ group handlers
│   ├── i18n/           # Babel/gettext translations
│   ├── migrations/     # Alembic database migration scripts
│   ├── platforms/      # 适配器注册表和平台自有权限定义
│   │   └── qq/permissions.py # QQ 默认身份组与运行时身份解析
│   ├── permissions/    # UID 身份、平台账号、命令授权与 SUPERUSERS API
│   ├── repositories/   # Data access layer
│   │   ├── blocklist.py     # Blocklist repository
│   │   ├── message_store.py # Message store repository
│   │   ├── permissions.py   # Permission-system ORM repository
│   │   ├── registry.py      # Platform/adapter/protocol registry seeding
│   │   └── user_mapping.py  # UID/platform account binding compatibility entrypoint
│   ├── services/       # Business logic services
│   └── start/          # Startup & initialization
├── apps/docs/          # Fumadocs documentation site
│   ├── content/docs/   # MDX content (zh + en)
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
| Docs site only        | `pnpm --filter docs lint` + `pnpm --filter docs test` + `pnpm turbo run check-types --filter=docs` + `pnpm --filter docs lint:links` |
| Markdown only         | `markdownlint-cli2`                                                               |
| i18n strings          | `task i18n` + `pytest`                                                            |
| Mixed / unsure        | `task check && task test`                                                          |

## Git Hooks

- **pre-commit**: 条件触发检查 — Prek auto-fix（始终）→ Ruff lint/format（Python 变更时）→ Pyright/ty（Python 变更时）→ pytest（Python 变更时）→ Docs ESLint/type-check/Vitest（docs 变更时）→ React Doctor（docs 变更时，优先全局/本地安装，回退到 `pnpm dlx` 缓存，最终兜底 `npx -y`）→ Gitnexus analyze（始终，非阻断，优先 `node_modules/.bin/gitnexus` 直接调用，零下载）
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
| `context7-mcp/`                | 查找库/框架文档、API 参考、代码示例            | Context7 MCP 集成，用于获取最新文档。                                                                     |
| `gitnexus/gitnexus-cli/`       | 运行 GitNexus CLI 命令（analyze、status、clean、wiki） | GitNexus 操作的 CLI 任务参考。                                                                           |
| `gitnexus/gitnexus-debugging/` | 调试 bug、追踪错误、"为什么 X 失败？"         | 科学调试工作流：假设 → 插桩 → 复现 → 分析 → 修复 → 验证。                                               |
| `gitnexus/gitnexus-exploring/` | 理解架构、"X 是怎么工作的？"                   | 通过知识图谱探索代码：执行流、符号关系。                                                                   |
| `gitnexus/gitnexus-guide/`            | 关于 GitNexus 工具/模式/工作流的问题           | 所有 GitNexus MCP 工具、资源和图谱模式的快速参考。                                                       |
| `gitnexus/gitnexus-impact-analysis/`  | "改 X 会破坏什么？"、编辑前安全检查           | 爆炸半径分析：深度 1/2/3 的上下游影响。                                                                   |
| `gitnexus/gitnexus-refactoring/`      | 重命名、提取、拆分、移动代码                   | 使用知识图谱 + 文本搜索的多文件协调重命名。                                                               |
| `gitnexus/gitnexus-pr-review/`        | 审查 Pull Request、评估合并风险                | 基于知识图谱的变更分析 PR 审查。                                                                         |
| `prek/`                               | 设置或运行 `prek` Git 钩子                     | `prek`（Rust 版 `pre-commit` 替代品）的配置、安装和工作流指南。                                           |

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

- **🧪 CI**: Static analysis (Ruff + Markdown + Turborepo lint), tests & type check (Pyright + ty + pytest + docs test), auto-format on push to main/dev. Test jobs install `--extra deprecated-adapters` so test files importing optional dependencies (Milky adapter) can resolve.
- **👷 CI-builds**: Build verification on Python/package changes
- **📚 Docs Deploy**: Build and deploy to GitHub Pages on push to main/dev
- **🩺 React Doctor**: React codebase health check on PRs (uses CLI, not the action — see Lessons Learned)
- **🧹 Clear Workflow**: Stale workflow cleanup
- **🏷️ Issues Top**: Issue triage automation

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

### Git Hooks Optimization

- **Pre-commit 应按变更文件类型条件触发检查**：用 `git diff --cached --name-only --diff-filter=ACMR` 收集暂存文件，通过 `has_pattern()` 检测文件后缀/路径，无 Python 变更时跳过 Ruff/Pyright/ty/pytest，无 Docs 变更时跳过 ESLint/type-check/Vitest，可节省 30-60 秒
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

- **pre-commit.ci failures** → use the **prek** skill (`.agents/skills/prek/SKILL.md`) to reproduce and fix pre-commit hook failures locally, instead of manually running each hook
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

### 待回退变更

规则抑制和临时变通方案，在触发条件改变后应予回退。定期审查此节（如更新依赖或重构时）。

| 内容                                                    | 位置                                   | 抑制原因                                                                                                                             | 回退条件                                                                                                     |
| ------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| Pyright/ty 排除 `src/.../adapters/milky` | `pyproject.toml` `[tool.pyright]` 和 `[tool.ty.src]` | Milky 适配器移至可选依赖；静态分析环境未安装，导致 `reportMissingImports` | 当 Milky 适配器完全删除或静态分析环境安装 `--extra deprecated-adapters` 时移除排除 |
| `deslop/unused-export: "off"`                           | `doctor.config.ts`                     | `mdx.tsx` 中的 `useMDXComponents` 是框架必需的重导出，但当前未被消费（`source.config.ts` 未配置 `providerImportSource`）               | 当 `useMDXComponents` 被实际消费后移除此抑制（如添加 `providerImportSource` 到 `source.config.ts` 或在其他地方导入它） |
| 使用 CLI 而非 `millionco/react-doctor@v2` action        | `.github/workflows/🩺-react-doctor.yml`   | 上游 action 存在 bug：detached HEAD、ANSI 泄漏到 PR 评论（PR #80 待合并）                                                             | 上游修复发布后切换回 action（关注 PR #80）                                                                     |

- **非组件导出破坏 Fast Refresh**：从组件文件（`mermaid.tsx`）导出工具函数（`getMermaidConfig`、`sanitizeMermaidSvg`、`renderMermaidSvg`）会触发 `react-doctor/only-export-components`。应将它们提取到独立的非组件模块（如 `mermaid-utils.ts`）并从那里导入。同时更新测试导入。
- **`/llms.txt` 是路由处理器而非静态文件**：从组件链接到 Next.js 路由处理器时，应使用 `<Link>`（而非普通 `<a>`）——它们是内部路由，可受益于客户端导航。

### Docs CI 和单元测试覆盖

为文档站点（`apps/docs/`）添加 CI 检查或单元测试时，出现过以下陷阱：

1. **MDX 表格中的 `|` 破坏内联代码跨度**：在 markdown 表格单元格内，`<群号|群名称>` 会被解析为三个表格列（`<群号`、`群名称>`），从而将 `<...>` 暴露为 JSX 并导致 "Unexpected end of file in name" 构建错误。应将 `|` 替换为 `或` / `_or_`（与现有风格一致，如 `<用户ID或@提及>`）。此规则同时适用于 `.mdx` 和 `.zh.mdx` 文件。

2. **`fumadocs-mdx` node loader 无法处理图片资源**：`lint:links` 脚本使用 `fumadocs-mdx/node` 的 `register()` 加载 MDX 文件以进行链接验证。当 MDX 文件导入 `.png`/`.jpg`/`.svg` 时，loader 的 `load` 钩子会调用 `nextLoad`，到达 Node 默认加载器并抛出 `ERR_UNKNOWN_FILE_EXTENSION`。解决方法是通过 `node:module` 的 `module.registerHooks()`（Node.js 23+）注册一个 `load` 钩子，对图片文件扩展名返回 `export default undefined;`。在 `scripts/lint.mts` 顶部、导入 `fumadocs-mdx/node` 之前添加此钩子。

3. **`next-validate-link` 从根索引页的 URL 解析**：根索引页（如 `platforms/index.mdx`）的 URL 没有尾部斜杠（`/docs/platforms`），因此相对链接如 `./qq` 会解析为 `/docs/qq` 而非 `/docs/platforms/qq`。从根索引页链接时应使用绝对 URL（如 `/docs/platforms/qq/overview`）。目录链接（如 `./onebot-v11`）必须包含具体页面后缀（`./onebot-v11/overview`）——纯目录链接无法通过验证。

4. **提取共享函数以提高可测试性**：当函数（如 `provider.tsx` 中的 `switchLocale`）定义在 React 组件文件内时，单元测试要么无法导入它，要么必须复制逻辑（从而偏离真实实现）。应将此类函数提取到独立模块（如 `src/lib/locale.ts`），组件和测试都从该模块导入。这确保测试验证的是真实导出，而非过时副本。

5. **在 vitest 中 mock `collections/server` 以防止 MDX 加载**：从 `src/lib/source.ts` 导入的测试会通过 `collections/server` 别名传递加载 MDX 集合文件，vitest 无法将其解析为 JavaScript（错误："Failed to parse source for import analysis"）。在测试文件顶部添加 `vi.mock('collections/server', () => ({ docs: { toFumadocsSource: () => ({}) } }))` 来 stub 集合并阻止 MDX 文件加载。

### 数据库存储重组

- **统一 ORM 合并**：从自定义 SQLAlchemy 引擎迁移到 `nonebot_plugin_orm` 时，必须移除所有自定义引擎管理代码（`Base`、`_ENGINES`、`session_for()`、`storage_target()`、`close_engines()`）——不要遗留残余。所有数据访问必须通过 `orm_crud.py` + `get_session()` 进行。
- **测试重写模式**：直接操作数据库文件的测试（如检查 `.db` 文件是否存在、使用 `session_for()` 修改记录）必须重写为在仓储模块级别 mock `orm_crud` 函数，使用 `patch.object(repository, "create"/"upsert"/"get_one"/"update"/"list_items"/"delete", ...)`。参照 `tests/database/test_blocklist.py` 的模式。
- **Alembic 迁移脚本生成**：如果数据库文件已包含之前 `create_all` 创建的表，`nb orm revision` 可能生成空迁移（`upgrade()` 和 `downgrade()` 中均为 `pass`）。此时需根据模型定义手动编写迁移脚本，包含 `op.create_table()` / `op.create_index()` 操作，或先删除现有数据库文件（若未被其他进程锁定）。
- **单文件转包**：将单个 `.py` 文件（如 `json5_store.py`）转为包（`json5_store/`）时，`__init__.py` 必须通过 `from .submodule import Symbol` 显式重新导出所有公共 API 符号，并在 `__all__` 中列出。仅导入子模块是不够的——`from ..database.json5_store import RobustAsyncJSON5DB` 等测试导入在没有显式重导出时会失败。
- **迁移脚本 lint**：Alembic 生成的迁移脚本中 `collections.abc.Sequence` 仅用于类型注解。在已有 `from __future__ import annotations` 的情况下，将 `Sequence` 导入移至 `TYPE_CHECKING` 块以满足 ruff 的 `TC003` 规则。
- **文档同步**：删除或重命名源文件时，必须更新所有文档引用（AGENTS.md 文件树、架构图、`apps/docs/` MDX 文件）——不仅是代码。使用 `Grep` 在结构变更后查找过期引用。

### 平台/适配器/协议表重组

- **注册表数据播种**：当添加与 Python 数据结构对应的数据库注册表（如 `registry.py`）时，应实现 `seed_registry_tables()` 函数在启动时执行 upsert。使用 `conflict_fields` 实现幂等 upsert，确保重复运行不会产生重复记录。
- **协议维度追踪**：为现有表添加 `protocol_id` 列时，应设为可空（`Mapped[str | None]`），因为在记录时协议实现并不总能确定（例如在 event_preprocessor 阶段，处理器尚未运行）。
- **可空列的唯一约束**：SQLite 在唯一约束中将 NULL 视为不同值，因此 `(platform_id, adapter_id, protocol_id, ...)` 允许同一消息标识存在多条 `protocol_id=NULL` 的记录。这对消息记录可接受，但应记录在文档中。
- **新部署的迁移脚本重写**：当用户接受"仅新部署"策略时，直接重写初始迁移脚本，而非创建修改 schema 的新迁移。这能保持新部署的迁移历史整洁。

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
