# Lingchu Bot

> English | [中文](README-zh.md)

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

**Lingchu Bot** is an application-side group management bot powered by NoneBot2. It currently focuses on QQ group management through the OneBot V11 adapter while keeping a plugin, platform registry, configuration, storage, permission, and documentation structure that can grow toward broader cross-platform workflows.

[![Zread Q&A][zread-shield]][zread-link]

[![DeepWiki Q&A][deepwiki-shield]][deepwiki-link]

## Project status

Lingchu Bot has published its first `0.0.1` formal release. The project is still early and may make breaking changes before `1.0.0`, but the current release is intended to be installable, documented, and reproducible through the release workflow.

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

## Capabilities

| Capability | Description |
| --- | --- |
| Member moderation | Mute, unmute, kick, block, unblock, clear blocklist, protect, and unprotect. |
| Speech management | Member mute/unmute, whole-group mute/unmute, and recent message recall. |
| Group operations | Set group name, set group avatar when supported, set member card/title/admin, send announcements when supported, and leave the current group. |
| Remote management | Operate on another group by group ID or fuzzy group name matching, including remote mute/unmute, whole-group mute/unmute, kick, block/unblock, and announcement. |
| Bot control | `silence` / `speak` suppress or resume response messages while still allowing commands to execute; `boot` / `shutdown` enable or disable command handlers. |
| Menu system | The `菜单` / `menu` command lists platform-, protocol-, and implementation-filtered submenu entries. |
| Runtime configuration | Plugin-owned TOML files under the localstore configuration directory, plus higher-priority NoneBot / environment overrides. |
| Permissions and protection | UID-based superusers, platform account mapping, command grants, platform runtime role passthrough, blocklist, and protected-subject safeguards. |
| Message store and API audit | Optional recording of events, processing status, bot lifecycle events, and platform API call summaries. |
| Runtime i18n | gettext / Babel catalogs for Simplified Chinese and English feedback text. |
| LLM service | Managed OpenAI / LiteLLM profiles with stable and provider-native APIs. |
| Scheduler | Periodic tasks and cleanup through `nonebot-plugin-apscheduler`. |

Future cross-platform and non-group-management features depend on later implementation and tests.

## Adapter support

The currently implemented platform profile is **QQ**, and the only active adapter is **OneBot V11**:

```dotenv
LINGCHUAdapter=~onebot.v11
```

When `LINGCHUAdapter` is unset, Lingchu selects `~onebot.v11` by default. The selected adapter must also be loaded and registered by NoneBot; otherwise startup fails with a clear adapter-not-loaded error.

Only OneBot V11 is implemented. Configuring any other adapter ID (such as `~milky`, `~qq`, or `~onebot.v12`) fails startup with `PlatformAdapterUnknownError`. Configuring multiple known adapters for the same platform fails with `PlatformAdapterConflictError`.

OneBot V11 currently has `default` and `NapCat` implementation paths. Some features are implementation-gated: for example, group announcement and group avatar entries are shown only when the selected implementation supports them, and remote announcement requires `NapCat.Onebot >= 4.18.0`.

## Quick start

### Requirements

- Python 3.13 (`pyproject.toml` requires `>=3.13, <4.0`; targets 3.13)
- `uv`
- Git
- A usable NoneBot runtime and OneBot V11 connection / account setup
- Node.js 24+ and pnpm for the docs / frontend workspace and the full setup script

### Option A — Install via NB-CLI (recommended)

```bash
nb plugin install nonebot-plugin-lingchu-bot
```

This installs the published package from PyPI and registers it with NoneBot. After installation, add `nonebot_plugin_lingchu_bot` to your NoneBot plugin list or let NB-CLI manage it automatically.

### Option B — Use as a local plugin directory

Clone the repository and initialize:

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

To load Lingchu Bot from an existing NoneBot project, point `plugin_dirs` at the cloned `src/plugins` directory:

