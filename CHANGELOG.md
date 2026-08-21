<!-- markdownlint-disable MD024 -->
# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [0.6.2] - 2026-08-21

补丁版本：基于整仓安全评审，收敛权限 fail-open、静默泄漏、数据一致性与时序脆弱点。

### Security

- 权限平台运行时组 passthrough 默认改为 `False`，未知平台不再放行；配置/查询异常时同样拒绝。
- SUPERUSERS 判定统一走数据库 `is_superuser`，移除对 `driver.config.superusers` 的旁路依赖。
- 静默模式（闭嘴/全局静默）下 `call_api("send_*")` 与 `send_*` 方法一并抑制，不再漏发。
- Handle 配置文件损坏时该指令默认**禁用**而非回退为启用。
- 群发公告限制单次目标数量并要求显式指定目标，避免单指令无限流群发。
- 原始事件/消息入库增加长度上限，降低 PII 明文落库体积。

### Changed

- 启动阶段的运行时配置加载与数据库播种支持有限重试，瞬时故障不再直接打崩 NoneBot。
- 会话 ID 加入 `group:`/`supergroup:`/`peer:` 前缀，避免跨类型碰撞。
- TOML 写入增加跨进程 lock-file 与文件/目录 `fsync`，降低断电丢数据风险。
- 消息摘要截断保证不超过字段上限。
- `release.yml` 改为手动触发（`workflow_dispatch` + `bump` 输入），不再推送 `releases/<bump>` 分支。

### Removed

- **BREAKING** 移除 Oracle 与 SQL Server 方言数据库支持，仅支持
  SQLite / PostgreSQL / MySQL / MariaDB（与 nonebot-plugin-orm 官方矩阵一致）；
  同步裁剪 `_dialect_compat` 变体、手写 MERGE upsert、CI 矩阵与相关依赖
  （`oracledb` / `aioodbc` / `pyodbc`）。

### Fixed

- `protocol_id` 唯一约束不再因 `NULL` 失效（`unknown` sentinel + 迁移 `g7b8c9d0e1f2`）。
- MySQL/MariaDB upsert 不再覆盖 `created_at`；blocklist 与 subject policy 双写置于 savepoint 内。
- 空序列 `IN` 过滤改为抛错，避免静默匹配不到任何记录。
- 外键冲突识别补齐 MySQL `1451/1452/23000`，不再误判为唯一冲突。
- 修复 `core → handle` 顶层导入环（函数内延迟导入）。

## [0.6.1] - 2026-08-20

补丁版本：合并运行时配置缓存、持久化可靠性和 CLI 无 `bot.py` 项目启动推导修复。

### Changed

- 运行时配置和机器人状态使用稳定快照、写后校验与有界重试，避免异步 flush 覆盖较新的内存状态。
- `lc-cli` 在项目没有 `bot.py` 时增强入口推导，并补齐相关文档命令引用。

### Fixed

- 启动时可变设置读取失败会回退到干净默认值；关机时两个配置域独立 flush，即使一个失败也不会阻断另一个。
- SQLite PRAGMA 游标创建、执行和关闭异常均 fail-soft 记录日志。

## [0.5.0] - 2026-08-14

次要版本发布：移除 LLM / NovelAI MCP 与 Pydantic 技术栈，运行时与开发数据治理加固。

### Removed

- **BREAKING** 移除基于 `pydantic-ai` 的 LLM 运行时与 `mcp` 依赖，以及 NovelAI MCP
  服务端/客户端、MCP 管理脚本（`scripts/mcp_admin.py`、`scripts/check-wheel-entrypoints.py`）。
- **BREAKING** 删除 MCP / LLM 相关文档页与 `.env.example` / `.env.prod.example` 配置项。

### Changed

- 运行时生命周期、身份、审核与出站 HTTP 行为 fail-safe 化（出站请求仅 2xx 视为成功并验证对端地址）。
- 身份完整性迁移：清理孤儿行后再建外键；缩短超长外键名以适配 MySQL 64 字符标识符限制。
- 调度器在会话内读取 ORM 字段并解码 payload，避免提交后 DetachedInstanceError。
- 权限 IN 展开为 OR-of-ANDs 以兼容 SQL Server；同步时清理过期超级用户授权。
- 新增 `clean_dev_data` 开发数据清理命令（拒绝解析到仓库外的路径）。
- `ci:version:bump` 改用 PEP 440 排序选取最新 tag。

### Fixed

