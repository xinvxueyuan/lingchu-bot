# Lingchu Bot

> [English](README.md) | 中文

[![CI](https://github.com/xinvxueyuan/lingchu-bot/actions/workflows/%F0%9F%A7%AA-python.yml/badge.svg)](https://github.com/xinvxueyuan/lingchu-bot/actions/workflows/%F0%9F%A7%AA-python.yml)
[![PyPI](https://img.shields.io/pypi/v/nonebot-plugin-lingchu-bot)](https://pypi.org/project/nonebot-plugin-lingchu-bot/)
[![Downloads](https://img.shields.io/pypi/dm/nonebot-plugin-lingchu-bot)](https://pypi.org/project/nonebot-plugin-lingchu-bot/)
[![Image size](https://ghcr-badge.egpl.dev/xinvxueyuan/lingchu-bot/size)](https://github.com/xinvxueyuan/lingchu-bot/pkgs/container/lingchu-bot)
[![License](https://img.shields.io/github/license/xinvxueyuan/lingchu-bot)](LICENSE-code)
[![Python](https://img.shields.io/badge/python-3.13-blue)](pyproject.toml)
[![NoneBot2](https://img.shields.io/badge/NoneBot2-2.x-orange)](https://nonebot.dev/)
[![Docs](https://img.shields.io/badge/docs-lingchu.zone.id-brightgreen)](https://lingchu.zone.id/)
[![Gitmoji](https://img.shields.io/badge/gitmoji-%20%F0%9F%98%9C%20%F0%9F%98%8D-FFDD67.svg?style=flat-square)](https://gitmoji.dev/)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot?ref=badge_shield)

**Lingchu Bot** 是一个由 NoneBot2 驱动的应用侧群组管理机器人。当前重点是基于 OneBot V11 的 QQ 群管理，同时保留可在后续演进为更完整跨平台工作流的插件、平台注册表、配置、存储、权限和文档结构。

[![Zread 问答][zread-shield]][zread-link]

[![DeepWiki 问答][deepwiki-shield]][deepwiki-link]

## 项目状态

Lingchu Bot 已发布首个 `0.0.1` 正式版本。项目在 `1.0.0` 前仍可能出现破坏性变更，但当前版本应可安装、可查阅文档，并可通过发布流程复现。

常用入口：

- [在线文档](https://lingchu.zone.id/)
- [用户指南概览](apps/docs/content/docs/user-guide/overview.zh.mdx)
- [快速开始](apps/docs/content/docs/user-guide/quick-start.zh.mdx)
- [QQ 命令参考](apps/docs/content/docs/platforms/qq/command-reference.zh.mdx)
- [架构指南](apps/docs/content/docs/developer-guide/architecture/introduction.zh.mdx)
- [贡献指南](CONTRIBUTING.md)

## 仓库内容

- `nonebot-plugin-lingchu-bot`：`pyproject.toml` 声明的 Python 包。
- `src/plugins/nonebot_plugin_lingchu_bot`：核心 NoneBot 插件，包含插件元数据、启动钩子、平台注册表、命令处理器、权限、i18n、仓储层和存储辅助能力。
- `pyproject.toml` 的 `[tool.nonebot]`：本地插件加载配置、已安装适配器声明和依赖插件声明。
- `apps/docs`：基于 Next.js / Fumadocs 的中英双语文档站。
- `Dockerfile` / `docker-compose.yml`：容器运行流程。镜像构建阶段会通过 `nb-cli` 生成 `/tmp/bot.py`；仓库根目录当前不提交本地 `bot.py`。
- `scripts/setup.sh`：本地开发用跨平台初始化脚本。

## 能力矩阵

| 能力 | 说明 |
| --- | --- |
| 成员管理 | 禁言、解禁、踢出、拉黑、删黑、清空黑名单、拉白和删白。 |
| 发言管理 | 成员禁言/解禁、全体禁言/解禁、最近消息撤回。 |
| 群聊操作 | 设置群名称、在实现支持时设置群头像、设置群名片/头衔/管理员、在实现支持时发送群公告、退出当前群。 |
| 远程管理 | 按群号或群名称模糊匹配操作其他群，包含远程禁言/解禁、全体禁言/解禁、踢出、拉黑/删黑和公告。 |
| 机器人控制 | `闭嘴` / `说话` 抑制或恢复反馈消息但不影响命令执行；`开机` / `关机` 启用或停用命令处理器。 |
| 菜单系统 | `菜单` / `menu` 按当前平台、协议和实现过滤后列出可用子菜单。 |
| 运行配置 | localstore 配置目录下的插件专属 TOML 文件，并可由更高优先级的 NoneBot / 环境变量覆盖。 |
| 权限与保护 | UID 超级用户、平台账号映射、命令授权、平台运行时角色透传、黑名单和受保护目标拦截。 |
| 消息存储与 API 审计 | 可选记录事件、处理状态、Bot 生命周期和平台 API 调用摘要。 |
| 运行时 i18n | 基于 gettext / Babel 的简体中文与英文反馈文本目录。 |
| LLM 服务 | 托管 OpenAI / LiteLLM profile，并提供稳定接口和提供商原生接口。 |
| 调度器 | 通过 `nonebot-plugin-apscheduler` 的周期任务与清理。 |

其他平台和非群管理能力以后续实现和测试为准。

## 适配器支持

当前已实现的平台 profile 是 **QQ**，唯一处于启动流程中的适配器是 **OneBot V11**：

```dotenv
LINGCHUAdapter=~onebot.v11
```

未设置 `LINGCHUAdapter` 时，Lingchu 默认选择 `~onebot.v11`。被选中的适配器也必须已由 NoneBot 加载并注册，否则启动会以明确的"适配器未加载"错误失败。

当前仅实现 OneBot V11。配置任何其他适配器 ID（如 `~milky`、`~qq`、`~onebot.v12`）都会以 `PlatformAdapterUnknownError` 启动失败。同一平台配置多个已知适配器会触发 `PlatformAdapterConflictError`。

OneBot V11 目前有 `default` 和 `NapCat` 两条实现路径。部分功能会按实现能力显示或隐藏：例如群公告、群头像只在当前实现支持时展示；远程公告要求 `NapCat.Onebot >= 4.18.0`。

## 快速开始

### 环境要求

- Python 3.13（`pyproject.toml` 要求 `>=3.12, <4.0`；目标版本 3.13）
- `uv`
- Git
- 可用的 NoneBot 运行环境，以及 OneBot V11 连接与账号配置
- Node.js 22+ 和 pnpm，用于 docs / 前端工作区和完整初始化脚本

### 方式 A — 通过 NB-CLI 安装（推荐）

```bash
nb plugin install nonebot-plugin-lingchu-bot
```

这会从 PyPI 安装已发布的包并注册到 NoneBot。安装后，将 `nonebot_plugin_lingchu_bot` 添加到 NoneBot 插件列表，或让 NB-CLI 自动管理。

### 方式 B — 作为本地插件目录使用

克隆仓库并初始化：

```bash
git clone https://github.com/xinvxueyuan/lingchu-bot.git
cd lingchu-bot
chmod +x scripts/setup.sh
./scripts/setup.sh
```

初始化脚本会检测操作系统和工具链、安装 Python 与 Node.js 依赖、生成环境文件、配置 Git hooks，并可选安装 Playwright 浏览器。

手动替代方式：

```bash
uv sync --frozen
pnpm install
pnpm exec husky
cp .env.example .env
```

如需从已有 NoneBot 项目加载 Lingchu Bot，将 `plugin_dirs` 指向克隆后的 `src/plugins` 目录：

```toml
# 在目标 NoneBot 项目的 pyproject.toml 中
[tool.nonebot]
plugin_dirs = ["path/to/lingchu-bot/src/plugins"]
```

### 方式 C — 在 Docker 中运行

```bash
# docker-compose.yml 读取 .env.prod；请先按部署环境创建它。
cp .env.example .env.prod
docker compose up --build
```

连接真实平台前，请准备好 NoneBot 与所用 OneBot V11 实现所需的账号、网络、反向 WebSocket / HTTP 配置和权限。

## 配置

Lingchu 首次启动时会在 `nonebot-plugin-localstore` 提供的插件配置目录中创建 `config.toml`。运行时配置优先级为：

1. 操作系统环境变量
2. NoneBot dotenv / 全局配置
3. `config.toml`
4. 代码默认值

下表枚举 `core/config.py` 与 `core/runtime_config.py` 实际读取的环境变量。NoneBot `.env` 文件中的布尔值必须使用 JSON 风格小写 `true` / `false`，不要写 Python 风格的 `True` / `False`。

| 分组 | 设置项 | 用途 |
| --- | --- | --- |
| NoneBot 核心 | `HOST`、`PORT` | NoneBot 服务器监听地址与端口。 |
| NoneBot 核心 | `NICKNAME` | 机器人昵称。 |
| NoneBot 核心 | `LOG_LEVEL` | NoneBot 日志级别。 |
| NoneBot 核心 | `COMMAND_START`、`COMMAND_SEP` | NoneBot 命令解析 token。 |
| NoneBot 核心 | `FASTAPI_DOCS_URL`、`FASTAPI_REDOC_URL` | FastAPI 文档端点；生产环境应禁用。 |
| 容器检测 | `IN_CONTAINERS` | 机器人是否运行在容器内（`config.in_containers`）。 |
| Lingchu 运行时 | `LINGCHUAdapter` / `LINGCHU_ADAPTER` | 选择启用适配器；当前支持值为 `~onebot.v11`。 |
| Lingchu 运行时 | `LINGCHU_SUPERUSERS` | Lingchu 超级用户的 UID 到平台账号映射。 |
| Lingchu 运行时 | `LINGCHU_LOCALE` | 运行时语言；可用目录为 `zh_CN` 和 `en_US`。 |
| Lingchu 运行时 | `SUPERUSER_KEY` | 超级用户密钥字符串（`superuser_key`）。 |
| Localstore | `LOCALSTORE_USE_CWD` | 为 true 时将 localstore 数据/配置/缓存放到项目目录下。 |
| 消息存储 | `MESSAGE_STORE_ENABLED` | 是否启用消息存储运行时钩子。 |
| 消息存储 | `MESSAGE_STORE_RETENTION_DAYS` | 消息记录保留天数；`0` 禁用基于天数的过期。 |
| 消息存储 | `MESSAGE_STORE_SUMMARY_LIMIT` | 文本、数据和结果摘要的最大长度。 |
| 消息存储 | `MESSAGE_STORE_RECORD_API_CALLS` | 是否记录平台 API 调用摘要。 |
| 消息存储 | `MESSAGE_STORE_CLEANUP_ENABLED` | 是否启用过期消息清理。 |
| 撤回 | `RECALL_MESSAGE_DEFAULT_COUNT` | 消息撤回命令省略数量时的默认条数（`1`–`100`）。 |
| 权限 | `PERMISSION_PLATFORM_RUNTIME_PASSTHROUGH` | 是否允许 QQ 群主/管理员/成员等平台角色满足 Lingchu 命令授权。 |
| 触发词覆盖 | `COMMAND_TRIGGER_OVERRIDES` | 按 command key 覆盖命令主触发词和别名。 |
| 触发词覆盖 | `MENU_PAGE_TRIGGER_OVERRIDES` | 按菜单页 id 覆盖菜单页触发词。 |
| 受保护目标 | `PROTECTED_SUBJECT_FEATURE_KEYS` | 目标用户受保护时会被拦截的副作用命令键。 |
| 数据库 | `SQLALCHEMY_DATABASE_URL` | SQLAlchemy 数据库 URL；支持 SQLite / PostgreSQL / MySQL / MariaDB / Oracle / SQL Server。未设置时使用默认 SQLite。 |
| 数据库 | `ALEMBIC_STARTUP_CHECK` | 生产环境设为 `true` 以在启动时强制 schema 迁移检查。 |
| LLM 服务 | `LINGCHU_AI_PROVIDER` | 旧版/默认 LLM 后端：`litellm` 或 `openai`。 |
| LLM 服务 | `LINGCHU_AI_MODEL` | 旧版/默认模型 id（`gpt-4o-mini`）。 |
| LLM 服务 | `LINGCHU_AI_BASE_URL` | 旧版/默认 OpenAI 兼容 Base URL。 |
| LLM 服务 | `LINGCHU_AI_TIMEOUT` | 旧版/默认请求超时秒数。 |
| LLM 服务 | `LINGCHU_AI_API_KEY` | 旧版/默认 API 密钥；profile 应优先使用 `api_key_env`。 |
| 公告图片 | `ANNOUNCEMENT_IMAGE_CACHE_DIR` | 公告图片的宿主侧缓存目录（默认为 localstore cache）。 |
| 公告图片 | `ANNOUNCEMENT_IMAGE_PROTOCOL_DIR` | NapCat 在容器内看到的协议侧目录。 |

`config.toml` 示例：

```toml
#:schema ./config.schema.json
superuser_key = "123456789abcdef"
message_store_enabled = true
message_store_retention_days = 30
message_store_summary_limit = 500
message_store_record_api_calls = true
message_store_cleanup_enabled = true
ai_provider = "litellm"
ai_model = "gpt-4o-mini"
ai_timeout = 60.0
recall_message_default_count = 10
permission_platform_runtime_passthrough = true
protected_subject_feature_keys = ["kick_member", "member_mute", "recall_message", "block_member"]
lingchu_adapter = "~onebot.v11"
```

TOML 没有 `null`；可选字段应省略，以使用其 `None` 默认值。旧 `.json5`
文件不会被读取或迁移。

### 托管 LLM profile

Lingchu 还会在插件配置目录创建 `llm.toml`。非空 `[profiles]` 表的优先级高于
`config.toml` 中旧版 `ai_*` 字段；空表则继续把旧字段作为隐式 `default`
profile。使用 `api_key_env` 指定环境变量名，避免把凭据写入 TOML：

```toml
#:schema ./llm.schema.json
default_profile = "primary"

[profiles.primary]
backend = "openai"
model = "gpt-4o-mini"
api_key_env = "OPENAI_API_KEY"
litellm_generation = "responses"
timeout = 60
max_retries = 2

[profiles.compatible]
backend = "litellm"
model = "openai/gpt-4o-mini"
api_key_env = "OPENAI_API_KEY"
litellm_generation = "chat"

[router]
enabled = false
strategy = "simple-shuffle"
num_retries = 2
```

OpenAI profile 的稳定生成接口使用 Responses。LiteLLM profile 通过
`litellm_generation` 选择 `responses` 或 `chat`；启用 `[router]` 后，受信任的
内部调用方可以使用 LiteLLM 进程内 Router。托管运行时也直接暴露原生
`AsyncOpenAI` 客户端、LiteLLM 模块和原生 Router，因此提供商专属资源或 SDK
新接口不必等待 Lingchu 增加包装层。

能力探测有 `supported`、`unsupported`、`unknown` 三种结果，仅作为提示；
`unknown` 不会阻止显式原生调用。重新加载时会先对候选 profile 做结构校验并冻结，
再原子替换旧运行时；凭据按 profile 延迟解析。失败时旧版本继续工作，成功后关闭
退役客户端并清空能力缓存。

自定义 `base_url` 默认拒绝回环、链路本地、云元数据地址及其他私有 IP 字面量，
只有设置 `allow_private_network = true` 才会放行。凭据默认不会发往自定义 Base
URL，只有设置 `allow_credentials_to_custom_base_url = true` 才会放行。这两个
选项表示明确接受信任边界，并非推荐配置；部署侧仍须在网络层校验 DNS 解析和
重定向。系统合成的隐式旧版 profile 会把已有旧 URL/密钥对视为旧版授权，显式
profile 不继承该例外。稳定接口的 `provider_options` 会拒绝凭据、端点、回调、
日志器、重试和 Router 控制键。Lingchu 可以透传工具定义和原生结果，但绝不会自动
执行模型请求的工具。

## 命令速览

主菜单：

```text
菜单
menu
```

默认子菜单页：

- `成员管理` / `member-management`
- `发言管理` / `speech-management`
- `群聊管理` / `group-chat-management`
- `远程管理` / `remote-management`
- `系统管理` / `system-management`

示例：

```text
禁言 @用户 [时长秒数] [原因]
mute @user [duration seconds] [reason]

撤回 [@用户] [数量]
recall [@user] [count]

远程禁言 <群号或群名称> @用户 [时长秒数] [原因]
remote-mute <group_id_or_group_name> @user [duration seconds] [reason]

闭嘴 / 说话
silence / speak

开机 / 关机
boot / shutdown
```

命令触发词按 locale 互斥选择。中文 locale 启用中文触发词，英文 locale 启用短横线风格英文触发词；两种语言不会同时启用。完整命令行为、权限预检、实现过滤和远程管理细节见 [QQ 命令](apps/docs/content/docs/platforms/qq/command-reference.zh.mdx)。

## 开发与验证

CI 会检查 Ruff、Markdown、Pyright、ty、多数据库 pytest 以及文档站 lint / test。提交前请运行与改动相关的检查。

Ruff：

```bash
uv run -m ruff check . --output-format=github
uv run -m ruff format --check .
```

类型检查：

```bash
uv run -m pyright
uv run -m ty check --output-format github
```

Python 测试：

```bash
uv run -m pytest

# 可选多数据库测试：
# SQLALCHEMY_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/postgres" uv run -m pytest
# SQLALCHEMY_DATABASE_URL="mysql+aiomysql://mysql:mysql@localhost:3306/mymysql" uv run -m pytest
```

文档站：

```bash
pnpm --filter docs lint
pnpm --filter docs test
pnpm turbo run build --filter=docs
```

运行时 i18n 目录：

```bash
task i18n
```

Markdown：

```bash
pnpm exec markdownlint-cli2 README.md README-zh.md
```

## 贡献

欢迎提交 Issue、测试、文档和代码改进。开始前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)，其中包含当前协作流程、GitNexus 影响分析要求、版本验证系统和 PR 检查清单。

参与讨论和审查时，请遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。安全相关问题请参考 [SECURITY.md](SECURITY.md)。

## 许可

本项目采用**分阶段开源许可证栈**（切换规则与触发日详见
[Repository-Policy.md](Repository-Policy.md)）：

- **当前阶段** — 代码：`LGPL-3.0-or-later`
  （[`LICENSE-code`](LICENSE-code)）。文档：`GFDL-1.3-or-later`
  （[`LICENSE-docs`](LICENSE-docs)）。视觉元素：`CC0-1.0`
  （[`LICENSE-cc0`](LICENSE-cc0)）。
- **未来阶段**（在首次公开发行后一年 或 首次主版本变更中较早发生者
  自动触发）— 代码：`MIT OR Apache-2.0`（双许可证，用户自选；见
  [`LICENSE-mit`](LICENSE-mit) 与 [`LICENSE-apache`](LICENSE-apache)）。
  文档与视觉元素：`CC-BY-SA-4.0-or-later`
  （[`LICENSE-cc-by-sa`](LICENSE-cc-by-sa)）。

提交贡献即表示您接受 [CLA.md](CLA.md) 的条款，该协议授予本项目执行
上述切换所需的权利。切换仅作用于触发日（含）之后提交的贡献；触发日
之前提交的贡献继续适用其提交当时生效的许可证。

媒体文件处理、脱敏要求、REUSE 合规以及官方许可证文本，请参见
[Repository-Policy.md](Repository-Policy.md) 与仓库根目录下的
[`LICENSE-*`](LICENSE-code) 系列文件。

## 致谢

Lingchu Bot 建立在许多优秀开源项目之上。特别感谢这些上游项目与社区：

- **机器人运行时与适配器生态**：[NoneBot2](https://nonebot.dev/)、[nonebot-adapter-onebot](https://github.com/nonebot/adapter-onebot)、`nonebot-plugin-alconna`、`nonebot-plugin-localstore`、`nonebot-plugin-orm`、`nonebot-plugin-apscheduler`、`nonebot-plugin-htmlkit` 和 `nonebot-plugin-docs`。
- **Python 配置、存储与服务工具**：`aiofiles`、`toml`、`rtoml`、`jsonschema`、[Babel](https://babel.pocoo.org/)、[Jinja](https://jinja.palletsprojects.com/)、[Typer](https://typer.tiangolo.com/)、[Arrow](https://arrow.readthedocs.io/)、`psutil`、[OpenAI Python SDK](https://github.com/openai/openai-python) 和 [LiteLLM](https://github.com/BerriAI/litellm)。
- **文档站与前端栈**：[Fumadocs](https://fumadocs.dev/)、[Next.js](https://nextjs.org/)、[React](https://react.dev/)、[Mermaid](https://mermaid.js.org/)、[Twoslash](https://twoslash.netlify.app/)、`flexsearch`、`d3-force`、`dompurify`、`feed` 和 [Tailwind CSS](https://tailwindcss.com/)。
- **工程质量、测试与仓库工作流**：[uv](https://docs.astral.sh/uv/)、[pnpm](https://pnpm.io/)、[Turborepo](https://turbo.build/repo)、[Ruff](https://docs.astral.sh/ruff/)、[Pyright](https://microsoft.github.io/pyright/)、[ty](https://docs.astral.sh/ty/)、[pytest](https://docs.pytest.org/)、[Vitest](https://vitest.dev/)、[Playwright](https://playwright.dev/)、[markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2)、[Prettier](https://prettier.io/)、[ESLint](https://eslint.org/)、[Husky](https://typicode.github.io/husky/)、[Gitmoji](https://gitmoji.dev/)、`gitnexus` 和 [FOSSA](https://fossa.com/)。

完整依赖列表请以 [pyproject.toml](pyproject.toml)、[package.json](package.json)、[apps/docs/package.json](apps/docs/package.json) 和 [uv.lock](uv.lock) 为准。

## 许可证合规

[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot?ref=badge_large)

[zread-shield]: https://img.shields.io/badge/Ask_Zread-_.svg?color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff

[deepwiki-shield]: https://deepwiki.com/badge.svg

[zread-link]: https://zread.ai/xinvxueyuan/lingchu-bot

[deepwiki-link]: https://deepwiki.com/xinvxueyuan/lingchu-bot