```toml
# In the target NoneBot project's pyproject.toml
[tool.nonebot]
plugin_dirs = ["path/to/lingchu-bot/src/plugins"]
```

### Option C — Run in Docker

```bash
# docker-compose.yml reads .env.prod; create it from your deployment settings.
cp .env.example .env.prod
docker compose up --build
```

Before connecting to a real platform, prepare the account, network, reverse WebSocket / HTTP settings, and permissions required by NoneBot and the OneBot V11 implementation you use.

## Configuration

Deployment fields are resolved by NoneBot from OS environment variables, its `.env` files or global configuration, then code defaults. Lingchu does not implement a second dotenv or TOML override layer. Startup does not create deployment configuration or install JSON Schema files.

Online-editable command, menu-trigger, and platform-permission overrides are stored separately in localstore-owned `runtime-overrides.toml`. Boolean values in NoneBot `.env` files must use JSON-style lowercase `true` / `false`, not Python-style `True` / `False`.

| Group | Setting | Purpose |
| --- | --- | --- |
| NoneBot Core | `HOST`, `PORT` | NoneBot server host and port. |
| NoneBot Core | `NICKNAME` | Bot nickname(s). |
| NoneBot Core | `LOG_LEVEL` | NoneBot log level. |
| NoneBot Core | `COMMAND_START`, `COMMAND_SEP` | NoneBot command parsing tokens. |
| NoneBot Core | `FASTAPI_DOCS_URL`, `FASTAPI_REDOC_URL` | FastAPI docs endpoints; disable in production. |
| Container Detection | `LINGCHU_IN_CONTAINERS` | Whether the bot runs inside a container (`config.in_containers`). |
| Lingchu Runtime | `LINGCHUAdapter` / `LINGCHU_ADAPTER` | Select the active adapter; current supported value is `~onebot.v11`. |
| Lingchu Runtime | `LINGCHU_SUPERUSERS` | UID-to-platform account mapping for Lingchu superusers. |
| Lingchu Runtime | `LINGCHU_LOCALE` | Runtime locale; available catalogs are `zh_CN` and `en_US`. |
| Lingchu Runtime | `LINGCHU_SUPERUSER_KEY` | Superuser key string (`superuser_key`). |
| Localstore | `LOCALSTORE_USE_CWD` | Store localstore data / config / cache under the project directory when true. |
| Message Store | `LINGCHU_MESSAGE_STORE_ENABLED` | Enable message-store runtime hooks. |
| Message Store | `LINGCHU_MESSAGE_STORE_RETENTION_DAYS` | Retention window for message records; `0` disables day-based expiry. |
| Message Store | `LINGCHU_MESSAGE_STORE_SUMMARY_LIMIT` | Maximum summary length for text / data / result payloads. |
| Message Store | `LINGCHU_MESSAGE_STORE_RECORD_API_CALLS` | Record platform API call summaries. |
| Message Store | `LINGCHU_MESSAGE_STORE_CLEANUP_ENABLED` | Enable expired message cleanup. |
| Recall | `LINGCHU_RECALL_MESSAGE_DEFAULT_COUNT` | Default count for the message recall command (`1`–`100`). |
| Protected Subjects | `LINGCHU_PROTECTED_SUBJECT_FEATURE_KEYS` | Side-effect command keys blocked when their target user is protected. |
| Database | `SQLALCHEMY_DATABASE_URL` | SQLAlchemy database URL; supports SQLite / PostgreSQL / MySQL / MariaDB / Oracle / SQL Server. Unset uses default SQLite. |
| Database | `ALEMBIC_STARTUP_CHECK` | Set to `true` in production to enforce schema migration checks on startup. |
| LLM Service | `LINGCHU_AI_PROVIDER` | Legacy/default LLM backend: `litellm` or `openai`. |
| LLM Service | `LINGCHU_AI_MODEL` | Legacy/default model id (`gpt-4o-mini`). |
| LLM Service | `LINGCHU_AI_BASE_URL` | Legacy/default OpenAI-compatible base URL. |
| LLM Service | `LINGCHU_AI_TIMEOUT` | Legacy/default request timeout in seconds. |
| LLM Service | `LINGCHU_AI_API_KEY` | Legacy/default API key; prefer profile `api_key_env`. |
| Announcement Images | `LINGCHU_ANNOUNCEMENT_IMAGE_CACHE_DIR` | Host-side cache directory for announcement images (defaults to localstore cache). |
| Announcement Images | `LINGCHU_ANNOUNCEMENT_IMAGE_PROTOCOL_DIR` | Protocol-side directory NapCat sees inside the container. |

