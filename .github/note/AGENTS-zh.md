## Lingchu Bot Agent Guide

> [English](../../AGENTS.md) | 中文

这是 `AGENTS.md` 的中文镜像。保持结构同步，内容以 `AGENTS.md` 为准；不要把本文件维护成独立规则集。

## CREATE 框架

本指南按 CREATE 组织，让 agent 快速取用约束：

| 字母 | 章节           | 目的                       |
| -- | ------------ | ------------------------ |
| C  | Context      | 项目是什么、各类事实来源在哪里          |
| R  | Role         | agent 在本仓库中的工作方式         |
| E  | Expectations | 不可违反的约束和质量门禁             |
| A  | Actions      | 标准开发流程和联动面               |
| T  | Tools        | 命令、skills、hooks、验证路径 |
| E  | Evidence     | 经验教训、清单和收尾证据             |

编辑本文件时遵循 DRY 和 SMAR/TL：

- **Specific**：规则必须点名精确文件、命令或 API。
- **Measurable**：每个流程都有具体验证命令或证据要求。
- **Actionable**：避免空泛建议，写清下一步可执行操作。
- **Relevant**：只保留仓库级规则或高价值失败防线。
- **Time-bounded / Timeliness-aware**：依赖、API、CI 经验可能过期，使用前重新验证。
- **Linked**：优先链接 canonical 文件，不复制表格、目录树或生成清单。
- **Tool-owned**：生成段落交给对应 CLI 维护；人工 guidance 放在生成 marker 外。保留 `<!-- gitnexus:start -->` 这类 HTML-style locator tags 的原样文本。

## C — Context

Lingchu Bot 是基于 NoneBot2 的群管理机器人。Monorepo 包含：

- Python 后端插件：`src/plugins/nonebot_plugin_lingchu_bot/`
- Astro Starlight 文档站：`apps/docs/`
- 项目本地 skills（单一来源）：`.agents/skills/`
  - `.claude/skills/` 和 `.trae/skills/` 是指向 `.agents/skills/` 的**整目录软链**，让 Codex、Trae、Claude Code 三家代理读同一套 skill；在 `.agents/skills/` 增删 skill 三个代理同时生效。
- 中文 agent 指南镜像：`.github/note/AGENTS-zh.md`
- Claude Code 指南镜像：`CLAUDE.md`

构建或包分发所需内容必须位于 `src/plugins/nonebot_plugin_lingchu_bot/` 下。仓库根目录的 `config/`、`data/` 等运行时/配置文件是本地开发产物，可丢弃。

不要在本文件维护手写完整目录树。需要当前结构时使用 `rg --files`、GitNexus，或查看 `apps/docs/src/content/docs/developer-guide/`。

## Tech Stack

Python 后端：

- Python 3.13，由 `uv` 管理
- NoneBot2 + OneBot V11 adapter；Milky、QQ、OneBot V12 已停维并移除
- `nonebot-plugin-alconna` 负责命令解析
- `nonebot-plugin-orm` + `aiosqlite` 负责异步数据库
- `nonebot-plugin-localstore` 负责 mutable data/config/cache/resource/schema 路径
- Ruff、Pyright、ty、pytest

文档站：

- Astro、Starlight static export、React 19、Tailwind CSS 4、TypeScript 6
- `shadcn/ui`（组件源码位于 `apps/docs/src/components/ui/`，通过 `@theme inline` 桥接与 Starlight 共享 Tailwind v4 主题）
- `p5.js`（instance mode，封装于 `src/components/p5/`，通过客户端 demo 组件支持 MDX 内嵌与首页 hero 动效）
- Vitest、Testing Library、ESLint、Playwright
- i18n、Starlight/Pagefind search、sitemap、Mermaid、Twoslash
- Starlight content collections 负责 docs routing、sidebar 和本地化静态输出
- Turborepo workspace，包管理器为 `pnpm`

## R — Role

Agent 是早期项目的实现伙伴。严重 breaking change 在能简化架构或解锁产品方向时可以接受，但必须显式、可追踪、已文档化。

操作规则：

- 设计前先检查当前仓库；旧记忆和旧生成文档不够。
- 优先复用既有项目模式，不轻易新增抽象。
- 需求缺失时尽早提问；用户明确要求实现后，端到端完成。
- 未经用户明确要求，不 commit、不 push、不开 PR。
- 提交前运行 `git status` 并检查 `git diff` / staged diff，绝不盲提。
- 自动化中显式调用 PowerShell 时，使用 `pwsh.exe -NoProfile`。
- 按下文保持 AGENTS、Claude、中文镜像同步。
- SubAgent 任务完成后，编排者 MUST 运行 `git status --short` 并删除任何 SubAgent 创建的临时文件（如 `_tmp_*`、`_writetest*`、临时脚本、探针文件）。SubAgent 不会自行清理；编排者负责工作区卫生边界。

## E — Expectations

### Canonical Context Files

| 文件                                  | 何时加载                     | 目的                                                            |
| ----------------------------------- | ------------------------ | ------------------------------------------------------------- |
| `AGENTS.md`                         | Codex / Trae 共享上下文       | canonical 项目规则、命令、约束和经验                                       |
| `CLAUDE.md`                         | Claude Code 上下文          | 与 `AGENTS.md` 同结构，唯一允许额外章节是 Claude Code Behavioral Guidelines |
| `.github/note/AGENTS-zh.md`         | 中文镜像                     | `AGENTS.md` 的中文 counterpart，结构同步                              |
| `.trae/rules/git-commit-message.md` | Trae always-applied rule | Gitmoji + Conventional Commits 校验                             |

当 `AGENTS.md`、`CLAUDE.md`、`.github/note/AGENTS-zh.md` 不一致时，以 `AGENTS.md` 为准，再把相同结构变更复制/同步到另外两个文件。

该同步规则从 `<!-- gitnexus:end -->` 之后开始。GitNexus marker 块由工具拥有，且各文件可能不同；不要手动统一。HTML comment markers 是 CLI contract，不是普通 prose。

### Hard Constraints