- MCP 移除后重新连接 Alembic 迁移链（`message_protocol_default` 迁移）。
- 修复 Dependabot alerts。
- 修复 CI badges、docs 测试路由与 docs smoke 的 checkout 顺序。
- Release 流程修复：pypi 环境声明（Trusted Publishing OIDC）、本地复合动作前显式
  checkout、Task >= 3.52 变量覆盖、不再提前删除 `.github` 目录。
- 修复 bump-style 发布流程的版本推导（pre-release 最新 tag 下开启新版本循环）与
  本地 `release:prepare`（pyproject.toml 持久化、Windows CR 清洗）。

## [0.4.1] - 2026-08-03

Release and CI infrastructure hardening, plus a Docker runtime stability fix.

### Changed

- Docker runtime stage reverted from `python:3.14-slim` to pinned
  `python:3.13-slim` so the image matches `requires-python = ">=3.13, <3.14"`.
- GitHub Actions steps consolidated into reusable composite actions
  (`.github/actions/{checkout,setup-node-pnpm,setup-uv-task,setup-toolchain,verify-wheel,attest-slsa}`).

### Fixed

- `ci:version:tag-only` failed to push release tags after workflow merges:
  `GITHUB_TOKEN` cannot create tags whose tree differs in
  `.github/workflows/**` from branch tips. The `versioned-build` and
  `github-release` jobs now checkout with a fine-grained PAT
  (`secrets.WORKFLOW_TOKEN`, `Contents` + `Workflows: read and write`).
- Release tag syntax error in the versioning workflow.
- Missing explicit checkout before `setup-toolchain` in `ci-builds.yml`.

## [0.4.0] - 2026-07-28

LLM runtime migrated from OpenAI/LiteLLM backends to Pydantic AI, and NovelAI
image subplugin migrated from hand-written HTTP client to MCP server subprocess.

### Added

- NovelAI MCP client service (`NovelAIMCPClient`) managing a
  `fastmcp.client.Client` stdio connection to the `novelai-image-mcp` server
  subprocess, with lazy initialization, env-var credential propagation, and
  NoneBot shutdown hook registration.
- `NovelAIConfig` MCP server management fields: `mcp_command` (default `"uvx"`),
  `mcp_args` (default `("novelai-image-mcp", "serve")`), `output_dir`.
- `handler.py::_plan_to_mcp_args()` converter mapping `NovelAIGenerationPlan`
  fields to MCP `generate_image` tool arguments.
- `NovelAIConfig.mcp_args` `@field_validator(mode="before")` to split
  whitespace-separated env-var strings into `tuple[str, ...]`.
- Pydantic AI-based LLM runtime using `pydantic_ai.Agent` with multi-provider
  support, MCP toolset integration, and Pydantic Logfire observability.
- LLM configuration schema using `[pydantic-ai]` and `[mcp]` sections in
  `llm.toml`, replacing the deprecated `[profiles.*]`, `[router]`, and `[eve]`.
- AGENTS lessons for Pydantic AI migration and NovelAI MCP migration.

### Changed

- **BREAKING** NovelAI image subplugin delegates all NovelAI HTTP interaction
  to the `novelai-image-mcp` MCP server subprocess. The hand-written HTTP
  client, authentication, MessagePack/ZIP parsing, and payload construction
  are removed; the handler calls MCP tools via `fastmcp.client.Client`.
- **BREAKING** LLM runtime migrated from OpenAI/LiteLLM backends to Pydantic AI.
  `LLMRuntime.openai()` and `LLMRuntime.litellm()` are removed; use
  `LLMRuntime.respond()` / `respond(stream=True)` for all LLM access.
- `handler.py` maps each former `NovelAIClient` method to its equivalent MCP
  tool: `generate_image`, `image_to_image`, `inpaint`, `director_tool`,
  `upscale_image`, `annotate_image`, `suggest_tags`, `get_subscription`,
  `get_user_data`, `encode_vibe`.
- `constants.py` simplified to only input-validation enums (`DirectorTool`,
  `Emotion`, `EmotionLevel`, `ControlNetModel`); API constants (`Endpoint`,
  `Model`, `Action`, `Sampler`, `NoiseSchedule`, `QUALITY_TAGS`, `UC_PRESETS`)
  are removed — the MCP server owns them.
- `models.py` simplified: `GenerationRequest`, `CharacterPrompt`, and
  `_merge_csv` removed; pipeline DTOs (`PromptIntent`, `NovelAIGenerationPlan`,
  `GenerationOverrides`, etc.) retained.