Example `runtime-overrides.toml`:

```toml
#:schema ./runtime-overrides.schema.json
permission_platform_runtime_passthrough = true

[command_trigger_overrides.member_mute]
chinese = "禁言"
english = "mute"

[menu_page_trigger_overrides.member-management]
chinese = "成员管理"
english = "member-management"
```

Use `lingchu config init`, `lingchu config validate`, and `lingchu schema install` to manage this file explicitly. Migrate an old combined file with `lingchu config migrate --source config.toml --env-file .env --residual runtime-overrides.toml --dry-run`, inspect the redacted plan, then rerun without `--dry-run`. Use `--force` only to replace conflicting managed environment keys. The same commands are available through `nb lingchu`. Legacy `.json5` files are not read or migrated.

### Managed LLM profiles

Lingchu also creates `llm.toml` in the plugin configuration directory. A
non-empty `[profiles]` table takes precedence over deployment `ai_*` environment fields; an empty table uses those deployment fields as an implicit `default`
profile. Keep credentials out of TOML by naming an environment variable with
`api_key_env`:

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

OpenAI profiles use Responses for the stable generation API. LiteLLM profiles
select `responses` or `chat` with `litellm_generation`; enabling `[router]`
exposes LiteLLM's in-process Router to trusted internal callers. The managed
runtime also exposes the native `AsyncOpenAI` client, LiteLLM module, and native
Router, so provider-specific resources and future SDK operations do not need a
Lingchu wrapper first.

Capability probes return `supported`, `unsupported`, or `unknown` and are
advisory: `unknown` never blocks an explicitly requested native call. A reload
structurally validates and freezes candidate profiles before atomically replacing
the old runtime; credentials remain lazy per profile. Failed reloads leave the
current generation running, and successful reloads close retired clients and
invalidate capability caches.

Custom `base_url` values reject loopback, link-local, metadata, and other
private IP literals unless `allow_private_network = true`. Credentials are not
sent to a custom base URL unless
`allow_credentials_to_custom_base_url = true`. These are explicit trust
switches, not recommendations; deployments must also enforce DNS and redirect
policy at the network layer. The synthesized implicit legacy profile treats an
existing legacy URL/key pair as legacy opt-in; explicit profiles never inherit
that exception. Stable `provider_options` reject credential, endpoint, callback,
logger, retry, and Router control keys. Lingchu passes tool definitions and native
results through but never executes model-requested tools automatically.

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

CI checks Ruff, Markdown, Pyright, ty, pytest on multiple database backends, and docs site lint / test. Run the checks relevant to your change before committing.

Ruff:

```bash
uv run -m ruff check . --output-format=github
uv run -m ruff format --check .
```

Type checking:

