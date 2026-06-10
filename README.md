<!-- markdownlint-disable MD033 MD013 -->
# Lingchu Bot

> English | [中文](README-zh.md)

[![License](https://img.shields.io/github/license/xinvxueyuan/lingchu-bot)](LICENSE-code)
[![Release](https://img.shields.io/github/v/release/xinvxueyuan/lingchu-bot)](https://github.com/xinvxueyuan/lingchu-bot/releases)
[![Python](https://img.shields.io/badge/python-3.13-blue)](pyproject.toml)
[![NoneBot2](https://img.shields.io/badge/NoneBot2-2.x-orange)](https://nonebot.dev/)
[![Docs](https://img.shields.io/badge/docs-lingchu.zone.id-brightgreen)](https://lingchu.zone.id/)
[![Gitmoji](https://img.shields.io/badge/gitmoji-%20%F0%9F%98%9C%20%F0%9F%98%8D-FFDD67.svg?style=flat-square)](https://gitmoji.dev/)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot?ref=badge_shield)

Lingchu Bot is an application-side management bot project built on NoneBot2. It organizes core capabilities as plugins, targeting group management, command processing, configuration management, local storage, and async data access.

## Project Status

This project is still in the pre-alpha / development stage. Current code, configuration, command behavior, and documentation may continue to change; please do not treat existing interfaces as stable production interfaces.

If you want to follow the design and usage instructions, please read these first:

- [Online Documentation](https://lingchu.zone.id/)
- [User Guide](apps/docs/content/docs/user-guide/overview.mdx)
- [Developer Guide](apps/docs/content/docs/developer-guide/introduction.mdx)
- [Contributing Guide](CONTRIBUTING.md)

[![Zread Q&A][zread-shield]][zread-link]

[![DeepWiki Q&A][deepwiki-shield]][deepwiki-link]

## Project Positioning

The current repository contains these actual entry points:

- `nonebot-plugin-lingchu-bot`: Core NoneBot plugin, responsible for configuration, startup flow, sub-plugin loading, and shared utility capabilities.
- `[tool.nonebot]`: NoneBot configuration in `pyproject.toml`, declaring this repository's plugin directory, installed adapters, and dependency plugins.
- `Dockerfile` / `docker-compose.yml`: Container runtime entry; the image build stage generates a runtime `/tmp/bot.py` via `nb-cli`.

Plugins organize adapters by platform capabilities, with only one adapter's business code enabled by default per platform. The QQ platform priority is `~onebot.v11` > `~milky` > `~qq` > `~onebot.v12`, so OneBot V11 is selected by default; to switch to Milky or another QQ adapter, specify it explicitly via `LINGCHUAdapter` and ensure NoneBot has loaded the corresponding adapter. Implemented business handlers with test coverage are based on current source code and tests.

## Feature Overview

- Command processing: Organized via `nonebot-plugin-alconna` for command parsing.
- Currently implemented capabilities: QQ group management handlers, including member muting, unmuting,全员 muting/unmuting, group profile settings, member card/title/admin settings, group announcements, kicking, and leaving groups. OneBot V11 is selected by default; the Milky path has test coverage but requires explicit adapter configuration.
- Future directions: The project structure preserves extensibility for multi-adapter and non-group-management features, and can continue to evolve toward service integration, scheduled tasks, Web/API capabilities, and storage-driven workflows.
- Configuration management: Lightweight runtime configuration is written to `config.json5` in the plugin configuration directory, and can be overridden by NoneBot global configuration.
- Local storage: Uses `nonebot-plugin-localstore` to manage data, configuration, and cache directories.
- Data access: Provides JSON5 storage utilities and async CRUD helpers based on `nonebot-plugin-orm`.
- Message storage: Can record event reception, processing status, bot lifecycle, and platform API call summaries; adapters not enabled for the same platform are treated as disabled and do not enter message storage.
- Sub-plugin loading: The core plugin discovers and loads project sub-plugins, facilitating future feature splitting.

## Quick Start

### Prerequisites

- Python 3.13
- uv
- A working NoneBot runtime environment
- Connection and account configuration for the currently enabled QQ platform adapter; OneBot V11 by default, set `LINGCHUAdapter` explicitly for Milky

### Install Dependencies

```bash
uv sync --frozen
```

### Running

The current working tree does not commit a root `bot.py`. This repository is primarily a plugin package and NoneBot configuration:

- If integrating into an existing NoneBot project, load the local plugin directory per `plugin_dirs = ["src/plugins"]` in `[tool.nonebot]`.
- If using container runtime, use the Docker build process; the image generates a runtime `/tmp/bot.py` via `nb-cli`.
- Common local development path configuration is in [.env.example](.env.example), where `LOCALSTORE_USE_CWD=true` makes localstore data prefer the project directory.

For actual connection parameters, bot accounts, and platform-side configuration, please refer to the NoneBot, OneBot V11, Milky, or target adapter documentation.

### Runtime Configuration

Lingchu Bot generates a plugin configuration file `config.json5` on first startup. This file is located in the plugin configuration directory provided by `nonebot-plugin-localstore`; during local development, if `LOCALSTORE_USE_CWD=true` is enabled, it typically lands in the localstore configuration path under the current working directory.

The priority of lightweight runtime configuration is:

1. OS environment variables
2. NoneBot dotenv / global configuration
3. `config.json5`
4. Code defaults

OS environment variable and dotenv parsing reuse NoneBot2's own configuration mechanism, so case sensitivity, path types, JSON-style boolean values, and env file selection all follow NoneBot behavior. It is recommended to write stable plugin runtime items into `config.json5`, and place deployment-environment-related or sensitive override items in environment variables or NoneBot env files.

The default `config.json5` content is equivalent to:

```json5
{
  superuser_key: "123456789abcdef",
  message_store_enabled: true,
  message_store_retention_days: 30,
  message_store_summary_limit: 500,
  message_store_record_api_calls: true,
  message_store_cleanup_enabled: true,
  lingchu_adapter: null,
}
```

It can still be overridden in NoneBot global configuration, for example:

```toml
LINGCHUAdapter = "~onebot.v11"
```

### Adapter Selection

Lingchu Bot maps multiple concrete adapters to the same platform capability. Currently known QQ platform adapters include `~onebot.v11`, `~milky`, `~qq`, and `~onebot.v12`, with only the highest-priority `~onebot.v11` enabled by default.

To specify a QQ platform adapter, write in NoneBot global configuration:

```toml
LINGCHUAdapter = "~onebot.v11"
```

In the above example, the QQ platform selects `~onebot.v11`. If set to `LINGCHUAdapter = "~milky"`, the QQ platform selects Milky. Explicitly declaring an adapter in `LINGCHUAdapter` that Lingchu has not implemented or cannot recognize will cause startup failure; unknown adapters registered at runtime are still ignored.

Explicitly configuring multiple adapters for the same platform will cause startup failure, for example:

```toml
LINGCHUAdapter = "~milky+~onebot.v11"
```

Lingchu Bot does not control which adapters NoneBot actually imports or registers; it only selects business code per `LINGCHUAdapter`. When not explicitly configured, `~onebot.v11` is selected by default, so OneBot V11 must already be loaded/registered by NoneBot. The same applies when explicitly selecting other adapters: if `LINGCHUAdapter = "~milky"` but NoneBot has not loaded Milky, startup will fail. Additional adapters imported or registered for the same platform are treated as disabled by Lingchu Bot and their messages, lifecycle, or API calls are not recorded.

## Development and Verification

CI checks Ruff, Markdown, Pyright, ty, pytest, and documentation site lint/test. Before committing, it is recommended to run at least the checks relevant to your changes.

This repository also contains a Turborepo workspace for developing the Next.js documentation site and frontend packages. The documentation site source is in [apps/docs](apps/docs/), built with [Fumadocs](https://fumadocs.dev/), supporting bilingual Chinese/English, RSS feeds, Mermaid diagrams, Twoslash code hover, EPUB export, LLM-friendly text (`/llms.txt`, `/llms-full.txt`), and documentation relationship graphs.

Ruff:

```bash
uv run -m ruff check . --output-format=github
uv run -m ruff format --check .
```

Type checking:

```bash
uv run -m pyright .
uv run -m ty check --output-format github
```

Python tests:

```bash
uv run -m pytest
```

Documentation site lint and test:

```bash
pnpm --filter docs lint
pnpm --filter docs test
```

Documentation build:

```bash
pnpm turbo run build --filter=docs
```

Markdown check:

```bash
pnpm exec markdownlint-cli2 README.md
```

## Contributing

Issues, tests, documentation, and code improvements are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before starting, which includes the current collaboration workflow, GitNexus impact analysis requirements, and PR checklist.

When participating in discussions and reviews, please follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). For security-related issues, please refer to [SECURITY.md](SECURITY.md).

## License

This project uses a composite license:

- Software code: LGPL-3.0-or-later, see [LICENSE-code](LICENSE-code).
- Documentation content: GNU FDL-1.3-or-later, see [LICENSE-docs](LICENSE-docs).
- License, media files, and sanitization requirements: see [Repository-Policy.md](Repository-Policy.md).

## Acknowledgments

Thanks to the [NoneBot](https://nonebot.dev/) project and community ecosystem for providing foundational capabilities. This project also depends on and thanks these tools and plugins:

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

For the complete dependency list, please refer to [pyproject.toml](pyproject.toml) and [uv.lock](uv.lock).

## License Compliance

[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot?ref=badge_large)

[zread-shield]: https://img.shields.io/badge/Ask_Zread-_.svg?color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff

[deepwiki-shield]: https://deepwiki.com/badge.svg

[zread-link]: https://zread.ai/xinvxueyuan/lingchu-bot

[deepwiki-link]: https://deepwiki.com/xinvxueyuan/lingchu-bot