- Credentials (`token`/`username`/`password`) passed to MCP subprocess as
  `NOVELAI_TOKEN`/`NOVELAI_USERNAME`/`NOVELAI_PASSWORD` env vars, not sent
  over HTTP by the bot.

### Removed

- **BREAKING** Deleted NovelAI HTTP modules: `client.py`, `auth.py`,
  `exceptions.py`, `imaging.py`, `payload.py`, `response.py`.
- **BREAKING** Deleted `services/llm/backends.py` — `LLMRuntime` creates
  `pydantic_ai.Agent` instances internally.
- Deleted NovelAI test files: `test_client.py`, `test_full_client.py`,
  `test_payload.py`, `test_protocol.py`.
- Deleted LLM test files: `test_litellm_backend.py`, `test_openai_backend.py`,
  `test_router.py`, `test_sdk_contract.py`, `test_live.py`.
- `NovelAIConfig` HTTP fields removed: `base_url`, `account_base_url`,
  `vibe_cache_entries`.
- `[profiles.*]`, `[router]`, and `[eve]` sections in `llm.toml` emit
  deprecation WARNINGs and are ignored.

### Fixed

### Security

- NovelAI credential handling delegated to MCP server subprocess; the bot no
  longer derives access keys or sends HTTP requests with embedded credentials.

## [0.3.0] - 2026-07-28

Adapter module registry consolidated into a single source of truth, plus a
transitive dependency security fix.

### Added

- ADR-0002 (`docs/adr/0002-adapter-module-path-registry.md`) recording the
  decision that `platforms/registry.py::_PROTOCOL_IMPLEMENTATIONS` is the
  single source of truth for adapter→module-path mapping.
- "Handler Kind" domain term in `CONTEXT.md` naming the `"command" | "menu"`
  dispatch dimension of the handler loader.

### Changed

- Adapter module registry consolidated: the `_ADAPTER_MODULES` dicts in
  `handle/qq/adapters/__init__.py` and `handle/menu.py` are removed. The
  loader now resolves handler module paths exclusively from
  `_PROTOCOL_IMPLEMENTATIONS` via `get_protocol_implementations`, so
  database seeding and handler loading share one mapping by construction.
- `load_adapter_handlers` interface deepened from
  `(adapter_id, adapter_modules, package)` to `(adapter_id, kind)`; the two
  `import_handle()` entry points (group + menu) collapsed into one
  `import_handle(kind: HandlerKind)`.

### Removed

- Telegram adapter compatibility shim at
  `handle/qq/adapters/telegram/default/__init__.py` — the loader now
  imports `handle.telegram.adapters.default` directly from the registry's
  absolute `module_path`.

### Fixed

- Resolved `brace-expansion@2.x` transitive dependency vulnerability
  (CVE-2026-14257) by globally overriding `minimatch` to `^10.2.5`.

### Security

- No new security findings. The `minimatch` override (above) closes the
  only Dependabot alert outstanding from 0.2.0.

## [0.2.0] - 2026-07-28

Telegram platform support added. This release introduces the Telegram Bot API
as a second platform front-end alongside OneBot V11, plus a smoke-test
startup fix, a full-project security audit, and a senior-architect
architecture review with P0 remediation.

### Added

- Telegram platform support: five group-management command handlers
  (`bot_state`, `menu`, `moderation`, `mute`, `recall`) under
  `handle/telegram/adapters/default/`, mirroring the OneBot V11 handler
  surface through the existing `selected_adapter_handle` decorator.
- Telegram permission seeds in `platforms/telegram/permissions.py`,
  registered via the platform registry and consumed by the permission
  service for fail-closed authorization.
- Telegram platform overview docs at
  `apps/docs/src/content/docs/platforms/telegram/overview.mdx` (EN + ZH),
  with a matching sidebar entry in `apps/docs/astro.config.mjs` and a
  Telegram row in the "Available platforms" table in
  `platforms/index.mdx` (EN + ZH).
- "Adapter Handle Decorators" lesson documented in `AGENTS.md`,
  `CLAUDE.md`, and `.github/note/AGENTS-zh.md`: handler modules decorated
  by `selected_adapter_handle` MUST NOT use `from __future__ import
  annotations`, because NoneBot resolves signature forward refs via
  `wrapper.__globals__` (the `common.py` module globals), not
  `func.__globals__`.
