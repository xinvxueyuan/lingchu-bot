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

## Lingchu Bot Agent Guide

> [English](../../AGENTS.md) | 中文

上方 GitNexus 块由 `gitnexus analyze` 管理。不要手动编辑、翻译、重排或同步 `<!-- gitnexus:start -->` 到 `<!-- gitnexus:end -->` 之间的内容。`<!-- ... -->` 这类带尖括号的 HTML 注释是 CLI 定位锚点；除非 owning CLI 文档明确要求，否则不要删除、转义、改名、翻译、复制或移动。

这是 `AGENTS.md` 的中文镜像。保持结构同步，内容以 `AGENTS.md` 为准；不要把本文件维护成独立规则集。

## CREATE 框架

本指南按 CREATE 组织，让 agent 快速取用约束：

| 字母 | 章节 | 目的 |
| --- | --- | --- |
| C | Context | 项目是什么、各类事实来源在哪里 |
| R | Role | agent 在本仓库中的工作方式 |
| E | Expectations | 不可违反的约束和质量门禁 |
| A | Actions | 标准开发流程和联动面 |
| T | Tools | 命令、skills、MCP、hooks、验证路径 |
| E | Evidence | 经验教训、清单和收尾证据 |

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
- Next.js 文档站：`apps/docs/`
- 项目本地 skills：`.agents/skills/`
- 中文 agent 指南镜像：`.github/note/AGENTS-zh.md`
- Claude Code 指南镜像：`CLAUDE.md`

构建或包分发所需内容必须位于 `src/plugins/nonebot_plugin_lingchu_bot/` 下。仓库根目录的 `config/`、`data/` 等运行时/配置文件是本地开发产物，可丢弃。

不要在本文件维护手写完整目录树。需要当前结构时使用 `rg --files`、GitNexus，或查看 `apps/docs/content/docs/developer-guide/`。

## Tech Stack

Python 后端：

- Python 3.13，由 `uv` 管理
- NoneBot2 + OneBot V11 adapter；Milky、QQ、OneBot V12 已停维并移除
- `nonebot-plugin-alconna` 负责命令解析
- `nonebot-plugin-orm` + `aiosqlite` 负责异步数据库
- `nonebot-plugin-localstore` 负责 mutable data/config/cache/resource/schema 路径
- Ruff、Pyright、ty、pytest

文档站：

- Next.js 16、Fumadocs 16 static export、React 19、Tailwind CSS 4、TypeScript 6
- Vitest、Testing Library、ESLint、Playwright
- i18n、RSS、Mermaid、Twoslash、EPUB 导出、`/llms.txt`、`/llms-full.txt`、文档关系图
- 所有 server components、route handlers、lib functions 都是 async
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

## E — Expectations

### Canonical Context Files

| 文件 | 何时加载 | 目的 |
| --- | --- | --- |
| `AGENTS.md` | Codex / Trae 共享上下文 | canonical 项目规则、命令、约束和经验 |
| `CLAUDE.md` | Claude Code 上下文 | 与 `AGENTS.md` 同结构，唯一允许额外章节是 Claude Code Behavioral Guidelines |
| `.github/note/AGENTS-zh.md` | 中文镜像 | `AGENTS.md` 的中文 counterpart，结构同步 |
| `.trae/rules/git-commit-message.md` | Trae always-applied rule | Gitmoji + Conventional Commits 校验 |

当 `AGENTS.md`、`CLAUDE.md`、`.github/note/AGENTS-zh.md` 不一致时，以 `AGENTS.md` 为准，再把相同结构变更复制/同步到另外两个文件。

该同步规则从 `<!-- gitnexus:end -->` 之后开始。GitNexus marker 块由工具拥有，且各文件可能不同；不要手动统一。HTML comment markers 是 CLI contract，不是普通 prose。

### Hard Constraints

- **Localstore 路径所有权**：所有 mutable data、config、cache、resource、schema 文件必须通过 `nonebot_plugin_localstore` helper 解析，例如 `get_plugin_data_dir()`、`get_plugin_config_dir()`、`get_plugin_cache_dir()`、`get_plugin_data_file()`、`get_plugin_config_file()`、`get_plugin_cache_file()`。
- **禁止硬编码 mutable 路径**：禁止对 mutable runtime 文件使用 `Path("...")`。
- **禁止打包 schema resource**：不要用 `importlib.resources` 或 wheel data 提供 JSON schema。Schema 文本位于 `src/plugins/nonebot_plugin_lingchu_bot/core/schemas.py`，由 `install_schemas()` 安装。
- **Prek 是 hook 唯一来源**：`prek.toml` 是唯一 pre-commit hook 配置，不要重新引入 `.pre-commit-config.yaml`。
- **版本同步**：使用 `Taskfile.yml` 的 `ci:version:write-config` 同步写入 `src/plugins/nonebot_plugin_lingchu_bot/core/config.py` 和根 `package.json`。
- **Skills 排除列表同步**：修改 `pyproject.toml` 中 skills exclusion pattern 时，同步 `prek.toml` 对应注释/模式。

