<!-- markdownlint-disable MD033 MD013 -->
# Lingchu Bot

> [English](README.md) | 中文

[![License](https://img.shields.io/github/license/xinvxueyuan/lingchu-bot)](LICENSE-code)
[![Release](https://img.shields.io/github/v/release/xinvxueyuan/lingchu-bot)](https://github.com/xinvxueyuan/lingchu-bot/releases)
[![Python](https://img.shields.io/badge/python-3.13-blue)](pyproject.toml)
[![NoneBot2](https://img.shields.io/badge/NoneBot2-2.x-orange)](https://nonebot.dev/)
[![Docs](https://img.shields.io/badge/docs-lingchu.zone.id-brightgreen)](https://lingchu.zone.id/)
[![Gitmoji](https://img.shields.io/badge/gitmoji-%20%F0%9F%98%9C%20%F0%9F%98%8D-FFDD67.svg?style=flat-square)](https://gitmoji.dev/)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot?ref=badge_shield)

Lingchu Bot 是一个由 NoneBot2 驱动的应用侧管理机器人项目。当前重点是基于 OneBot V11 的 QQ 群管理，同时保留插件、平台注册表、配置、存储、权限和文档站结构，方便后续演进为更完整的跨平台工作流。

[![Zread 问答][zread-shield]][zread-link]

[![DeepWiki 问答][deepwiki-shield]][deepwiki-link]

## 项目状态

Lingchu Bot 仍处于 **pre-alpha / development** 阶段。代码、配置、命令行为、存储结构和文档仍可能继续调整。README 主要用于快速了解项目；当前行为请以源码和 docs 为准。

推荐入口：

- [在线文档](https://lingchu.zone.id/)
- [用户指南概览](apps/docs/content/docs/user-guide/overview.zh.mdx)
- [快速开始](apps/docs/content/docs/user-guide/quick-start.zh.mdx)
- [QQ 命令参考](apps/docs/content/docs/platforms/qq/command-reference.zh.mdx)
- [架构指南](apps/docs/content/docs/developer-guide/architecture/introduction.zh.mdx)
- [贡献指南](CONTRIBUTING.md)

## 仓库里有什么

- `nonebot-plugin-lingchu-bot`：`pyproject.toml` 声明的 Python 包。
- `src/plugins/nonebot_plugin_lingchu_bot`：核心 NoneBot 插件，包含插件元数据、启动钩子、平台注册表、命令处理器、权限、i18n、仓储层和存储辅助能力。
- `pyproject.toml` 的 `[tool.nonebot]`：本地插件加载配置、已安装适配器声明和依赖插件声明。
- `apps/docs`：基于 Next.js / Fumadocs 的中英双语文档站。
- `Dockerfile` / `docker-compose.yml`：容器运行流程。镜像构建阶段会通过 `nb-cli` 生成 `/tmp/bot.py`；仓库根目录当前不提交本地 `bot.py`。
- `scripts/setup.sh`：本地开发用跨平台初始化脚本。

## 当前能力

当前用户侧能力集中在 QQ 群管理命令：

- **成员管理**：禁言、解禁、踢出、拉黑、删黑、清空黑名单、拉白和删白。
- **发言管理**：成员禁言/解禁、全体禁言/解禁、最近消息撤回。
- **群聊操作**：设置群名称、在实现支持时设置群头像、设置群名片/头衔/管理员、在实现支持时发送群公告、退出当前群。
- **远程管理**：按群号或群名称模糊匹配操作其他群，包含远程禁言/解禁、远程全体禁言/解禁、远程踢出、远程拉黑/删黑和远程公告。
- **机器人控制**：`闭嘴` / `说话` 控制反馈消息发送但不影响命令执行；`开机` / `关机` 控制命令处理器是否启用。
- **菜单系统**：`菜单` / `menu` 会按当前平台、协议和实现过滤后列出可用子菜单。
- **运行配置**：插件专属 JSON5 配置文件位于 localstore 配置目录，并可由更高优先级的 NoneBot / 环境变量覆盖。
- **权限与保护**：UID 超级用户、平台账号映射、命令授权、平台运行时角色透传、黑名单和受保护目标拦截。
- **消息存储与 API 审计**：可选记录事件、处理状态、Bot 生命周期和平台 API 调用摘要。
- **运行时 i18n**：基于 gettext/Babel 的简体中文与英文反馈文本目录，通过 `LINGCHU_LOCALE`、`lc_locale` 或 `locale` 选择。

其他平台和非群管理能力以后续实现和测试为准。

## 适配器支持

当前已实现的平台 profile 是 **QQ**，唯一处于启动流程中的适配器是 **OneBot V11**：

```dotenv
LINGCHUAdapter=~onebot.v11
```

未设置 `LINGCHUAdapter` 时，Lingchu 默认选择 `~onebot.v11`。被选中的适配器也必须已经由 NoneBot 加载并注册，否则启动会以明确的“适配器未加载”错误失败。

以下已停维适配器已从启动流程移除：

- `~milky`
- `~qq`
- `~onebot.v12`

配置任何已移除适配器都会快速失败并抛出 `PlatformAdapterDeprecatedError`。同一平台配置多个已知适配器会触发 `PlatformAdapterConflictError`。配置 Lingchu 未实现或无法识别的适配器会导致启动失败。

OneBot V11 目前有 `default` 和 `NapCat` 两条实现路径。部分功能会按实现能力显示或隐藏：例如群公告、群头像只在当前实现支持时展示；远程公告要求 `NapCat.Onebot >= 4.18.0`。

## 快速开始

### 环境要求

- Python 3.13（`pyproject.toml` 要求 `>=3.13, <3.14`）
- `uv`
- Git
- 可用的 NoneBot 运行环境，以及 OneBot V11 连接与账号配置
- Node.js 20+ 和 pnpm 9+，用于完整初始化脚本和 docs/frontend 工作区

### 克隆并初始化

```bash
git clone https://github.com/xinvxueyuan/lingchu-bot.git
cd lingchu-bot
chmod +x scripts/setup.sh
./scripts/setup.sh
```

初始化脚本会检测操作系统和工具链、安装 Python 与 Node.js 依赖、生成环境文件、配置 Git hooks，并可选安装 Playwright 浏览器。

手动安装方式：

```bash
uv sync --frozen
pnpm install
pnpm exec husky
cp .env.example .env
```

### 选择运行方式

把 Lingchu Bot 作为本地插件目录加载到已有 NoneBot 项目：

```toml
# 在目标 NoneBot 项目的 pyproject.toml 中
[tool.nonebot]
plugin_dirs = ["path/to/lingchu-bot/src/plugins"]
```

或使用容器运行：

```bash
# docker-compose.yml 当前读取 .env.prod；请先按部署环境创建它。
cp .env.example .env.prod
docker compose up --build
```

连接真实平台前，请准备好 NoneBot 与所用 OneBot V11 实现所需的账号、网络、反向 WebSocket / HTTP 配置和权限。

## 核心配置

Lingchu 首次启动时会在 `nonebot-plugin-localstore` 提供的插件配置目录中创建 `config.json5`。运行时配置优先级为：

1. 操作系统环境变量
2. NoneBot dotenv / 全局配置
3. `config.json5`
4. 代码默认值

重要配置项：

| 配置项 | 用途 |
| --- | --- |
| `LINGCHUAdapter` / `LINGCHU_ADAPTER` | 选择启用适配器；当前支持值为 `~onebot.v11`。 |
| `LINGCHU_SUPERUSERS` | Lingchu 超级用户的 UID 到平台账号映射。 |
| `SUPERUSERS` | `LINGCHU_SUPERUSERS` 缺失或为 null 时的 QQ 账号 fallback。 |
| `LINGCHU_LOCALE` | 运行时语言；当前可用目录包括 `zh_CN` 和 `en_US`。 |
| `LOCALSTORE_USE_CWD` | 为 true 时将 localstore 数据/配置/缓存放到项目目录下。 |
| `MESSAGE_STORE_ENABLED` | 是否启用消息存储运行时钩子。 |
| `MESSAGE_STORE_RETENTION_DAYS` | 消息记录保留天数；`0` 禁用基于天数的过期。 |
| `MESSAGE_STORE_SUMMARY_LIMIT` | 文本、数据和结果摘要的最大长度。 |
| `MESSAGE_STORE_RECORD_API_CALLS` | 是否记录平台 API 调用摘要。 |
| `RECALL_MESSAGE_DEFAULT_COUNT` | 消息撤回命令省略数量时的默认条数。 |
| `PERMISSION_PLATFORM_RUNTIME_PASSTHROUGH` | 是否允许 QQ 群主/管理员/成员等平台角色满足 Lingchu 命令授权。 |
| `COMMAND_TRIGGER_OVERRIDES` | 按 command key 覆盖命令主触发词和别名。 |
| `MENU_PAGE_TRIGGER_OVERRIDES` | 按菜单页 id 覆盖菜单页触发词。 |
| `PROTECTED_SUBJECT_FEATURE_KEYS` | 目标用户受保护时会被拦截的副作用命令键。 |

`config.json5` 示例：

```json5
{
  "$schema": "config.schema.json5",
  superuser_key: "123456789abcdef",
  message_store_enabled: true,
  message_store_retention_days: 30,
  message_store_summary_limit: 500,
  message_store_record_api_calls: true,
  message_store_cleanup_enabled: true,
  recall_message_default_count: 10,
  permission_platform_runtime_passthrough: true,
  command_trigger_overrides: {},
  menu_page_trigger_overrides: {},
  protected_subject_feature_keys: ["kick_member", "member_mute", "recall_message", "block_member"],
  lingchu_adapter: "~onebot.v11",
  lingchu_superusers: null,
}
```

NoneBot `.env` 文件中的布尔值必须使用 JSON 风格小写 `true` / `false`，不要写 Python 风格的 `True` / `False`。

## 命令速览

主菜单：

```text
菜单
menu
```

默认子菜单：

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

CI 会检查 Ruff、Markdown、Pyright、ty、多数据库 pytest 和文档站 lint/test。提交前建议至少运行与本次改动相关的检查。

Ruff：

```bash
uv run -m ruff check . --output-format=github
uv run -m ruff format --check .
```

类型检查：

```bash
uv run -m pyright .
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

欢迎提交 Issue、测试、文档和代码改进。开始前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)，其中包含当前协作流程、GitNexus 影响分析要求和 PR 检查清单。

参与讨论和审查时，请遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。安全相关问题请参考 [SECURITY.md](SECURITY.md)。

## 许可

本项目采用**分阶段开源许可证栈**（切换规则与触发日详见
[Repository-Policy.md](Repository-Policy.md)）：

- **当前阶段** — 代码：[LGPL-3.0-or-later](LICENSE-code)。文档：
  [GNU FDL-1.3-or-later](LICENSE-docs)。视觉：
  [CC0-1.0](LICENSE-cc0)。
- **未来阶段**（在首次公开发行后一年 或 首次主版本变更中较早发生者
  自动触发）— 代码：[MIT-or-later](LICENSE-mit) 或
  [Apache-2.0-or-later](LICENSE-apache)（用户自选双许可证）。文档与
  视觉：[CC-BY-SA-4.0-or-later](LICENSE-cc-by-sa)。

提交贡献即表示您接受 [CLA.md](CLA.md) 的条款，该协议授予本项目执行
上述切换所需的权利。切换仅作用于触发日（含）之后提交的贡献；触发日
之前提交的贡献继续适用其提交当时生效的许可证。

媒体文件处理、脱敏要求以及官方许可证文本，请参见
[Repository-Policy.md](Repository-Policy.md) 与仓库根目录下的
[`LICENSE-*`](LICENSE-mit) 系列文件。

## 致谢

Lingchu Bot 建立在许多优秀开源项目之上。特别感谢这些上游项目与社区：

- **机器人运行时与适配器生态**：[NoneBot2](https://nonebot.dev/)、[nonebot-adapter-onebot](https://github.com/nonebot/adapter-onebot)、`nonebot-plugin-alconna`、`nonebot-plugin-localstore`、`nonebot-plugin-orm`、`nonebot-plugin-apscheduler`、`nonebot-plugin-htmlkit`、`nonebot-plugin-docs` 和 `nonebot-plugin-wait-a-minute`。
- **Python 配置、存储与服务工具**：`aiofiles`、`json5`、`rtoml`、`jsonschema`、[Babel](https://babel.pocoo.org/)、[Jinja](https://jinja.palletsprojects.com/)、[Typer](https://typer.tiangolo.com/)、[Arrow](https://arrow.readthedocs.io/)、`psutil` 和 [OpenAI Python SDK](https://github.com/openai/openai-python)。
- **文档站与前端栈**：[Fumadocs](https://fumadocs.dev/)、[Next.js](https://nextjs.org/)、[React](https://react.dev/)、[Mermaid](https://mermaid.js.org/)、[Twoslash](https://twoslash.netlify.app/)、[FlexSearch](https://github.com/nextapps-de/flexsearch)、[D3](https://d3js.org/)、[DOMPurify](https://github.com/cure53/DOMPurify)、[Feed](https://github.com/jpmonette/feed) 和 [Tailwind CSS](https://tailwindcss.com/)。
- **工程质量、测试与仓库工作流**：[uv](https://docs.astral.sh/uv/)、[pnpm](https://pnpm.io/)、[Turborepo](https://turbo.build/repo)、[Ruff](https://docs.astral.sh/ruff/)、[Pyright](https://microsoft.github.io/pyright/)、[ty](https://docs.astral.sh/ty/)、[pytest](https://docs.pytest.org/)、[Vitest](https://vitest.dev/)、[Playwright](https://playwright.dev/)、[markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2)、[Prettier](https://prettier.io/)、[ESLint](https://eslint.org/)、[Husky](https://typicode.github.io/husky/)、[Gitmoji](https://gitmoji.dev/)、`gitnexus` 和 [FOSSA](https://fossa.com/)。

完整依赖列表请以 [pyproject.toml](pyproject.toml)、[package.json](package.json)、[apps/docs/package.json](apps/docs/package.json) 和 [uv.lock](uv.lock) 为准。

## 许可证合规

[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot?ref=badge_large)

[zread-shield]: https://img.shields.io/badge/Ask_Zread-_.svg?color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff

[deepwiki-shield]: https://deepwiki.com/badge.svg

[zread-link]: https://zread.ai/xinvxueyuan/lingchu-bot

[deepwiki-link]: https://deepwiki.com/xinvxueyuan/lingchu-bot