- Threat model and full-project security audit report at
  `.trae/specs/prepare-0.2.0-release/security-audit.md` covering all six
  surfaces (trust boundaries, authn/authz, secret handling, persisted PII,
  network egress, MCP server exposure). Result: 0 CRITICAL, 0 HIGH,
  0 MEDIUM, 1 LOW (pre-existing, accepted), 1 INFO (accepted).
- Senior-architect architecture review report at
  `.trae/specs/prepare-0.2.0-release/architecture-review.md` with
  prioritized findings (2 P0 fixed, 6 P1 + 5 P2 deferred to follow-up
  specs) and four ADR candidates.

### Changed

- `hooks/adapters.py` event normalization extended for Telegram events
  with type-safe `getattr` + `isinstance` checks and 128-char field
  limits on `conversation_id`, `user_id`, and `message_id`.
- `permissions/service.py` integrates Telegram permission resolution via
  the platform registry; superuser bypass remains explicit and
  fail-closed for anonymous principals.
- `platforms/registry.py` registers the Telegram platform profile
  (`PlatformProfile` + `ProtocolImplementationInfo`).
- `handle/qq/adapters/__init__.py` and `handle/menu.py` adapter module
  registry extended to load `~telegram` adapter handlers at startup.
- `runtime_settings.py` extended for Telegram adapter selection.

### Fixed

- Fixed `NameError: name 'GroupMessageEvent' is not defined` on startup
  when Telegram handlers used `from __future__ import annotations`.
  NoneBot resolves signature forward refs via `wrapper.__globals__` (the
  `common.py` module globals), not `func.__globals__`; `@wraps` copies
  `__wrapped__`/`__name__`/`__annotations__` but NOT `__globals__`, so
  adapter-specific event types became unresolvable. Removed
  `from __future__ import annotations` from the five Telegram handler
  files (`bot_state.py`, `menu.py`, `moderation.py`, `mute.py`,
  `recall.py`) and added a root-cause comment at
  `handle/qq/commands/common.py::_state_wrapper`.
- Fixed `ModuleNotFoundError: No module named 'src'` in installed-package
  environments: the `handle/qq/adapters/telegram/default/__init__.py`
  compatibility shim used `from src.plugins...` absolute import;
  switched to package-relative
  `from nonebot_plugin_lingchu_bot.handle.telegram.adapters.default import import_handle`.

### Security

- Full-project security audit completed ahead of the 0.2.0 release. The
  audit used the `TRAE-security-review` skill on both the worktree diff
  and the `src/` baseline, plus parallel Sub-Agent deep sweeps over
  `services/mcp_server/`, `services/llm/`, `permissions/`, `hooks/` +
  `handle/`, and the `lingchu` CLI. No HIGH/CRITICAL findings were
  identified. The 1 LOW finding (pre-existing
  `ensure_mcp_server_config_file_async` creates config on startup — a
  constraint violation rather than a security vulnerability) and the 1
  INFO finding (post-send audit exception swallowed by design) are
  accepted with documented rationale and tracked for follow-up.

### Release Notes

- Software code remains under `LGPL-3.0-or-later`.
- Documentation remains under `GFDL-1.3-or-later`.
- Visual elements remain under `CC0-1.0`.

## [0.1.0] - 2026-07-27

First minor release. The jump from `0.0.1` to `0.1.0` reflects significant
accumulated changes: TOML configuration migration, multi-database support,
LLM service integration, docs site, CLI tooling, and smoke test enhancement.

### Added

- Docs site home hero: full-bleed p5.js "Organic Turbulence" flow-field
  sketch with layered Perlin noise, steered particles, accumulating trails,
  velocity-mapped color, and `prefers-reduced-motion` support.
- Dependency-free shadcn-style `Badge` and `Alert` components for the docs
  site, reading Starlight theme tokens and adapting to light/dark mode.
- Global style polish for the docs site: accent-tinted selection color,
  refined theme-aware scrollbars, hero banner layout, card hover glow,
  feature grid, and inline code/block refinement.
- Three-stage runtime smoke test flow (dev env / prod env clean-localstore /
  CLI tool verification) documented across `AGENTS.md`, `CLAUDE.md`,
  `.github/note/AGENTS-zh.md`, and both EN/zh `testing-ci.mdx` pages.
- Non-Docker prod-env smoke test job (`smoke-test-prod-env`) in
  `👷-ci-builds.yml`, validating schema-write-free startup on a pristine
  runner without Docker-specific defaults.
- `lingchu config init` now seeds `llm.toml` from `LINGCHU_AI_*` environment
  variables, enabling zero-touch LLM profile bootstrap in containerized and
  CI environments.