### Architecture Decisions

- Docs route handlers、server components、`baseOptions()`、`buildGraph()`、`getRSS()` 返回 Promise。
- Docs i18n 使用 `hideLocale: 'default-locale'`；默认英文 URL 不带 `/en/`。
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

| 面向 | 常见文件 |
| --- | --- |
| Source | `src/plugins/nonebot_plugin_lingchu_bot/` |
| Tests | `tests/` |
| i18n | `src/plugins/nonebot_plugin_lingchu_bot/i18n/`；用户可见字符串变化时运行 `task i18n` |
| Docs | `apps/docs/content/docs/` |
| Menu | `src/plugins/nonebot_plugin_lingchu_bot/handle/menu.py` |
| Runtime config | `config.json5`、`bot_state.json5`、`menu.json5`、`core/schemas.py` schema 文本 |
| Handle config files | `handle_config_defaults/`、localstore config_dir 中的 `<command_key>.json5` |
| Triggers | `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/commands/triggers.py` |
| Agent context | `AGENTS.md`、`CLAUDE.md`、`.github/note/AGENTS-zh.md` |

涉及 handle、QQ command、adapter handler、matcher、`command_key`、menu、trigger、permission、config 耦合的工作，使用 `.agents/skills/engineering-workflow/references/delivery-loop/references/handle-feature-workflow.md`。

### Command And Menu Rules

- 群命令触发词是 locale-exclusive。不要为同一个 matcher 同时注册中文和英文触发词。使用 `get_configured_locale()`，并排除非当前语言 aliases。
- 菜单 fail closed。隐藏当前身份或实现不能执行的命令。
- `MENU_FEATURES.command_key` 是 permission checks、menu filtering、handler decorators 的共享命令标识。
- 添加命令时，同步 triggers、`MENU_FEATURES`、tests、QQ command-reference docs。
- 远程管理命令仅 OneBot V11 支持，实现在 `handle/qq/adapters/onebot11/default/remote.py`。

### State And Config Rules

- `core/bot_state.py` 通过 localstore 持久化 `bot_state.json5`。
- `is_handle_active(platform_id)` 按 global AND platform 解析。
- `is_silent_mode(platform_id)` 按 global OR platform 解析。
- `selected_adapter_handle()` 支持 `bypass_gate` 和 `bypass_silent`。
- “闭嘴”/“说话”绕过 silent mode，但不绕过 shutdown gate。
- “开机”/“关机”同时绕过 gate 和 silent mode。
- `install_schemas()` 必须在 runtime JSON5 文件引用 schema basename 前运行。失败只记录日志，不中断启动。

### Repository API Style

- 对包含耦合字段的 write/audit API，使用 frozen dataclass request object。
- Command audit payload 使用 `CommandAudit`，再调用 `record_audit_fire_and_forget()` 或 `record_command_audit()`。
- 不新增 platform、adapter、bot、group、target、reason、duration 等长参数列表；创建 request object。
- `fire_and_forget(coro, *, name="...")` 只用于调用方不需要结果的可丢弃后台工作。

## T — Tools

### Skills And MCPs

| 需求 | 路由 |
| --- | --- |
| 当前 library、framework、SDK、API、CLI、cloud 文档 | 通过 `tool-workflows` 使用 Context7：resolve library ID，再用完整用户问题 query docs |
| OpenAI 产品/API 文档 | `openai-docs`，只用官方文档 |
| 架构、影响、重构、review、前端质量、issue planning | `.agents/skills/engineering-workflow/SKILL.md` |
| Lingchu / NapCat / QQ live runtime 故障 | `.agents/skills/interactive-runtime-debugging/SKILL.md` |
| Hooks、Prek、Husky、skill 管理 | `.agents/skills/tool-workflows/SKILL.md` |
| OneBot V11 / NapCat API 签名 | 写 adapter 调用前查 NapCat API MCP |
| GitHub PR、issue、CI、发布 | GitHub skills |

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