- **Localstore 路径所有权**：所有 mutable data、config、cache、resource、schema 文件必须通过 `nonebot_plugin_localstore` helper 解析，例如 `get_plugin_data_dir()`、`get_plugin_config_dir()`、`get_plugin_cache_dir()`、`get_plugin_data_file()`、`get_plugin_config_file()`、`get_plugin_cache_file()`。
- **禁止硬编码 mutable 路径**：禁止对 mutable runtime 文件使用 `Path("...")`。
- **配置仅允许显式写入**：启动过程不得创建、迁移或重新生成配置文件。配置写入必须使用 localstore 管理的路径或明确指定的部署路径。
- **Prek 是 hook 唯一来源**：`prek.toml` 是唯一 pre-commit hook 配置（显式声明 ruff/ty 钩子，与 husky 解耦，无重复执行）。不要重新引入 `.pre-commit-config.yaml`。
- **版本同步**：使用 `Taskfile.yml` 的 `ci:version:write-config` 同步写入 `src/plugins/nonebot_plugin_lingchu_bot/core/config.py` 和根 `package.json`。
- **发布分支**：正式版本使用 `releases/<version>` 分支，发布前必须保持 `pyproject.toml`、`package.json` 和 `core/config.py` 中的版本一致。
- **发布说明**：每个正式版本都要更新 `CHANGELOG.md` 和发布策略记录。
- **发布凭据**：PyPI 使用 Trusted Publishing / OIDC；GHCR 使用带 `packages: write` 权限的 `GITHUB_TOKEN`；不要新增长期有效的包仓库 token。
- **Skills exclusion sync**：修改 `pyproject.toml` 中 skills exclusion pattern 时，同步 `prek.toml` 对应注释/模式。
- **REUSE compliance**：所有文件 MUST 通过 `REUSE.toml` 声明 SPDX 许可；提交前 `reuse lint` MUST 通过。新文件 MUST 被 `REUSE.toml` glob 覆盖，或带有内联 `SPDX-License-Identifier` 头。
- **Docker build context**：`docker build` 前，`.dockerignore` MUST 排除 `.git`、`.venv`、`node_modules`、`.env*`（保留 `.env.example`/`.env.prod.example`）、`tests/`、`.github/`、`.trae/`、`.gitnexus/`、`.turbo/` 及缓存目录。
- **CODEOWNERS**：`.github/CODEOWNERS` 将 `src/`、`apps/docs/`、`.github/`、`Dockerfile`、`docker-compose.yml`、`Taskfile.yml`、`pyproject.toml`、`package.json`、`REUSE.toml`、`LICENSE-*` 路由给 `@xinvxueyuan` 用于 auto-review。
- **Workflow 文件名规范**：`.github/workflows/*.yml` 文件名使用纯 kebab-case，不带前导 emoji。emoji 仅保留在 `name:` 字段中，使 Actions UI 仍可按视觉分类。CI 不会因 emoji 失败，但 Cygwin 路径、zip 归档、Windows shell 自动补全对 emoji 处理脆弱，因此新工作流 MUST 遵循纯名约定，已有文件被触及 MUST 通过 `git mv` 重命名。

### 代码风格

项目在 Python 和前端工作空间统一执行以下代码风格：

- **`.editorconfig`**：根目录编辑器基线。Python 使用 4 空格缩进；JS/TS/CSS/MD/YAML/TOML/JSON 使用 2 空格。所有文本文件使用 LF 换行、UTF-8 编码、末尾换行、去除行尾空格。
- **Python 格式化**：`ruff format`（行宽 88，LF，双引号）。不使用 Black 或 isort — Ruff 替代两者。
- **Python 文档字符串**：Ruff `D`（pydocstyle）规则族，`convention = "google"`。缺失文档字符串规则（`D100`–`D103`）全局忽略（现有代码库规模太大无法一次性补全）；D 规则仍对已有文档字符串执行风格检查。测试文件有独立的 D 忽略。
- **Python 静态检查**：Ruff 规则族包括 F, W, E, I, C90, N, PL, UP, YTT, ANN, ASYNC, BLE, FBT, B, A, COM, C4, D, DTZ, T10, ICN, PIE, T20, PYI, Q, RSE, RET, SIM, SLOT, TID, TC, ARG, PTH, FAST, PERF, PGH, FURB, TRY, RUF。
- **Python 类型检查**：Pyright `standard` 模式 + ty（Astral，快速反馈）。两者均在 CI 中运行。
- **前端格式化**：Prettier（`.prettierrc.json`）用于 JS/TS/TSX/CSS/JSON。Markdown 文件被排除 — `markdownlint-cli2` 负责 `.md`，`eslint-plugin-mdx` 负责 `.mdx`（双 linter 策略）。
- **前端检查**：ESLint 10 flat config。`apps/docs` 使用 Astro/Starlight-aware TypeScript 和 MDX linting。`eslint-config-prettier` 作为最后一项追加，禁用与 Prettier 冲突的格式化规则。
- **TypeScript**：TS 6，`strict: true`，`target: ES2025`，`module: ESNext`，`moduleResolution: Bundler`（在 `packages/typescript-config/base.json` 中）。
- **工具版本**：ruff>=0.15.22, pyright>=1.1.411, ty>=0.0.61, prek>=0.4.10, ESLint 10.x, TypeScript 6.x。
- **格式化工作流**：`task format` 运行 Ruff format → Prettier → markdownlint --fix。`task fix` 运行 Ruff check --fix → Ruff format → Prettier → ty check --fix → markdownlint --fix。
- **已移除的无用脚手架**：`packages/eslint-config/` 和 `packages/ui/`（Turborepo 模板残留，未被任何 app 引用）。`apps/docs` 有自己的 `eslint.config.mjs`。
- **忽略注释治理**：`src/` 中禁止内联 `# noqa`、`# type: ignore`、`# pyright: ignore`、`# ty: ignore` 和文件级 `# ruff: noqa`。所有合法抑制 MUST 集中在 `pyproject.toml` `[tool.ruff.lint.per-file-ignores]` 中，每个条目附带 `# comment` 理由。模块级 `# pyright: reportMissingImports=false` 仅用于可选依赖导入。前端 `@ts-ignore` 通过 `@typescript-eslint/ban-ts-comment` 禁用；改用 `@ts-expect-error` 并附带描述。Pre-commit Phase 2.5 对 staged `src/*.py` 中新增的 `# noqa` 发出告警；CI `ignore-comment-audit` job 在 PR 中对回归发评论。
- **激进工具链策略（2026 面向未来版）**：项目承诺面向未来的工具链基线；以下规则不可违反，除非显式回滚。
  - Ruff：lint 与 format 启用 `preview = true` + `explicit-preview-rules = true`，主动采用 2026 style guide；`future-annotations = true`、显式 `isort`、`task-tags`。
  - Pyright：`typeCheckingMode = "strict"`；NoneBot 框架约束的 handler 签名通过 `per-file-ignores` 等价配置集中治理，禁止内联 `# pyright: ignore`。
  - ty：通过 `[tool.ty]` + `[[tool.ty.overrides]]` 启用 strict 模式；Taskfile 不得用 `|| true` 掩盖失败。
  - TypeScript：`packages/typescript-config/base.json` 启用 strictest 四件套（`exactOptionalPropertyTypes`、`noImplicitOverride`、`noPropertyAccessFromIndexSignature`、`noUnusedLocals`）+ `verbatimModuleSyntax`。
  - ESLint：启用 type-aware 规则集（`no-floating-promises`、`no-misused-promises` 等）并配置 `projectService`；`eslint-plugin-import-x` + `eslint-plugin-unicorn` 强制 `import/order`、`import/no-cycle`、`unicorn/filename-case`。
  - Prettier：`printWidth = 100`，`singleAttributePerLine = true`。
  - pytest：`--strict-markers --strict-config`；`[tool.coverage.run]` 启用 `branch = true`。
  - Python 基线：3.13（降级守卫），`requires-python = ">=3.13, <4.0"`，`target-version = "py313"`，不升级至 3.14。
  - Docker Compose：移除 `version` 字段，新增 `name: lingchu-bot`，使用 `restart: unless-stopped`。
  - CI：所有 workflow 顶层 `permissions: contents: read`，job 级按需提升并附注释说明。

