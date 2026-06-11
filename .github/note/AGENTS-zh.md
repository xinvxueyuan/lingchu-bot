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

## Project Context

> [English](../../AGENTS.md) | 中文

## Overview

Lingchu Bot 是一个基于 NoneBot2 的群管机器人。本 monorepo 包含 Python 后端插件（`nonebot-plugin-lingchu-bot`）和 Next.js 文档站（`apps/docs`）。

## Tech Stack

### Python Backend

- Python 3.13，由 `uv` 管理
- NoneBot2 + Milky 适配器
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

| What changed | Minimum checks before commit |
|---|---|
| Python source only | `ruff check` + `ruff format --check` + `pyright` + `ty check` + `pytest` |
| Docs site only | `pnpm --filter docs lint` + `pnpm --filter docs test` + `tsc --noEmit` |
| Markdown only | `markdownlint-cli2` |
| i18n strings | `task i18n` + `pytest` |
| Mixed / unsure | `task check && task test` |

## Git Hooks

- **pre-commit**: 条件触发检查 — Prek auto-fix（始终）→ Ruff lint/format（Python 变更时）→ Pyright/ty（Python 变更时）→ pytest（Python 变更时）→ Docs ESLint/type-check/Vitest（docs 变更时）→ Gitnexus analyze（始终，非阻断）
- **commit-msg**: gitmoji + Conventional Commits 格式校验 + 自动追加 Signed-off-by（含 trailer 块检测）
- **prepare-commit-msg**: Interactive gitmoji commit message via `pnpm exec gitmoji --hook`
- Set `$env:HUSKY='0'` to skip hooks when needed (e.g., automated commits)

## Agent Preferences

以下规则作为上下文注入每次对话，视为硬约束。

- **未经用户明确指示不得提交或推送** — 绝不自动提交、自动推送，或假设用户在完成任务后需要提交。等待用户明确要求。
- **持久偏好写入 AGENTS.md** — memory 文件和会话上下文都是临时的；AGENTS.md 是项目级规则和用户偏好的唯一真实来源。当用户说"记住这个"或表达偏好时，写到这里。
- **优先使用颗粒度检查而非完整 `task check`** — 使用上方的 Quick Reference 表，只运行与变更相关的检查。完整 `task check && task test` 用于提交前验证，而非每一步中间操作。
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

| 文件 | 加载时机 | 用途 |
|------|----------|------|
| `.trae/rules/git-commit-message.md` | 始终应用（Trae） | Gitmoji + Conventional Commits 格式规范。通过正则校验强制执行提交信息格式。 |

### 技能目录

技能**按需加载** — 仅当用户任务匹配触发条件时加载，不会注入每次对话。

#### `.agents/skills/`（Trae / Codex）

| 技能 | 触发条件 | 用途 |
|------|----------|------|
| `available-skills/` | 选择加载哪个技能时 | 所有可用技能的紧凑路由索引。列出项目本地、编码、前端、云、制品和技能创作技能。 |
| `gitnexus/gitnexus-cli/` | 运行 GitNexus CLI 命令（analyze、status、clean、wiki） | GitNexus 操作的 CLI 任务参考。 |
| `gitnexus/gitnexus-debugging/` | 调试 bug、追踪错误、"为什么 X 失败？" | 科学调试工作流：假设 → 插桩 → 复现 → 分析 → 修复 → 验证。 |
| `gitnexus/gitnexus-exploring/` | 理解架构、"X 是怎么工作的？" | 通过知识图谱探索代码：执行流、符号关系。 |
| `gitnexus/gitnexus-guide/` | 关于 GitNexus 工具/模式/工作流的问题 | 所有 GitNexus MCP 工具、资源和图谱模式的快速参考。 |
| `gitnexus/gitnexus-impact-analysis/` | "改 X 会破坏什么？"、编辑前安全检查 | 爆炸半径分析：深度 1/2/3 的上下游影响。 |
| `gitnexus/gitnexus-refactoring/` | 重命名、提取、拆分、移动代码 | 使用知识图谱 + 文本搜索的多文件协调重命名。 |
| `hf-cli/` | Hugging Face Hub 操作（模型、数据集、空间、存储桶、端点、作业） | `hf` 命令的完整 CLI 参考 — 认证、上传/下载、缓存、仓库、论文、集合、端点、作业。 |
| `prek/` | 设置或运行 `prek` Git 钩子 | `prek`（Rust 版 `pre-commit` 替代品）的配置、安装和工作流指南。 |
| `react-doctor/` | 完成 React 功能、修复 bug、`/doctor`、扫描/分诊 React 代码 | React 代码库健康扫描器（安全性、性能、正确性、架构）。输出 0–100 分。包含规则解释和配置参考。 |

#### `.claude/skills/`（Claude Code）