| 变更 | 提交前最低检查 |
| --- | --- |
| 仅 Python source | Ruff check + Ruff format check + Pyright + ty + relevant pytest |
| 仅 docs site | `pnpm --filter docs lint`（通过 ESLint flat config + eslint-plugin-mdx 覆盖 `.ts/.tsx/.mdx`）+ docs tests + Playwright hook smoke + docs type check + content 变更时 link lint |
| 仅 Markdown | `pnpm exec markdownlint-cli2` |
| i18n strings | `task i18n` + relevant pytest |
| 混合 / 不确定 | `task check && task test` |

开发中优先 granular checks。完整 `task check && task test` 用于提交前或大范围验证。

### Git Hooks

- Pre-commit 基于变更文件类型运行 Prek auto-fix、markdownlint、Ruff、Pyright、ty、pytest、docs lint/type/test/e2e smoke、`.tsx` 的 React Doctor，以及 non-blocking GitNexus analyze。
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
- 结构一致不包括 GitNexus marker 块；该块由 `gitnexus analyze` 生成。保持 marker comments 和其他尖括号定位标签原样，确保 CLI 能找到受管范围。
- 不在 agent context 嵌入大型生成清单。链接 canonical docs 或检查实时文件。
- 结构性源码变化后，更新 developer docs 并搜索 stale references。

#### Adapter And API Boundaries