### Architecture Decisions

- Docs i18n 使用 Starlight root locale 作为英文；默认英文 URL 不带 `/en/`。
- Docs build output 是 `apps/docs/dist`；CI、Pages upload 和 smoke tests 必须消费该目录。
- Client components 使用 `useSyncExternalStore` 处理 mount detection，不使用 `useState` + `useEffect`。
- GitNexus 是代码智能和影响分析层；其生成上下文块由 CLI 拥有。
- 平台默认身份组位于 `platforms/qq/permissions.py` 等平台模块；core permissions 消费 seeds 和 runtime resolvers，但不硬编码平台角色树。

## A — Actions

### Standard Development Flow

1. 检查 `git status --short`，记录已有用户改动。
2. 只加载相关 skills 或 references；不要预加载所有指南。
3. 编辑 symbol 前使用 GitNexus 做代码理解和影响分析。
4. 手动检查附近源码和测试；工具可能漏掉业务联动面。
5. 做最小但完整的变更。
6. 涉及用户可见行为时，同步 tests、i18n、docs、menus、triggers、runtime config、schemas。
7. 按 quick reference 运行针对性检查。
8. 用户要求提交时，先复核 diff，运行 `detect_changes()`，再按约定提交。

### Cross-Cutting Change Checklist

修改业务逻辑，尤其 adapter 层代码时，完成前检查所有相关面：

| 面向                  | 常见文件                                                                     |
| ------------------- | ------------------------------------------------------------------------ |
| Source              | `src/plugins/nonebot_plugin_lingchu_bot/`                                |
| Tests               | `tests/`                                                                 |
| i18n                | `src/plugins/nonebot_plugin_lingchu_bot/i18n/`；用户可见字符串变化时运行 `task i18n`  |
| Docs                | `apps/docs/src/content/docs/`                                                |
| Menu                | `src/plugins/nonebot_plugin_lingchu_bot/handle/menu.py`                  |
| Runtime config      | NoneBot 部署环境、localstore `runtime-overrides.toml`、`bot_state.toml`、`menu.toml` 与 `_lingchu_bot_contracts/` |
| Handle config files | `handle_config_defaults/<command>.py`、localstore config\_dir 中的 `<command_key>.toml` |
| Triggers            | `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/commands/triggers.py`  |
| Handler session injection | 新 matcher handler 添加 `session: async_scoped_session`（仅类型注解，不要写 `= Depends(...)`）；调用 repository/permission 时把 `session` 作为首参 |
| Agent context       | `AGENTS.md`、`CLAUDE.md`、`.github/note/AGENTS-zh.md`                      |

涉及 handle、QQ command、adapter handler、matcher、`command_key`、menu、trigger、permission、config 耦合的工作，直接检查 `src/plugins/nonebot_plugin_lingchu_bot/handle/` 及相邻 tests —— 原 `engineering-workflow` skill 引用已移除。

### Command And Menu Rules

- 群命令触发词是 locale-exclusive。不要为同一个 matcher 同时注册中文和英文触发词。使用 `get_configured_locale()`，并排除非当前语言 aliases。
- 菜单 fail closed。隐藏当前身份或实现不能执行的命令。
- `MENU_FEATURES.command_key` 是 permission checks、menu filtering、handler decorators 的共享命令标识。
- 添加命令时，同步 triggers、`MENU_FEATURES`、tests、QQ command-reference docs。
- 远程管理命令仅 OneBot V11 支持，实现在 `handle/qq/adapters/onebot11/default/remote.py`。

### State And Config Rules

- `core/bot_state.py` 通过 localstore 持久化 `bot_state.toml`。
- `is_handle_active(platform_id)` 按 global AND platform 解析。
- `is_silent_mode(platform_id)` 按 global OR platform 解析。
- `selected_adapter_handle()` 支持 `bypass_gate` 和 `bypass_silent`。
- “闭嘴”/“说话”绕过 silent mode，但不绕过 shutdown gate。
- “开机”/“关机”同时绕过 gate 和 silent mode。
- 启动过程不得创建、迁移或重新生成配置与 schema；缺失的可变配置使用 typed 内存默认值。部署设置属于 NoneBot 配置，`MutableRuntimeSettings` 属于 localstore `runtime-overrides.toml`。

### Repository API Style

- 对包含耦合字段的 write/audit API，使用 frozen dataclass request object。
- Command audit payload 使用 `CommandAudit`，再调用 `record_audit_fire_and_forget()` 或 `record_command_audit()`。
- 不新增 platform、adapter、bot、group、target、reason、duration 等长参数列表；创建 request object。
- `fire_and_forget(coro, *, name="...")` 只用于调用方不需要结果的可丢弃后台工作。
- **Session 首参约定**：所有 `database/orm_crud/*.py` 和 `repositories/*.py` 函数 MUST 把 `session: AsyncSession | async_scoped_session` 作为第一个位置参数。函数内 MUST NOT 自己 `get_session()`（仅 `services/scheduler.py` 和 `services/message_store.py` 的后台任务保留 `async with get_session() as s:`，因为它们自管生命周期）。函数内 MUST NOT `commit`/`rollback` —— 事务边界由调用方控制。**例外 —— 自管 session 必须自 commit**：自己开 `get_session()` 的代码路径（后台任务、fire-and-forget 审计写入）自己就是事务边界，写入后 MUST `await session.commit()`。`async with get_session() as s:` 退出只关闭 session —— 未提交的 flush 事务会被**静默回滚**（2026-08-14 实例：消息存储因此数月零写入，撤回恒 0/0/0）。
- **Fire-and-forget 审计/权限 helper**：当 handler 侧 helper（如 `_default_permission_resolver`、`_default_audit_writer`）包装的 repository 函数已要求 `session` 时，helper MUST 自己开 scoped session（`async with get_session() as session:`）以满足调用方仍在使用的 Protocol/Callable 类型。不要把 session 参数推到 Protocol 签名上，把边界缝留在 helper 内部。

## T — Tools

### Skills And MCPs