### Changed

- **Breaking:** replaced all Lingchu-owned JSON5 configuration and state files
  with TOML backed by `rtoml`. Legacy `.json5` files are not read, migrated, or
  backed up; recreate configuration as `.toml`. Optional `None` values are
  represented by omitted keys, and programmatic writes do not preserve custom
  comments or formatting.
- Refreshed governance and documentation infrastructure: realigned
  `AGENTS.md`, `CLAUDE.md`, and `.github/note/AGENTS-zh.md` under the CREATE
  framework; corrected README environment variable tables (added `LINGCHU_`
  prefix) and pinned Python 3.13 / Node.js 24+ requirements; completed the CI
  workflow list and husky pre-commit description in `CONTRIBUTING.md`; expanded
  the PR template checklist; exposed the orphan `user-guide/deployment/tipo-llama-cpp`
  page and added 7 bilingual architecture doc pairs
  (permissions, i18n-runtime, storage-orm, llm-service, scheduler,
  platform-registry, api-audit) under `apps/docs`.

### Deprecated

### Removed

- Removed legacy `.serena/` tool configuration directory (cleanup of a
  deprecated tool's残留).

### Fixed

- Corrected project brand name from "灵枢" to "灵初" across docs site
  (hero eyebrow, sketch concept, integration guide).
- Fixed hero p5.js animation layout: Astro `client:load` wraps the island
  in `<astro-island>`, breaking the `>` child selector; the canvas now
  correctly overlays behind the hero content instead of sitting side-by-side.
- Fixed quick-navigation cards being non-clickable: Starlight `Card` component
  does not support `href`; cards are now wrapped in `<a>` tags for navigation.
- Fixed `_LLMConfigError` on `nb run` startup when `llm.toml` is missing or
  empty: `ensure_llm_config_file_async()` no longer creates the file at
  startup; `load_llm_runtime_config()` falls through to an empty mapping and
  emits an actionable warning instead of a traceback.
- Fixed Windows ESLint failure caused by `brace-expansion@5.x` (ESM-only)
  being forced onto `minimatch@9.0.9` (expects CJS default export); added a
  targeted `minimatch@9.0.9>brace-expansion` override to `^2.1.2` (not
  affected by CVE-2026-14257) while keeping the global `^5.0.8` security fix.

### Security

- `brace-expansion` overridden to `^5.0.8` globally to mitigate
  CVE-2026-14257 / GHSA-mh99-v99m-4gvg (DoS via memory exhaustion).

### Release Notes

- Software code remains under `LGPL-3.0-or-later`.
- Documentation remains under `GFDL-1.3-or-later`.
- Visual elements remain under `CC0-1.0`.

## [0.0.1] - 2026-07-06

Initial formal release for QQ group management through OneBot V11.

### Added

- QQ group management commands for member moderation, speech management, group operations, remote management, bot control, and dynamic menus.
- Runtime permission, protection, i18n, message storage, and API audit support.
- Docker runtime support and documentation site.
- Multi-database test coverage across SQLite, PostgreSQL, MySQL, MariaDB, Oracle, and SQL Server.

### Release Notes

- Software code remains under `LGPL-3.0-or-later`.
- Documentation remains under `GFDL-1.3-or-later`.
- Visual elements remain under `CC0-1.0`.

[Unreleased]: https://github.com/xinvxueyuan/lingchu-bot/compare/v0.6.2...HEAD
[0.6.2]: https://github.com/xinvxueyuan/lingchu-bot/releases/tag/v0.6.2
[0.6.1]: https://github.com/xinvxueyuan/lingchu-bot/releases/tag/v0.6.1
[0.5.0]: https://github.com/xinvxueyuan/lingchu-bot/releases/tag/v0.5.0
[0.4.1]: https://github.com/xinvxueyuan/lingchu-bot/releases/tag/v0.4.1
[0.4.0]: https://github.com/xinvxueyuan/lingchu-bot/releases/tag/v0.4.0
[0.3.0]: https://github.com/xinvxueyuan/lingchu-bot/releases/tag/v0.3.0
[0.2.0]: https://github.com/xinvxueyuan/lingchu-bot/releases/tag/v0.2.0
[0.1.0]: https://github.com/xinvxueyuan/lingchu-bot/releases/tag/v0.1.0
[0.0.1]: https://github.com/xinvxueyuan/lingchu-bot/releases/tag/v0.0.1