- 同名 adapter API 可能返回不同形状。OneBot V11 API 常返回 `dict`；写访问模式前检查已安装 adapter 源码。
- deprecated Milky、QQ、OneBot V12 源码已从项目中彻底移除，包括所有按需加载工具。
- OneBot V11 群 `event.get_session_id()` 可能同时包含群和用户 ID。群级历史必须用 `group_id` 作为 `conversation_id`。
- OneBot V11 图片 API 变更前，先用当前 adapter 和 NapCat 文档确认 file field 格式。
- WSL2 + Docker Desktop bind mount 要求 WSL 发行版根目录必须加入 Docker Desktop File Sharing 白名单。漏配时容器内 bind 目标是空目录，但 `docker inspect` 仍报源路径正确。判断方法：`docker exec <ctr> mount | grep <src>`，出现 `fuse.bind` 或纯 `bind` 是正常；`overlay`（lower=`/tmp/docker-desktop-root-ro`）说明桥接层返回了空视图。修法：在 Docker Desktop → Settings → Resources → File sharing 加 `\\wsl.localhost\<distro>\`（旧版 WSL 写 `\\wsl$\<distro>\`），点 **Apply & restart** 后重建容器。Windows 侧 docker daemon 不会通过普通 bind 看到 WSL 路径；WSL Integration 与 File Sharing 是两个独立开关，不能假设"已经开了"。

#### Testing And Typing

- 修改函数签名时，grep 所有调用方，更新 fixtures，并运行 Ruff、Pyright、ty、pytest。
- gettext-heavy handler 中不要用 `_` 当临时变量覆盖 gettext helper。
- 测试中的 side-effect exception 必须匹配生产代码 `except` 分支。
- NoneBot event narrowing 使用 `isinstance(event, GroupMessageEvent)`。
- 按真实 API shape mock adapter 返回值。
- `assert_called_once_with()` 是精确匹配；optional kwargs 用 `mock.call_args.kwargs` 检查存在性。

#### Docs Site And Frontend

- `eslint-plugin-react@7.x` 与 ESLint 10 不兼容；pin ESLint 9 或迁移到 `@eslint-react/eslint-plugin`。
- `eslint-plugin-mdx@3.8.1` 通过三层配置集成 MDX lint 到 `apps/docs/eslint.config.mjs`：`mdx.flat`（解析器 + `mdx/*` 规则）、`mdx.createRemarkProcessor({ lintCodeBlocks: true })`（代码块 lint）、`mdx.flatCodeBlocks`（代码块规则）。`peerDependencies: { eslint: ">=8.0.0" }` 与 ESLint 10 兼容。代码块规则 MUST 关闭所有 `react/*` 与 `@next/*` 规则（通过 `files: ['**/*.{md,mdx}/**']` 收窄范围），避免 `vercel/next.js#89764` 的 `TypeError: contextOrFilename.getFilename is not a function` 在虚拟文件上崩溃。`.remarkrc.json` MUST 将 `remark-frontmatter` 排在 lint 预设之前，否则 frontmatter 的 `---` 分隔符会被误判为 setext H2 下划线，产生 `remark-lint-heading-style` 假阳性（基线 306 条 warning，添加 `remark-frontmatter` 后全部消除）。双 markdown linter 政策：`markdownlint-cli2` 覆盖 `.md`；`eslint-plugin-mdx` 覆盖 `.mdx`（无重叠）。pre-commit hook 使用独立 `HAS_DOCS_MDX` flag（通过 `^apps/docs/.*\.mdx$` 匹配），CI 使用独立 `frontend-mdx` 输出 flag，均收窄范围以避免 `.json` 内容变更误触发 ESLint。
- MDX 表格 cell 不能在 inline code 中包含裸 `|`，例如 `<群号|群名称>`；改用 `<群号或群名称>`。
- Fumadocs link validation 中，root index pages 的相对链接需要改为 absolute URLs。
- 导入 `src/lib/source.ts` 的 Vitest 测试需要 mock `collections/server`。
- 测试需要导入的共享函数应从 component file 中抽到独立模块。
- Component file 导出 utility 可能破坏 React Fast Refresh；移到非 component module。
- `/llms.txt` 是 route handler；内部链接使用 Next.js `Link`。
- Docker 服务不要占用 Playwright webServer 的 `3100` 端口；使用 `6100:3000` 等 CI 范围外端口。
- `next typegen` 在首次 `fumadocs-mdx` 之后可能把 `apps/docs/.source/server.ts`（和 `browser.ts`）清空为 0 字节。`docs:check-types` 脚本 MUST 在 `next typegen` 之后再跑一次 `fumadocs-mdx` 以重新填充 collections 导出，否则 `tsc --noEmit` 会报 `TS2305: Module '"collections/server"' has no exported member 'docs'`。使用 `fumadocs-mdx && next typegen && fumadocs-mdx && tsc --noEmit`。

#### Database And Runtime Files

- 所有数据访问通过 `nonebot_plugin_orm` 和 `database/orm_crud/`；不要重新引入自定义 engine management。
- 文件转 package 需要在 `__init__.py` 显式 re-export。
- Alembic model package 必须 import 所有 models，保证 discovery 生效。
- 非 SQLite 测试前先运行 migrations。
- `ensure_json5_dict_file_async()` 只创建缺失文件；覆盖写入用 `write_json5_dict_file_async()`。
- Runtime config defaults 必须 JSON-serializable；需要时用 Pydantic `mode="json"` dump。

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

#### Hooks, CI, And GitHub

- Windows 下 Bash hooks 可能找到不可直接运行的 `.cmd` shim。Windows Node shim 通过 `cmd.exe /c` 执行。
- Hook 中不要吞掉 `git diff --cached` 失败。
- 机械性问题优先用 CLI auto-fix：Ruff fix/format、markdownlint `--fix`、ESLint `--fix`、Prek。
- Markdownlint 配置集中在 `.markdownlint-cli2.jsonc`；调用点应依赖该配置。
- PowerShell markdownlint 优先 `pwsh.exe -NoProfile`，避免临时手写 quoted globs。
- GitHub Actions pin 到 commit SHA，不 pin annotated tag object SHA。
- Workflow 文件名使用 emoji-prefix + kebab-case，workflow `name:` 使用英文并匹配 emoji。
- `.github` YAML 注释使用英文；移除空的/损坏的 schema comment。
- `git push origin --delete` 前用 `git ls-remote` 检查远端分支是否存在。
- CI 工作流按领域拆分：`🧪-python.yml`（Python 静态分析 + 多数据库测试矩阵 + auto-format）、`🧪-frontend.yml`（docs lint/type/test/links）、`📚-docs.yml`（docs 部署）。共享的变更检测位于 `.github/actions/detect-changes` 复合 action（输出 python/markdown/frontend-* 标志）。标准触发约定：PR 仅跑检查（不提交/部署）；push 到 `main`/`dev` 跑检查 + auto-format + 部署。每个工作流有独立的 concurrency group 以避免互相取消。
- Python CI 的 Static Analysis job 使用 `uv sync --no-dev --group lint --group git --frozen` + `UV_NO_SYNC=1` 来只安装 lint/format 所需的最小依赖集（ruff、pyright、ty、prek），避免安装 test 组中包含的数据库驱动（mariadb、aioodbc）——这些驱动需要系统级库，在极简 CI 环境中可能构建失败。任何不需要运行测试的 CI job 都可使用此模式。

#### Pending Rollbacks

| What | Where | Why | Rollback condition |
| --- | --- | --- | --- |
| `deslop/unused-export: "off"` | `doctor.config.ts` | `useMDXComponents` 是框架要求 re-export，但当前未消费 | `useMDXComponents` 被实际消费后移除 |
| React Doctor CLI instead of action | `.github/workflows/🩺-react-doctor.yml` | 上游 action 有 detached HEAD 和 ANSI 泄漏问题 | 上游发布修复后切回 action |