| 需求                                        | 路由                                                                     |
| ----------------------------------------- | ---------------------------------------------------------------------- |
| 计划/领域：对照代码库 grill 计划，构建 CONTEXT.md + ADRs | `grill-with-docs` skill                                                |
| 计划/领域：磨砺领域语言和术语                           | `domain-modeling` skill                                                |
| 计划/领域：不带文档产物的轻量压力测试                       | `grilling` skill                                          |
| 将计划/对话转为 spec                             | `to-spec` skill                                                        |
| 将 spec 拆成带阻塞边的 tracer-bullet tickets       | `to-tickets` skill                                                     |
| 测试驱动开发（红-绿-重构，垂直切片）                      | `tdd` skill                                                            |
| Lazy / 最小方案强制                              | `ponytail` skill                                                       |
| 当前 library、framework、SDK、API、CLI、cloud 文档 | `context7-cli` / `find-docs` skills                                    |
| OpenAI 产品/API 文档                          | `openai-docs`，只用官方文档                                                   |
| 架构、影响、重构、review                          | GitNexus（见本文件顶部）                                                       |
| Hooks、Prek、Husky                          | `prek` skill                                                           |
| React 代码 triage / cleanup                | `react-doctor` skill                                                   |
| Web 抓取、爬取、搜索                              | `firecrawl-*` skills                                                   |
| OneBot V11 / NapCat API 签名                | 写 adapter 调用前检查当前 adapter 与 NapCat 文档                            |
| GitHub PR、issue、CI、发布                     | GitHub skills                                                          |

### Development Workflow Chain（开发调度链）

Skills 组成从计划到提交的调度链。在每个阶段开始时加载对应 skill；不要预加载整条链。

```text
grill-with-docs          ← 阶段 1：PLAN
  ↓                        grill 计划，构建 CONTEXT.md + ADRs
domain-modeling          ← 阶段 1b：磨砺领域语言（可选）
  ↓
to-spec                  ← 阶段 2：SPEC
  ↓                        将计划综合成 spec
to-tickets               ← 阶段 3：TICKETS
  ↓                        将 spec 拆成垂直切片 tickets
tdd                      ← 阶段 4：IMPLEMENT
  ↓                        红-绿-重构，一次一个切片
  ├─ ponytail             ← 实现中强制最小方案
  ├─ context7-cli         ← 需要时查库文档
  ├─ gitnexus             ← 编辑 symbol 前运行 impact()
  ├─ firecrawl-*          ← 需要时做 Web 调研/抓取
  └─ react-doctor         ← 前端变更的 React triage
prek                     ← 阶段 5：COMMIT
                           Git hooks：lint + format + type + test
```

轻量替代：`grilling` 在只需要压力测试、不需要文档产物时替代 `grill-with-docs` + `domain-modeling`。

### Development Commands

Python:

```bash
uv run -m ruff check . --output-format=github
uv run -m ruff check --fix .
uv run -m ruff format --check .
uv run -m ruff format .
uv run -m pyright
uv run -m ty check --output-format github
uv run -m pytest
```

Docs:

```bash
pnpm --filter docs lint
pnpm --filter docs test
pnpm --filter docs check-types
pnpm --filter docs build
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

| 变更              | 提交前最低检查                                                                                                                                                                                                  |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 仅 Python source | Ruff check + Ruff format check + Pyright strict + ty strict（`uv run -m ty check --output-format github`）+ relevant pytest                                                                                |
| 仅 docs site     | `pnpm --filter docs lint`（通过 ESLint/Astro/MDX config 覆盖 `.ts/.tsx/.astro/.mdx`）+ docs tests + docs type check + docs build + Playwright hook smoke + `src/components/p5/` 或 `src/components/ui/` 改动时运行 Vitest |
| 仅 Markdown      | `pnpm exec markdownlint-cli2`                                                                                                                                                                            |
| i18n strings    | `task i18n` + relevant pytest                                                                                                                                                                            |
| 基础设施配置          | `docker compose config` + `prek run --all-files` + `task ci:typecheck`                                                                                                                                   |
| 混合 / 不确定        | `task check && task test`                                                                                                                                                                                |

开发中优先 granular checks。完整 `task check && task test` 用于提交前或大范围验证。

### Git Hooks

- Pre-commit 基于变更文件类型运行 Prek auto-fix、markdownlint、Ruff、Pyright、ty、pytest、docs lint/type/test/e2e smoke、`.tsx` 的 React Doctor，随后运行非阻断 `gitnexus analyze --force`（全量重建，非增量 —— 增量模式存在 FTS 索引损坏 bug，详见 `.trae/specs/fix-gitnexus-post-commit-fts/`），并自动将 AGENTS.md/CLAUDE.md 更新暂存进即将创建的提交。
- Commit message 使用 gitmoji + Conventional Commits，并自动追加 Signed-off-by。
- Hook CLI 解析顺序：local `node_modules/.bin`、global PATH、通过 `cmd.exe /c` 执行 global `.cmd` shim、`pnpm dlx`、最后 `npx -y`。
- 仅在明确需要时设置 `$env:HUSKY='0'`，例如自动化提交。

## E — Evidence

### Required Closeout

代码变更结束时说明：

- 改了什么、触及哪些文件。
- 运行了哪些 targeted checks，结果如何。
- 哪些检查未运行及原因。
- 哪些既有 dirty worktree 变更未触碰。
- AGENTS/CLAUDE/中文镜像是否需要同步。

### Lessons Learned

经验教训是失败防线，不是 changelog。保持短、当前、可验证。依赖、API、CI 行为在使用前重新验证。

#### Documentation And Mirror Sync

- 更新仓库 guidance 时，保持 `AGENTS.md`、`CLAUDE.md`、`.github/note/AGENTS-zh.md` 结构一致。
- 三个 agent context 文件（`AGENTS.md`、`CLAUDE.md`、`.github/note/AGENTS-zh.md`）MUST 结构对齐。向其中之一新增教训或约束时，同一 PR 内必须镜像到另外两个文件。
- 结构一致不包括 GitNexus marker 块；该块由 `gitnexus analyze` 生成。保持 marker comments 和其他尖括号定位标签原样，确保 CLI 能找到受管范围。
- 不在 agent context 嵌入大型生成清单。链接 canonical docs 或检查实时文件。
- 结构性源码变化后，更新 developer docs 并搜索 stale references。

#### Ignore Comment Governance

- `src/` 中的内联 `# noqa` / `# type: ignore` 已全部集中到 `pyproject.toml` `[tool.ruff.lint.per-file-ignores]`；禁止与执行（Phase 2.5 告警 + CI `ignore-comment-audit` PR 评论）见 "Code Style → 忽略注释治理"。以下各条记录 `per-file-ignores` 中保留的合法例外。
- NoneBot matcher handler 和 ORM upsert 函数的 `PLR0913`（参数过多）通过 `per-file-ignores` 抑制，因为参数列表受框架约束。未来向 frozen dataclass 请求对象重构（见 "Repository API Style"）应逐步削减这些抑制。
- `BLE001`（blind-except）在启动/探测代码中允许使用（fail-closed/fail-soft 设计）。理由注释以普通 `# <reason>` 形式保留在行内，不使用 `# noqa` 指令。