`.agents/skills/` 的子集 — 包含 `available-skills/`、所有 `gitnexus/*` 技能和 `prek/`。不包含 `hf-cli/` 或 `react-doctor/`（仅限 Trae/Codex）。

### 跨语言对应文件

| 文件 | 用途 |
|------|------|
| `.github/note/AGENTS-zh.md` | `AGENTS.md` 的中文翻译。必须与结构变更保持同步。 |

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

- **Static Analysis**: Ruff + Markdown + Turborepo lint
- **Tests & Type Check**: Pyright + ty + pytest + docs test
- **Auto Format**: On push to main/dev, auto-fix and commit
- **Docs Deploy**: Build and deploy to GitHub Pages

## Lessons Learned

> **时效性警示**：以下经验反映的是编写时代码库和依赖的状态。在依赖任何经验之前，请先验证其是否仍然成立——API 会变、包会新增导出、CI 配置也会演进。当经验过时时，应更新或删除，而非传播过时假设。

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
| --- | ---------- | ----- |
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

- **Pre-commit 应按变更文件类型条件触发检查**：用 `git diff --cached --name-only --diff-filter=ACMR` 收集暂存文件，通过 `has_pattern()` 检测文件后缀/路径，无 Python 变更时跳过 Ruff/Pyright/ty/pytest，无 Docs 变更时跳过 ESLint/type-check/Vitest，可节省 30-60 秒
- **Signed-off-by 追加需检测 trailer 块**：已有 trailer（如 `Closes #`、`BREAKING CHANGE:`、`Reviewed-by:`）时应追加到同一块（无空行分隔），无 trailer 时才用空行分隔
- **空行清理不能破坏消息结构**：`sed '/^$/N;/^\n$/d'` 会删除所有连续空行，破坏 subject-body-trailer 结构；应仅压缩 ≥3 连续空行为 2 个
- **重复签名检测需忽略尾部空白**：`grep -qF` 可能因行尾空白差异误判，应先 `sed 's/[[:space:]]*$//'` 去尾空白再 `grep -qxF` 精确整行匹配
- **空消息体不应追加 Signed-off-by**：空提交消息由格式校验拦截即可，追加签名到空文件无意义

### Switching i18n Default Locale

- **Fumadocs 语言包**：`@fumadocs/language` 导出其支持的语言包（如 `zh-cn`、`zh-tw`）；英语（`en-us`）默认内置，无需单独导入。切换默认语言为英语时，`layout.shared.tsx` 只需 `preset('zh', zhCN())` 加载中文语言包，无需导入英语包。在假设某个 locale 是否可用之前，务必检查 `@fumadocs/language` 当前的导出列表。
- **测试环境覆盖 locale 而非改断言**：将 Python `DEFAULT_LOCALE` 从 `zh_CN` 改为 `en_US` 后，所有断言中文翻译的测试会失败。正确做法是在 `tests/conftest.py` 的 `nonebot.init()` 中加 `"lingchu_locale": "zh_CN"` 覆盖回中文，避免逐个修改数百条测试断言，同时验证了 locale 配置覆盖机制。
- **Fumadocs i18n 文件命名约定**：默认语言的 MDX 文件不加后缀（`page.mdx`），非默认语言加 locale 后缀（`page.zh.mdx`）；`meta.json` 同理。切换默认语言时需批量重命名内容文件。

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

### 待回退变更

规则抑制和临时变通方案，在触发条件改变后应予回退。定期审查此节（如更新依赖或重构时）。

| 内容 | 位置 | 抑制原因 | 回退条件 |
|------|------|---------|---------|
| `deslop/unused-export: "off"` | `doctor.config.ts` | `mdx.tsx` 中的 `useMDXComponents` 是框架必需的重导出，但当前未被消费（`source.config.ts` 未配置 `providerImportSource`） | 当 `useMDXComponents` 被实际消费后移除此抑制（如添加 `providerImportSource` 到 `source.config.ts` 或在其他地方导入它） |
| 使用 CLI 而非 `millionco/react-doctor@v2` action | `.github/workflows/react-doctor.yml` | 上游 action 存在 bug：detached HEAD、ANSI 泄漏到 PR 评论（PR #80 待合并） | 上游修复发布后切换回 action（关注 PR #80） |

- **非组件导出破坏 Fast Refresh**：从组件文件（`mermaid.tsx`）导出工具函数（`getMermaidConfig`、`sanitizeMermaidSvg`、`renderMermaidSvg`）会触发 `react-doctor/only-export-components`。应将它们提取到独立的非组件模块（如 `mermaid-utils.ts`）并从那里导入。同时更新测试导入。
- **`/llms.txt` 是路由处理器而非静态文件**：从组件链接到 Next.js 路由处理器时，应使用 `<Link>`（而非普通 `<a>`）——它们是内部路由，可受益于客户端导航。
