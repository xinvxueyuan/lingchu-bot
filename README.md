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

Lingchu Bot is an application-side management bot project powered by NoneBot2. It currently focuses on QQ group management through OneBot V11 while keeping a plugin, platform registry, configuration, storage, permission, and documentation structure that can grow toward broader cross-platform workflows.

[![Zread Q&A][zread-shield]][zread-link]

[![DeepWiki Q&A][deepwiki-shield]][deepwiki-link]

## Project status

Lingchu Bot is still in **pre-alpha / development**. Code, configuration, command behavior, storage schema, and documentation can still change. Treat this README as an orientation map, and treat the source code plus docs as the source of truth for current behavior.

Useful entry points:

- [Online documentation](https://lingchu.zone.id/)
- [User guide overview](apps/docs/content/docs/user-guide/overview.mdx)
- [Quick start](apps/docs/content/docs/user-guide/quick-start.mdx)
- [QQ command reference](apps/docs/content/docs/platforms/qq/command-reference.mdx)
- [Architecture guide](apps/docs/content/docs/developer-guide/architecture/introduction.mdx)
- [Contributing guide](CONTRIBUTING.md)

## What is in this repository

- `nonebot-plugin-lingchu-bot`: the Python package declared in `pyproject.toml`.
- `src/plugins/nonebot_plugin_lingchu_bot`: the core NoneBot plugin, including metadata, startup hooks, platform registry, command handlers, permissions, i18n, repositories, and storage helpers.
- `[tool.nonebot]` in `pyproject.toml`: local plugin loading configuration, installed adapter declarations, and dependency plugin declarations.
- `apps/docs`: the Next.js / Fumadocs documentation site, with Chinese and English content.
- `Dockerfile` / `docker-compose.yml`: container runtime flow. The image generates `/tmp/bot.py` during build through `nb-cli`; the repository root does not ship a committed local `bot.py`.
- `scripts/setup.sh`: cross-platform initialization script for local development.

## Current capabilities

Current user-facing capabilities are concentrated in QQ group management commands:

- **Member moderation**: mute, unmute, kick, block, unblock, clear blocklist, protect, and unprotect.
- **Speech management**: member mute/unmute, whole-group mute/unmute, and recent message recall.
- **Group operations**: set group name, set group avatar when supported, set member card/title/admin, send announcements when supported, and leave the current group.
- **Remote management**: operate on another group by group ID or fuzzy group name matching, including remote mute/unmute, whole-group mute/unmute, kick, block/unblock, and announcement.
- **Bot control**: `silence` / `speak` suppress or resume response messages while still allowing commands to execute; `boot` / `shutdown` enable or disable command handlers.
- **Menu system**: the `菜单` / `menu` command lists platform-, protocol-, and implementation-filtered submenu entries.
- **Runtime configuration**: plugin-owned JSON5 files under the localstore configuration directory, plus higher-priority NoneBot/global environment overrides.
- **Permissions and protection**: UID-based superusers, platform account mapping, command grants, platform runtime role passthrough, blocklist, and protected-subject safeguards.
- **Message storage and API audit**: optional recording of events, processing status, bot lifecycle events, and platform API call summaries.
- **Runtime i18n**: gettext/Babel catalogs for Simplified Chinese and English feedback text, selected by `LINGCHU_LOCALE`, `lc_locale`, or `locale`.

Future cross-platform and non-group-management features depend on later implementation and tests.

## Adapter support

The currently implemented platform profile is **QQ**, and the only active adapter is **OneBot V11**:

```dotenv
LINGCHUAdapter=~onebot.v11
```

When `LINGCHUAdapter` is unset, Lingchu selects `~onebot.v11` by default. The selected adapter must also be loaded and registered by NoneBot; otherwise startup fails with a clear adapter-not-loaded error.

Deprecated adapters have been removed from the startup flow:

- `~milky`
- `~qq`
- `~onebot.v12`

Configuring any removed adapter fails fast with `PlatformAdapterDeprecatedError`. Configuring multiple known adapters for the same platform fails with `PlatformAdapterConflictError`. Configuring an unknown adapter fails startup as an unsupported Lingchu adapter.

OneBot V11 currently has `default` and `NapCat` implementation paths. Some features are implementation-gated: for example, group announcement and group avatar entries are shown only when the selected implementation supports them, and remote announcement requires `NapCat.Onebot >= 4.18.0`.

## Quick start

### Requirements

- Python 3.13 (`pyproject.toml` requires `>=3.13, <3.14`)
- `uv`
- Git
- A usable NoneBot runtime and OneBot V11 connection/account setup
- Node.js 20+ and pnpm 9+ for the docs/frontend workspace and the full setup script

### Clone and initialize

```bash
git clone https://github.com/xinvxueyuan/lingchu-bot.git
cd lingchu-bot
chmod +x scripts/setup.sh
./scripts/setup.sh
```

The setup script checks the operating system and toolchain, installs Python and Node.js dependencies, creates environment files, configures Git hooks, and can optionally install Playwright browsers.

Manual alternative:

```bash
uv sync --frozen
pnpm install
pnpm exec husky
cp .env.example .env
```

### Choose a runtime mode

Use Lingchu Bot as a local plugin directory from an existing NoneBot project:

```toml
# In the target NoneBot project's pyproject.toml
[tool.nonebot]
plugin_dirs = ["path/to/lingchu-bot/src/plugins"]
```

Or use the container runtime:

```bash
# docker-compose.yml currently reads .env.prod; create it from your deployment settings.
cp .env.example .env.prod
docker compose up --build
```

Before connecting to a real platform, prepare the account, network, reverse WebSocket/HTTP settings, and permissions required by NoneBot and the OneBot V11 implementation you use.

## Essential configuration

Lingchu creates `config.json5` on first startup in the plugin configuration directory provided by `nonebot-plugin-localstore`. Runtime configuration priority is:

1. OS environment variables
2. NoneBot dotenv / global configuration
3. `config.json5`
4. Code defaults

Important settings:

| Setting | Purpose |
| --- | --- |
| `LINGCHUAdapter` / `LINGCHU_ADAPTER` | Select the active adapter; current supported value is `~onebot.v11`. |
| `LINGCHU_SUPERUSERS` | UID-to-platform account mapping for Lingchu superusers. |
| `SUPERUSERS` | Fallback QQ account list when `LINGCHU_SUPERUSERS` is absent or null. |
| `LINGCHU_LOCALE` | Runtime locale; available catalogs currently include `zh_CN` and `en_US`. |
| `LOCALSTORE_USE_CWD` | Store localstore data/config/cache under the project directory when true. |
| `MESSAGE_STORE_ENABLED` | Enable message-store runtime hooks. |
| `MESSAGE_STORE_RETENTION_DAYS` | Retention window for message records; `0` disables day-based expiry. |
| `MESSAGE_STORE_SUMMARY_LIMIT` | Maximum summary length for text/data/result payloads. |
| `MESSAGE_STORE_RECORD_API_CALLS` | Record platform API call summaries. |
| `RECALL_MESSAGE_DEFAULT_COUNT` | Default count for the message recall command. |
| `PERMISSION_PLATFORM_RUNTIME_PASSTHROUGH` | Allow platform roles such as QQ owner/admin/member to satisfy Lingchu permission grants. |
| `COMMAND_TRIGGER_OVERRIDES` | Override primary command triggers and aliases by command key. |
| `MENU_PAGE_TRIGGER_OVERRIDES` | Override menu page triggers by menu page id. |
| `PROTECTED_SUBJECT_FEATURE_KEYS` | Side-effect command keys blocked when their target user is protected. |

Example `config.json5`:

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

Boolean values in NoneBot `.env` files must use JSON-style lowercase `true` / `false`, not Python-style `True` / `False`.

## Commands at a glance

Main menu:

```text
菜单
menu
```

Default submenu pages:

- `成员管理` / `member-management`
- `发言管理` / `speech-management`
- `群聊管理` / `group-chat-management`
- `远程管理` / `remote-management`
- `系统管理` / `system-management`

Examples:

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

Command trigger language is locale-exclusive. Chinese locales enable Chinese triggers; English locales enable short hyphenated English triggers. They are not enabled at the same time. Full command behavior, permission pre-checks, implementation filters, and remote management details are documented in [QQ Commands](apps/docs/content/docs/platforms/qq/command-reference.mdx).

## Development and verification

CI checks Ruff, Markdown, Pyright, ty, pytest on multiple database backends, and docs site lint/test. Run the checks relevant to your change before committing.

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

# Optional multi-database testing:
# SQLALCHEMY_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/postgres" uv run -m pytest
# SQLALCHEMY_DATABASE_URL="mysql+aiomysql://mysql:mysql@localhost:3306/mymysql" uv run -m pytest
```

Documentation site:

```bash
pnpm --filter docs lint
pnpm --filter docs test
pnpm turbo run build --filter=docs
```

Runtime i18n catalogs:

```bash
task i18n
```

Markdown:

```bash
pnpm exec markdownlint-cli2 README.md README-zh.md
```

## Contributing

Issues, tests, documentation, and code improvements are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before starting; it describes the current collaboration workflow, GitNexus impact analysis requirements, and PR checklist.

When participating in discussions and reviews, please follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). For security-related issues, please refer to [SECURITY.md](SECURITY.md).

## License

This project uses a composite license:

- Software code: LGPL-3.0-or-later, see [LICENSE-code](LICENSE-code).
- Documentation content: GNU FDL-1.3-or-later, see [LICENSE-docs](LICENSE-docs).
- License, media files, and sanitization requirements: see [Repository-Policy.md](Repository-Policy.md).

## Acknowledgments

Lingchu Bot stands on a lot of good open-source shoulders. Thanks especially to these upstream projects and communities:

- **Bot runtime and adapter ecosystem**: [NoneBot2](https://nonebot.dev/), [nonebot-adapter-onebot](https://github.com/nonebot/adapter-onebot), `nonebot-plugin-alconna`, `nonebot-plugin-localstore`, `nonebot-plugin-orm`, `nonebot-plugin-apscheduler`, `nonebot-plugin-htmlkit`, `nonebot-plugin-docs`, and `nonebot-plugin-wait-a-minute`.
- **Python configuration, storage, and service utilities**: `aiofiles`, `json5`, `rtoml`, `jsonschema`, [Babel](https://babel.pocoo.org/), [Jinja](https://jinja.palletsprojects.com/), [Typer](https://typer.tiangolo.com/), [Arrow](https://arrow.readthedocs.io/), `psutil`, and the [OpenAI Python SDK](https://github.com/openai/openai-python).
- **Documentation and frontend stack**: [Fumadocs](https://fumadocs.dev/), [Next.js](https://nextjs.org/), [React](https://react.dev/), [Mermaid](https://mermaid.js.org/), [Twoslash](https://twoslash.netlify.app/), `flexsearch`, `d3-force`, `dompurify`, `feed`, and [Tailwind CSS](https://tailwindcss.com/).
- **Engineering, testing, and repository workflow**: [uv](https://docs.astral.sh/uv/), [pnpm](https://pnpm.io/), [Turborepo](https://turbo.build/repo), [Ruff](https://docs.astral.sh/ruff/), [Pyright](https://microsoft.github.io/pyright/), [ty](https://docs.astral.sh/ty/), [pytest](https://docs.pytest.org/), [Vitest](https://vitest.dev/), [Playwright](https://playwright.dev/), [markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2), [Prettier](https://prettier.io/), [ESLint](https://eslint.org/), [Husky](https://typicode.github.io/husky/), [Gitmoji](https://gitmoji.dev/), `gitnexus`, and [FOSSA](https://fossa.com/).

For complete dependency lists, please refer to [pyproject.toml](pyproject.toml), [package.json](package.json), [apps/docs/package.json](apps/docs/package.json), and [uv.lock](uv.lock).

## License compliance

[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot?ref=badge_large)

[zread-shield]: https://img.shields.io/badge/Ask_Zread-_.svg?color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff

[deepwiki-shield]: https://deepwiki.com/badge.svg

[zread-link]: https://zread.ai/xinvxueyuan/lingchu-bot

[deepwiki-link]: https://deepwiki.com/xinvxueyuan/lingchu-bot
