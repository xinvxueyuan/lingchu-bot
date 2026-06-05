# Lingchu Bot

[![License](https://img.shields.io/github/license/xinvxueyuan/lingchu-bot)](LICENSE-code)
[![Release](https://img.shields.io/github/v/release/xinvxueyuan/lingchu-bot)](https://github.com/xinvxueyuan/lingchu-bot/releases)
[![Python](https://img.shields.io/badge/python-3.13-blue)](pyproject.toml)
[![NoneBot2](https://img.shields.io/badge/NoneBot2-2.x-orange)](https://nonebot.dev/)
[![Docs](https://img.shields.io/badge/docs-lingchu.zone.id-brightgreen)](https://lingchu.zone.id/)
[![Gitmoji](https://img.shields.io/badge/gitmoji-%20%F0%9F%98%9C%20%F0%9F%98%8D-FFDD67.svg?style=flat-square)](https://gitmoji.dev/)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot?ref=badge_shield)

Lingchu Bot 是一个基于 NoneBot2 的应用侧管理机器人项目。它以插件形式组织核心能力，面向群管理、命令处理、配置管理、本地存储和异步数据访问等场景。

## 项目状态

本项目仍处于 pre-alpha / development 阶段。当前代码、配置、命令行为和文档都可能继续调整；请不要把现有接口视为稳定生产接口。

如果你想跟进设计和使用说明，请优先阅读：

- [在线文档](https://lingchu.zone.id/)
- [用户指南](apps/docs/content/docs/user-guide/overview.mdx)
- [开发指南](apps/docs/content/docs/developer-guide/introduction.mdx)
- [贡献指南](CONTRIBUTING.md)

## 项目定位

Lingchu Bot 当前仓库包含这些实际入口：

- `nonebot-plugin-lingchu-bot`：核心 NoneBot 插件，负责配置、启动流程、子插件加载和共享工具能力。
- `[tool.nonebot]`：`pyproject.toml` 中的 NoneBot 配置，声明本仓库插件目录、已安装适配器和依赖插件。
- `Dockerfile` / `docker-compose.yml`：容器运行入口，镜像构建阶段会通过 `nb-cli` 生成运行用 `/tmp/bot.py`。

插件元数据声明支持 OneBot V11/V12、Milky、Discord、Telegram 和 GitHub 等适配器；`pyproject.toml` 当前安装/配置 OneBot V11/V12、Milky 和 QQ 适配器。已实现并有测试覆盖的业务处理器以当前源码和测试为准。

## 功能概览

- 命令处理：基于 `nonebot-plugin-alconna` 组织命令解析。
- 当前已实现能力：以 Milky 群管理处理器为主，包含成员禁言、解禁、全体禁言/解禁、群资料设置、成员名片/头衔/管理员设置、群公告、踢人和退群。
- 后续扩展方向：项目结构保留多适配器与非群管理功能的扩展空间，可继续演进服务集成、定时任务、Web/API 能力和存储驱动工作流。
- 配置管理：通过 NoneBot 插件配置和 Pydantic 模型集中声明运行配置。
- 本地存储：使用 `nonebot-plugin-localstore` 管理数据、配置和缓存目录。
- 数据访问：提供 JSON5 存储工具和基于 `nonebot-plugin-orm` 的异步 CRUD 辅助能力。
- 子插件加载：核心插件会发现并加载项目内子插件，方便后续功能拆分。

## 快速开始

### 环境要求

- Python 3.13
- uv
- 可用的 NoneBot 运行环境
- Milky 适配器所需的连接与账号配置

### 安装依赖

```bash
uv sync --frozen
```

### 运行方式

当前工作树没有提交根目录 `bot.py`。本仓库以插件包和 NoneBot 配置为主：

- 如果集成到已有 NoneBot 项目，请按 `[tool.nonebot]` 中的 `plugin_dirs = ["src/plugins"]` 加载本地插件目录。
- 如果使用容器运行，请使用 Docker 构建流程；镜像会通过 `nb-cli` 生成运行用 `/tmp/bot.py`。
- 本地开发常用路径配置见 [.env.example](.env.example)，其中 `LOCALSTORE_USE_CWD=true` 会让 localstore 数据优先落在项目目录。

实际连接参数、机器人账号和平台侧配置请按 NoneBot、Milky 或目标适配器的文档准备。

## 开发与验证

CI 会检查 Ruff、Markdown、Pyright、ty、pytest 和文档站 lint/test。提交前建议至少运行与本次改动相关的检查。

本仓库同时包含一个 Turborepo 工作区，用于开发 Next.js 版文档站和前端包。文档站源码位于 [apps/docs](apps/docs/)，基于 [Fumadocs](https://fumadocs.dev/) 构建，支持中英双语、RSS 订阅、Mermaid 图表、Twoslash 代码悬停、EPUB 导出、LLM 友好文本（`/llms.txt`、`/llms-full.txt`）和文档关系图谱。

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
```

文档站 lint 与测试：

```bash
pnpm --filter docs lint
pnpm --filter docs test
```

文档构建：

```bash
pnpm turbo run build --filter=docs
```

Markdown 检查：

```bash
pnpm exec markdownlint-cli2 README.md
```

## 贡献

欢迎提交 Issue、测试、文档和代码改进。开始前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)，其中包含本仓库当前的协作流程、GitNexus 影响分析要求和 PR 检查清单。

参与讨论和审查时，请遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。安全相关问题请参考 [SECURITY.md](SECURITY.md)。

## 许可

本项目使用复合许可证：

- 软件代码：LGPL-3.0-or-later，详见 [LICENSE-code](LICENSE-code)。
- 文档内容：GNU FDL-1.3-or-later，详见 [LICENSE-docs](LICENSE-docs)。
- 许可证、媒体文件和脱敏要求：详见 [Repository-Policy.md](Repository-Policy.md)。

## 致谢

感谢 [NoneBot](https://nonebot.dev/) 项目和社区生态提供的基础能力。本项目也依赖并感谢这些工具与插件：

- [nonebot-plugin-alconna](https://github.com/nonebot/plugin-alconna)
- [nonebot-plugin-localstore](https://github.com/nonebot/plugin-localstore)
- [nonebot-plugin-orm](https://github.com/nonebot/plugin-orm)
- [nonebot-plugin-apscheduler](https://github.com/nonebot/plugin-apscheduler)
- [Fumadocs](https://fumadocs.dev/)
- [Next.js](https://nextjs.org/)
- [Vitest](https://vitest.dev/)
- [Ruff](https://docs.astral.sh/ruff/)
- [Pyright](https://microsoft.github.io/pyright/)
- [ty](https://docs.astral.sh/ty/)

完整依赖列表请以 [pyproject.toml](pyproject.toml) 和 [uv.lock](uv.lock) 为准。

## License

[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot?ref=badge_large)