```bash
uv run -m pyright
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

Issues, tests, documentation, and code improvements are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before starting; it describes the current collaboration workflow, GitNexus impact analysis requirements, version validation system, and PR checklist.

When participating in discussions and reviews, please follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). For security-related issues, please refer to [SECURITY.md](SECURITY.md).

## License

This project uses a **phased open-source license stack** (see
[Repository-Policy.md](Repository-Policy.md) for the transition rules
and trigger date):

- **Current phase** — Software: `LGPL-3.0-or-later`
  ([`LICENSE-code`](LICENSE-code)). Documentation: `GFDL-1.3-or-later`
  ([`LICENSE-docs`](LICENSE-docs)). Visual elements: `CC0-1.0`
  ([`LICENSE-cc0`](LICENSE-cc0)).
- **Future phase** (triggered automatically on the earlier of one year
  after the first public release or the first major version bump) —
  Software: `MIT OR Apache-2.0` (dual, user-elected; see
  [`LICENSE-mit`](LICENSE-mit) and [`LICENSE-apache`](LICENSE-apache)).
  Documentation and visual elements: `CC-BY-SA-4.0-or-later`
  ([`LICENSE-cc-by-sa`](LICENSE-cc-by-sa)).

By submitting a contribution, you accept the terms of
[CLA.md](CLA.md), which grants the Project the rights it needs to
execute the transition described above. The transition only applies to
contributions submitted on or after the trigger date; contributions made
before the trigger date remain under the license that was in effect at
the time of submission.

For media file handling, sanitization requirements, REUSE compliance,
and the official license texts, see [Repository-Policy.md](Repository-Policy.md)
and the [`LICENSE-*`](LICENSE-code) files in the repository root.

## Acknowledgments

Lingchu Bot stands on a lot of good open-source shoulders. Thanks especially to these upstream projects and communities:

- **Bot runtime and adapter ecosystem**: [NoneBot2](https://nonebot.dev/), [nonebot-adapter-onebot](https://github.com/nonebot/adapter-onebot), `nonebot-plugin-alconna`, `nonebot-plugin-localstore`, `nonebot-plugin-orm`, `nonebot-plugin-apscheduler`, `nonebot-plugin-htmlkit`, and `nonebot-plugin-docs`.
- **Python configuration, storage, and service utilities**: `aiofiles`, `toml`, `rtoml`, `jsonschema`, [Babel](https://babel.pocoo.org/), [Jinja](https://jinja.palletsprojects.com/), [Typer](https://typer.tiangolo.com/), [Arrow](https://arrow.readthedocs.io/), `psutil`, [OpenAI Python SDK](https://github.com/openai/openai-python), and [LiteLLM](https://github.com/BerriAI/litellm).
- **Documentation and frontend stack**: [Fumadocs](https://fumadocs.dev/), [Next.js](https://nextjs.org/), [React](https://react.dev/), [Mermaid](https://mermaid.js.org/), [Twoslash](https://twoslash.netlify.app/), `flexsearch`, `d3-force`, `dompurify`, `feed`, and [Tailwind CSS](https://tailwindcss.com/).
- **Engineering, testing, and repository workflow**: [uv](https://docs.astral.sh/uv/), [pnpm](https://pnpm.io/), [Turborepo](https://turbo.build/repo), [Ruff](https://docs.astral.sh/ruff/), [Pyright](https://microsoft.github.io/pyright/), [ty](https://docs.astral.sh/ty/), [pytest](https://docs.pytest.org/), [Vitest](https://vitest.dev/), [Playwright](https://playwright.dev/), [markdownlint-cli2](https://github.com/DavidAnson/markdownlint-cli2), [Prettier](https://prettier.io/), [ESLint](https://eslint.org/), [Husky](https://typicode.github.io/husky/), [Gitmoji](https://gitmoji.dev/), `gitnexus`, and [FOSSA](https://fossa.com/).

For complete dependency lists, please refer to [pyproject.toml](pyproject.toml), [package.json](package.json), [apps/docs/package.json](apps/docs/package.json), and [uv.lock](uv.lock).

## License compliance

[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2Fxinvxueyuan%2Flingchu-bot?ref=badge_large)

[zread-shield]: https://img.shields.io/badge/Ask_Zread-_.svg?color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff

[deepwiki-shield]: https://deepwiki.com/badge.svg

[zread-link]: https://zread.ai/xinvxueyuan/lingchu-bot

[deepwiki-link]: https://deepwiki.com/xinvxueyuan/lingchu-bot