#### Adapter And API Boundaries

- 同名 adapter API 可能返回不同形状。OneBot V11 API 常返回 `dict`；写访问模式前检查已安装 adapter 源码。
- deprecated Milky、QQ、OneBot V12 源码已从项目中彻底移除，包括所有按需加载工具。
- OneBot V11 群 `event.get_session_id()` 可能同时包含群和用户 ID。群级历史必须用 `group_id` 作为 `conversation_id`。
- OneBot V11 图片 API 变更前，先用当前 adapter 和 NapCat 文档确认 file field 格式。
- WSL2 + Docker Desktop bind mount 要求 WSL 发行版根目录必须加入 Docker Desktop File Sharing 白名单。漏配时容器内 bind 目标是空目录，但 `docker inspect` 仍报源路径正确。判断方法：`docker exec <ctr> mount | grep <src>`，出现 `fuse.bind` 或纯 `bind` 是正常；`overlay`（lower=`/tmp/docker-desktop-root-ro`）说明桥接层返回了空视图。修法：在 Docker Desktop → Settings → Resources → File sharing 加 `\\wsl.localhost\<distro>\`（旧版 WSL 写 `\\wsl$\<distro>\`），点 **Apply & restart** 后重建容器。Windows 侧 docker daemon 不会通过普通 bind 看到 WSL 路径；WSL Integration 与 File Sharing 是两个独立开关，不能假设"已经开了"。

#### Handler Session Injection

- nonebot_plugin_orm 的 `async_scoped_session` 是 `Annotated[sa_async.async_scoped_session[sa_async.AsyncSession], Depends(coroutine(get_scoped_session))]` —— `Depends` 已嵌入 `Annotated` 元数据。正确签名是 `async def handler(session: async_scoped_session, ...)`（仅类型注解）；写 `session: async_scoped_session = Depends(async_scoped_session)` 会触发 pyright strict 错误，且是错误的。
- 需要 NoneBot 依赖注入（bot、event、session）的 handler 签名 MUST 在任何 wrapper 上使用 `@wraps(func)`，让 `inspect.signature(wrapper)` 跟随被包装函数 —— NoneBot 通过 signature 决定注入哪些 kwargs。
- 在 wrapper 内部（如 `_permission_wrapper`），通过 `session = kwargs.get("session")` 提取已注入的 session；不要重新 `get_session()`。
- handler 测试 fixture 使用 `mock_session = AsyncMock()`，并把 `sess.add = MagicMock()` / `sess.add_all = MagicMock()`（同步 API 用同步 mock）；调用 handler 时传 `session=mock_session`。断言 `mock.call_args` 时注意 `args[0]` 现在是 `session`（repository/permission 函数首参为 session）。
- 后台任务（`services/scheduler.py`、`services/message_store.py`）保留 `async with get_session() as session:`，因为它们自管生命周期，不属于 NoneBot handler 依赖。写入后 MUST 在块内 `await session.commit()` —— `async with` 退出只关闭 session（未提交事务被回滚），没有外部调用方替它们 commit（2026-08-14 实例：消息存储数月静默零记录，导致撤回恒返回 0/0/0）。

#### NoneBot 配置透传（Config Passthrough）

- NoneBot `Config` **大小写不敏感**：自定义 env 键在 `Config.model_dump()` 里全部存为**小写**（`LINGCHU_MESSAGE_STORE_ENABLED` → `lingchu_message_store_enabled`）。**属性访问**（`driver.config.LINGCHU_X`）大小写不敏感、可用；但**对 `model_dump()` 做 dict 查找 MUST 用小写键**。
- 通过 `_value(source, *names, default)` 读取自定义键时，查找名列表 MUST 包含小写全名（`lingchu_<field>`），不能只写大写 env 名。否则键永远匹配不上，该设置成为**死配置** —— 无论 `.env.dev` 写什么，运行时恒为默认值。2026-08-14 已修复 7 个键（`_lingchu_bot_contracts/runtime_settings.py`：message_store_enabled、retention_days、summary_limit、record_api_calls、cleanup_enabled、recall_message_default_count、superuser_key、protected_subject_feature_keys）。
- 诊断：启动 DEBUG 日志 `Loaded Config: {...}` 里**能看到键 ≠ 配置生效**。要看消费方是属性访问还是对 `model_dump()` 做 dict 查找。死配置症状：改 `.env.dev` 运行时零效果、值恒为默认。
- env 文件解析链：`Env()` 读 `.env` → `ENVIRONMENT` → `nonebot.init()` 以 `.env.{ENVIRONMENT}`（如 `.env.dev`）为 `_env_file`。DEBUG 行 `Current Env: dev` 可确认链路。
- zhenxun 宿主部署：`_lingchu_bot_contracts` 运行时从 **site-packages 副本**（uv 安装）导入，不是 `zhenxun/plugins/` 下的 —— 必须连 venv 副本一起改；后续 `uv sync`/重装会冲掉手动修改。

#### Adapter Handle Decorators

- 被 `selected_adapter_handle` 装饰的 handler 模块 MUST NOT 使用 `from __future__ import annotations`。NoneBot 的 `get_typed_signature` 通过 `wrapper.__globals__`（即 `handle/qq/commands/common.py` 模块命名空间）解析 forward refs，而不是 `func.__globals__`。`@wraps(func)` 复制 `__wrapped__` / `__name__` / `__annotations__`，但 NOT `__globals__`，因此 adapter-specific 事件类型（如 `GroupMessageEvent`）在启动时变成无法解析的 `NameError`。保持注解为真实类型对象；参考同名的 OneBot V11 sibling 文件，它从不使用 `from __future__ import annotations`。
- 失败面：`handle/qq/commands/common.py::_state_wrapper`（装饰器）；`handle/telegram/adapters/default/` 下的 5 个 Telegram handler（`bot_state.py`、`menu.py`、`moderation.py`、`mute.py`、`recall.py`）曾在 dev smoke test 中抛出 `NameError: name 'GroupMessageEvent' is not defined`。修复以每个 Telegram 文件顶部的 docstring 与 `_state_wrapper` 内的 NOTE 块形式保留。

#### Supply Chain

- `.github/workflows/*.yml` 中所有第三方 GitHub Actions 都按 40 字符 commit SHA 锁定并附 `# vX.Y.Z` 注释（非可变 tag）。`ci-builds.yml` 与 `release.yml` 均使用 `actions/attest-build-provenance@v4.1.0`（SHA `a2bbfa2…`）生成 SLSA Build L3 provenance。用 `gh attestation verify <artifact> --repository xinvxueyuan/lingchu-bot` 验证。
- 版本验证系统：分支名约定（`dev-minor-*`/`dev-major-*`/`dev-alpha-*`/`dev-beta-*`/`dev-rc-*`/`dev-stable-*`）驱动 `ci:version:bump` 中的 `BUMP_LEVEL`/`BUMP_PRERELEASE`。`ci:version:precheck` 校验 PEP 440 + 大于所有 tag + 源一致性 + 无重复 tag。`ci:version:postcheck` 调用 `release:verify-version` + dev release 语义。智能 bump 策略处理 stable vs pre-release tag：stable tag 需要 level+prerelease，同类 pre-release tag 仅 bump prerelease，`stable` 清除 prerelease。
- 发布分支从字面量 `releases/X.Y.Z` 改为 bump-style `releases/<bump-name>`（`major`/`minor`/`patch`/`stable`/`alpha`/`beta`/`rc`），从而发布工作流可以直接复用 `versioned-build` 的 `task ci:version:bump`。实际版本由最新 tag + `uv version --bump` 推导，再由 `ci:version:write-config` 把 `core/config.py` + `package.json` 同步后打 tag。
- `release.yml::validate` 通过共享的 `task ci:version:derive-bump` 任务（委托给 `scripts/ci_derive_bump.py`）从分支名推导 `BUMP_LEVEL` / `BUMP_PRERELEASE`，与 `ci-builds.yml::versioned-build`、`release:prepare`、`release:notes` 共享同一份单一来源。`task ci:version:bump` 在 `release:prepare` / `release:notes` 中以 `DRY_RUN=true` 调用，因此本地脚手架不会污染 `pyproject.toml`（任务在 bump 后执行 `git checkout -- pyproject.toml`）；`build` job 在 CI 计算的版本与本地写入版本出现漂移时会 amend 发布分支，使 tag 与源码保持一致。`workflow_dispatch` 现在接收 `bump` 选项输入而非字面量版本号。
- 发布说明仍按计算出的版本号命名（`.github/releases/<version>.md`）；开发者通过 `task release:notes`（或 `release:prepare` 钩子）在推送前脚手架该文件。发布时 `github-release` job 会把手工 notes 与 GitHub 自动生成的变更说明（generate-notes API，在 tag 创建后调用）合并为 release body —— 手工 notes 在上、自动 PR/commit 变更列表在下，中间以 `---` 分隔。该合并步骤同时修复了原跨 job 引用 `RUNNER_TEMP` body_path 的隐患（不同 job 的临时目录相互隔离，原 body 文件在 release runner 上并不存在）。
- `.github/ISSUE_TEMPLATE/` 使用 YAML 表单模板（`bug.yml`、`feature.yml`、`docs.yml`、`config.yml`）；`blank_issues_enabled: false` 带 contact\_links 指向 docs 站和安全策略。不要重新引入 Markdown issue 模板。
- `CHANGELOG.md` 遵循 Keep a Changelog 1.1.0 格式，包含 `## [Unreleased]` 节和底部 compare 链接。

#### Docker And Runtime

- `Dockerfile` 使用多阶段构建与 `# syntax=docker/dockerfile:1.7` BuildKit pragma、非 root `app` 用户、完整 OCI labels、`SMOKE_TEST` build arg 用于条件 smoke-test。`docker-compose.yml` 使用 named volumes（`lingchu-config`/`lingchu-data`/`lingchu-cache`）与 `env_file: .env.prod`。

#### Testing And Typing

- 修改函数签名时，grep 所有调用方，更新 fixtures，并运行 Ruff、Pyright、ty、pytest。
- 修改钩子、适配器或启动流程后，运行三阶段真实启动冒烟测试（完整流程见 `apps/docs/src/content/docs/developer-guide/engineering/testing-ci.mdx` → "Runtime smoke test"）：
  - **开发环境**：`uvx --from nb-cli nb.exe run` 通过 `ENVIRONMENT=dev` 载入 `.env` + `.env.dev`；需观察到 `Application startup complete.` 并至少完成一个事件周期。能捕获静态分析无法发现的前向引用签名错误与导入顺序问题。
  - **生产环境**：删除 `config/nonebot_plugin_lingchu_bot/`、`data/nonebot_plugin_lingchu_bot/`、`data/nonebot_plugin_orm/`、`cache/nonebot_plugin_lingchu_bot/`（均为 localstore 管理），设置 `ENVIRONMENT=prod`，再 `uvx --from nb-cli nb.exe run` 载入 `.env` + `.env.prod`。验证启动能在干净 localstore 下存活。
- gettext-heavy handler 中不要用 `_` 当临时变量覆盖 gettext helper。
- 测试中的 side-effect exception 必须匹配生产代码 `except` 分支。
- NoneBot event narrowing 使用 `isinstance(event, GroupMessageEvent)`。
- 按真实 API shape mock adapter 返回值。
- `assert_called_once_with()` 是精确匹配；optional kwargs 用 `mock.call_args.kwargs` 检查存在性。
- SubAgent 会产生临时文件（`_tmp_cov.sh`、`_writetest.txt`、探针脚本等）且从不自行清理。编排者 MUST 在 SubAgent 批次结束后运行 `git status --short`，并在 staging/commit 前 `rm -f` 所有临时文件，否则 pre-commit 钩子会因意外文件失败，提交也会携带垃圾。
- 在测试中重写 `list.__getitem__` 时，必须匹配 typeshed 签名：`def __getitem__(self, index: SupportsIndex | slice, /) -> list[object]`。使用 `int | slice` 或省略 `/` 会触发 `reportIncompatibleMethodOverride`。重写 `BaseException.args` 容易签名不兼容（与读写 property 冲突）；敌对 args 测试优先用 `__getattribute__` 拦截。
- 使用 `yield` 的 pytest fixture MUST 声明返回类型 `collections.abc.Iterator[None]`（或 `Generator[None, None, None]`），绝不能用 `-> None`。Pyright strict 模式会把 generator 函数的 `-> None` 当作返回类型错误，husky pre-commit Phase 4 钩子会阻断提交。

#### Docs Site And Frontend

- `eslint-plugin-react@7.x` 与 ESLint 10 不兼容；pin ESLint 9 或迁移到 `@eslint-react/eslint-plugin`。
- `apps/docs` 使用 Astro/Starlight-aware lint 和 type checks。MDX lint 保持收窄到 docs content，`.astro` 文件由 docs lint script 覆盖，并由 `astro check` 在 build 前验证 Starlight content collections。双 markdown linter 政策保持：`markdownlint-cli2` 覆盖 `.md`；docs ESLint/MDX tooling 覆盖 `.mdx`（无重叠）。
- MDX 表格 cell 不能在 inline code 中包含裸 `|`，例如 `<群号|群名称>`；改用 `<群号或群名称>`。
- Starlight root-locale 页面发布时不带 `/en/`；内部链接使用与 Astro 生成路由匹配的 root-relative URLs。
- 触碰 docs routing helper 的 Vitest 测试需要 mock Starlight/Astro content collection imports。
- 测试需要导入的共享函数应从 component file 中抽到独立模块。
- Component file 导出 utility 可能破坏 React Fast Refresh；移到非 component module。
- Starlight/Pagefind search output 在 docs build 时生成；CI smoke tests 必须 serve `apps/docs/dist`。
- Docker 服务不要占用 Playwright webServer 的 `3100` 端口；使用 `6100:3000` 等 CI 范围外端口。
- `docs:check-types` 应直接运行 Astro/Starlight 类型验证；不要重新引入旧文档生成或框架 typegen steps。

#### Database And Runtime Files

- 所有数据访问通过 `nonebot_plugin_orm` 和 `database/orm_crud/`；不要重新引入自定义 engine management。
- 文件转 package 需要在 `__init__.py` 显式 re-export。
- Alembic model package 必须 import 所有 models，保证 discovery 生效。
- 非 SQLite 测试前先运行 migrations。
- `ensure_toml_dict_file_async()` 只创建缺失文件；覆盖写入用 `write_toml_dict_file_async()`。
- 迁移生成工作流：`nb orm revision -m "msg" --branch-label nonebot_plugin_lingchu_bot` 默认开启 autogenerate（无 `--autogenerate` 标志）。Taskfile 别名：`task db:revision -- MSG="..."`、`task db:check`、`task db:upgrade`。autogenerate 产出的是 `sa.Boolean` / `sa.DateTime(timezone=True)` / `sa.Text` / `sa.String`，必须手动改写为 `database/_dialect_compat.py` 中的 `CompatBoolean` / `CompatDateTimeTZ` / `CompatText` / `compat_string(length)` 以兼容六种数据库。autogenerate 无法识别列/表重命名（会生成 drop+add，丢数据），重命名需手动用 `op.alter_column` 编写迁移。CI 在 `nb orm upgrade` 后运行 `nb orm check` 强制模型与迁移同步。不带 --branch-label 时文件会落到 ./migrations/versions/ 而非插件迁移目录。
- `nb orm upgrade` 在本地开发库上不可靠：当库由 `Base.metadata.create_all()` 或早期直接建表产生时，alembic 版本表无初始迁移记录，`nb orm upgrade` 会重跑 `initial schema` 导致 `sqlite3.OperationalError: table lingchu_message_records already exists`。每次更改模型定义时都应手写迁移脚本（autogenerate 仅作起点，不是终点）。本地开发库若已存在表但无迁移历史，用 `nb orm stamp head` 标记为最新而非重跑迁移；或删除 DB 文件后从头执行 `nb orm upgrade`。

#### 跨数据库方言适配（随 MariaDB / Oracle / SQL Server 支持新增）

- `database/_dialect_compat.py` 提供 `CompatBoolean`、`CompatDateTimeTZ`、`CompatText`、`compat_string(length)` 作为跨方言类型；ORM model MUST 使用这些 helper，禁止直接用裸的 `String` / `Text` / `Boolean` / `DateTime(timezone=True)`。
- `CompatDateTimeTZ` 在 MySQL / MariaDB 上编译为 `DATETIME(6)` 并发出 "timezone only supported in MySQL 5.6+" 警告；写入侧统一用 `datetime.now(UTC)`（即 `database/models/message.py` 中的 `utc_now()`），实际无时区漂移。
- `CompatBoolean` 在 Oracle pre-23c 映射 `NUMBER(1)`，23c+ 用原生 `BOOLEAN`；应用层不需要做方言分支。
- `CompatText` 在 Oracle 映射 `CLOB`，避免 `VARCHAR2(4000)` 截断长文本。
- `compat_string(length)` 仅在 `length > 4000` 时切换为 SQL Server 的 `NVARCHAR(MAX)`；本仓库所有 `String` 列均 ≤ 128，各方言均保持为 `VARCHAR(N)`。
- `orm_crud/_bulk.py::upsert` 支持 6 个后端：SQLite / PostgreSQL 使用 `sqlite_insert` / `postgresql_insert` + `on_conflict_do_update`；MySQL / MariaDB 共用 `mysql_insert` + `on_duplicate_key_update`（`mariadb` 官方驱动在 SQLAlchemy 2.0.51 仍以 `mysql` dialect 路径编译，但 `dialect.name == "mariadb"`）；Oracle / SQL Server 通过私有函数 `_oracle_upsert` / `_mssql_upsert` 显式拼装 `MERGE INTO` 原始 SQL（经 `sqlalchemy.text()` + 命名绑定参数）。
- **Oracle / SQL Server upsert 验证事实**：`from sqlalchemy.dialects.{oracle,mssql} import insert` 抛 `ImportError: cannot import name 'insert'`；通用 `from sqlalchemy import insert` 返回的 `Insert` 对象**无** `on_conflict_do_update` 方法；`oracle/base.py` 与 `mssql/base.py` 中无 `MERGE INTO` / `visit_insert` 编译逻辑。如未来升级 SQLAlchemy ≥ 2.1（已提供 `mssql.insert` / `oracle.insert`）需重新评估。
- Oracle `MERGE INTO` 用 `USING (SELECT :p1 AS c1, :p2 AS c2 FROM DUAL) s`；SQL Server 用 `USING (SELECT :p1 AS c1, :p2 AS c2) s`（无 `FROM DUAL`）。两个后端均无 `INSERT ... RETURNING`，执行 MERGE 后通过 `SELECT ... WHERE conflict_keys` 取回最新行。
- Oracle 最低版本 12.2（2016-12）；现有表 / 约束名均在 128 字符限制内，未做重命名。新增标识符前需核对部署目标是否兼容 30 字符限制。
- MariaDB 与 MySQL 使用统一驱动 `aiomysql`；SQLAlchemy 通过连接字符串自动检测 dialect（`mysql` vs `mariadb`），无需专用 `mariadb` Python 驱动。移除专用驱动可简化依赖并避免 CI 静态分析环境的系统库问题（`mariadb` 驱动依赖系统级 MariaDB Connector/C，在极简 CI 环境可能构建失败）。
- `oracledb` 2.0+ 默认 Thin 模式，CI 镜像无需安装 Oracle Instant Client。
- `aioodbc`（含传递依赖 `pyodbc`）在 Linux CI 需要系统 ODBC Driver 18 包（`ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18 unixodbc-dev`）；macOS 用同名 brew 包；Windows 自带。
- CI 矩阵跨 6 个引擎跑 10 个任务，均启用 `fail-fast: false`（SQLite + PostgreSQL 16/18 + MySQL 8.4/9.7 LTS + MariaDB 11.4/11.8 LTS + Oracle 23ai + SQL Server 2022/2025）；Oracle / SQL Server 启动慢（health-start-period 90-180s），单次全跑约 8-15 分钟，预算 CI 时间时需要考虑。SQL Server 已从废弃的 `azure-sql-edge` 镜像迁移到 `mcr.microsoft.com/mssql/server:{2022,2025}-latest`（两者均自带 `mssql-tools18` 用于健康检查）。矩阵条目携带 `engine` + `image` 字段；服务容器通过 `${{ matrix.db.engine == '<engine>' && matrix.db.image || '' }}` 选择镜像，使同一引擎的多个版本可在一个矩阵中共存。

#### Actions DRY 重构

- **复合 action 目录**：5 个可复用 composite action 位于 `.github/actions/<name>/action.yml` —— `checkout`、`setup-node-pnpm`、`setup-uv-task`、`setup-toolchain`（组合前三者）、`verify-wheel`、`attest-slsa`。新工作流 MUST 通过 `uses: ./.github/actions/<name>` 消费它们，而不是重新声明 `actions/checkout`、`actions/setup-node`、`pnpm/action-setup`、`astral-sh/setup-uv`、`go-task/setup-task` 或内联 `actions/attest-build-provenance` 步骤。Inputs（`fetch-depth`、`node-version`、`python-version`、`with-retry`、`subject-path`）覆盖了所有旧调用点；只有需要原本不可能的参数时才新增 input。
- **集中化 bump 推导**：`task ci:version:derive-bump`（委托给 `scripts/ci_derive_bump.py`）是 `BUMP_LEVEL` + `BUMP_PRERELEASE` 的唯一来源。`ci-builds.yml::versioned-build`、`release.yml::validate`、`task release:prepare`、`task release:notes` 全部调用它，不再各自维护 `case` 映射。分支名约定集中在一组正则中，新增 dev- 或 release-bump 类型只需一行修改。
- **SHA 升级成本下降**：重构前升级 `actions/checkout` SHA 需要编辑 37 个工作流文件；重构后只需在 `.github/actions/checkout/action.yml` 改一处，下游工作流自动继承。composite action 边界是新的“pin surface”——40 字符 SHA + `# vX.Y.Z` 注释约定只出现在 composite action 内部的 `uses:` 行，绝不出现在调用方。
- **YAML 之外的 inline 代码**：wheel 验证、SLSA attestation 设置、bump 推导原本是嵌在 3 个工作流中的 12 行 `run:` 块，现在分别是 `scripts/ci_verify_wheel.py`、`.github/actions/attest-slsa`、`scripts/ci_derive_bump.py`。超过 5 行逻辑的 workflow 步骤 SHOULD 抽取到 `scripts/`，再通过精简的 composite action 或 `run:` 步骤调用。
- **文件名去 emoji**：通过 `git mv` 重命名 10 个工作流（如 `🚀-release.yml` → `release.yml`），`git log --follow <new-name>` 保留 rename 前的历史。新增 workflow 时文件名 MUST NOT 带前导 emoji；emoji 只允许出现在 `name:` 字段中。

#### Hooks, CI, And GitHub

- Windows 下 Bash hooks 可能找到不可直接运行的 `.cmd` shim。Windows Node shim 通过 `cmd.exe /c` 执行。
- Hook 中不要吞掉 `git diff --cached` 失败。
- 机械性问题优先用 CLI auto-fix：Ruff fix/format、markdownlint `--fix`、ESLint `--fix`、Prek。
- Markdownlint 配置集中在 `.markdownlint-cli2.jsonc`；调用点应依赖该配置。
- PowerShell markdownlint 优先 `pwsh.exe -NoProfile`，避免临时手写 quoted globs。
- GitHub Actions pin 到 commit SHA，不 pin annotated tag object SHA。
- Workflow 文件名使用纯 kebab-case（不带前导 emoji）；`name:` 字段仍使用英文并匹配 emoji，使 Actions UI 能视觉分组。修改 `name:` 中的 emoji 不需要重命名文件。
- `.github` YAML 注释使用英文；移除空的/损坏的 schema comment。
- `git push origin --delete` 前用 `git ls-remote` 检查远端分支是否存在。
- CI 工作流按领域拆分：`python.yml`（Python 静态分析 + 多数据库测试矩阵 + auto-format）、`frontend.yml`（docs lint/type/test/links）、`docs.yml`（docs 部署）、`ci-builds.yml`（版本 bump + build artifacts + SLSA provenance）、`release.yml`（PyPI/GHCR 发布）、`clear-workflow.yml`（手动 dispatch；通过 `actions: write` 删除非运行中的 workflow run）、`issues-top.yml`（每日定时；label 并展示 top issues）、`stale.yml`（每日定时；14+7 天无活动后标记并关闭陈旧 issue）、`react-doctor.yml`（`.tsx` 变更时 PR/push；直接运行 React Doctor CLI — 见 Pending Rollbacks）、`playwright.yml`（`apps/docs` 变更时 PR/push；带 browser cache 的 Playwright E2E）。共享的变更检测位于 `.github/actions/detect-changes` 复合 action（输出 python/markdown/frontend-\* 标志）。共享的 setup 逻辑位于 `.github/actions/{checkout,setup-node-pnpm,setup-uv-task,setup-toolchain,verify-wheel,attest-slsa}` 复合 actions 中，每个工作流只需声明 `uses:` 引用即可。标准触发约定：PR 仅跑检查（不提交/部署）；push 到 `main`/`dev` 跑检查 + auto-format + 部署。每个工作流有独立的 concurrency group 以避免互相取消。Workflow 文件名不再带前导 emoji（`name:` 字段仍保留），以便跨平台文件系统与 CLI tab-completion 保持稳定。
- Python CI 的 Static Analysis job 使用 `uv sync --no-dev --group lint --group git --frozen` + `UV_NO_SYNC=1` 来只安装 lint/format 所需的最小依赖集（ruff、pyright、ty、prek），避免安装 test 组中包含的数据库驱动（mariadb、aioodbc）——这些驱动需要系统级库，在极简 CI 环境中可能构建失败。任何不需要运行测试的 CI job 都可使用此模式。

#### Pending Rollbacks

| What                               | Where                                   | Why                                       | Rollback condition          |
| ---------------------------------- | --------------------------------------- | ----------------------------------------- | --------------------------- |
| `deslop/unused-export: "off"`      | `doctor.config.ts`                      | `useMDXComponents` 是框架要求 re-export，但当前未消费 | `useMDXComponents` 被实际消费后移除 |
| React Doctor CLI instead of action | `.github/workflows/react-doctor.yml` | 上游 action 有 detached HEAD 和 ANSI 泄漏问题     | 上游发布修复后切回 action            |
