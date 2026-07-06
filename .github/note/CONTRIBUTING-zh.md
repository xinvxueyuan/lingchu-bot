# 贡献指南

> [English](../../CONTRIBUTING.md) | 中文

欢迎参与 Lingchu Bot。项目欢迎代码、测试、文档、问题报告和功能建议；贡献时请保持改动小而清晰，让维护者能快速理解意图、影响面和验证结果。

## 贡献前准备

- 使用 Python 3.13。
- 使用 `uv` 管理 Python 环境和依赖。
- 使用 `pnpm` 管理文档站和前端工作区依赖。
- 使用 `Taskfile.yml` 作为本地自动化主入口。

```bash
task install
```

`task install` 会执行 `uv sync` 和 `pnpm install`。如果只处理单侧改动，也可以分别运行 `uv sync --frozen` 或 `pnpm install --frozen-lockfile`。

开始前请阅读 [README.md](../../README.md)、[Repository-Policy.md](../../Repository-Policy.md) 和 [CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md)。提交媒体、截图或示例数据时，遵守仓库策略中的许可和脱敏要求。

## 本地开发环境搭建

### 前置条件

- Python 3.13（由 `uv` 管理）
- Node.js 22+ 和 pnpm（用于文档站和前端工作区）
- git

### 分步搭建

1. 克隆仓库并进入项目目录：

   ```bash
   git clone https://github.com/xinvxueyuan/lingchu-bot.git
   cd lingchu-bot
   ```

2. 使用 `uv` 安装 Python 依赖：

   ```bash
   uv sync --frozen
   ```

3. 使用 `pnpm` 安装 Node.js 依赖：

   ```bash
   pnpm install --frozen-lockfile
   ```

4. 或使用 Taskfile 一次性安装两者：

   ```bash
   task install
   ```

5. 将 `.env.example` 复制为 `.env`，并根据你的环境调整配置值：

   ```bash
   cp .env.example .env
   ```

6. 安装 Git hooks（husky）：

   ```bash
   pnpm exec husky
   ```

   这通常由 `pnpm install` 自动安装。通过检查 `.husky/` 是否存在来验证 hooks 是否已激活。

7. 运行检查以验证环境：

   ```bash
   task check
   task test
   ```

   如果两者都通过，开发环境即准备就绪。

## 工具链

- `Taskfile.yml`：统一封装安装、检查、测试、构建、修复、版本和 i18n 流程。
- `uv`：Python 依赖、虚拟环境、Ruff、Pyright、ty、pytest、Babel 和构建命令入口。
- `pnpm`：Node 工作区、docs 应用、Turbo、Gitmoji、Markdown lint 和前端依赖入口。
- `turbo`：编排 docs 与 packages 的 lint、type check、build 等任务。
- `husky`：安装 Git hooks；`pre-commit` 运行 prek 和 GitNexus 分析，`commit-msg` 校验提交信息，`prepare-commit-msg` 尝试启动 Gitmoji 交互。
- `prek`：通过 `prek.toml` 运行 pre-commit hooks，检查空白、换行、YAML/TOML/JSON/XML、合并冲突、大文件、私钥和大小写冲突等。
- GitNexus / codegraph：用于代码理解、影响分析、变更范围检查和安全重构。
- Context7：用于查询当前库、框架、SDK、CLI 或云服务文档；不要用它替代业务逻辑分析或代码审查。

## 工作流程

1. 先确认问题、成功标准、不做的范围和影响面。需求不清时，先在 Issue 或 PR 讨论中补齐上下文。
2. 开始前运行 `git status --short`，识别已有改动。不要回退、格式化或重写与当前任务无关的文件。
3. 按目标 PR 分支创建工作分支；常见目标分支是 `main` 或 `dev`，功能/修复分支通常使用 `feature/`、`fix/`、`hotfix/` 或 `releases/` 前缀，以维护者或 PR 页面要求为准。
4. 对较大的功能、重构或行为变化，先写计划，再实施。计划应说明目标、关键改动、测试方案和假设。
5. 实施时优先沿用仓库已有结构、工具和风格。保持改动范围最小，避免顺手重构。
6. 修改代码后运行必要检查，并在 PR 中写明实际执行过的命令和结果。

## 代码智能要求

修改 Python、TypeScript 或共享逻辑前，先用 GitNexus/codegraph 理解现有结构。修改函数、类或方法前必须做 upstream 影响分析，并在说明或 PR 中记录直接调用者、受影响流程和风险等级。

```text
gitnexus_impact({target: "symbolName", direction: "upstream"})
```

- 如果影响分析为 `HIGH` 或 `CRITICAL`，先暂停并说明风险，不要直接继续改动。
- 探索陌生代码时，优先用 GitNexus query/context 或 codegraph 查执行流和符号上下文。
- 提交前运行 GitNexus detect changes，确认变更只影响预期符号和执行流。
- 重命名符号时使用图工具支持的 rename 流程，不要用全局查找替换。
- docs-only 改动可在 PR 中说明未修改代码符号；仍应说明已用搜索或索引核对相关事实。

## 开发与验证命令

优先使用 Taskfile 的高层任务：

```bash
task check      # 静态检查、格式检查、Markdown、lint、类型检查
task test       # Python 测试 + docs 测试
task build      # 构建所有工作区
task ci         # check + test + build
task i18n       # 提取、更新并编译 gettext catalog
```

聚焦 Python/code 改动时，可以直接运行：

```bash
uv run -m ruff check . --output-format=github
uv run -m ruff format --check .
uv run -m pyright .
uv run -m ty check --output-format github
uv run -m pytest
```

聚焦 docs/frontend 改动时，可以直接运行：

```bash
pnpm --filter docs lint
pnpm --filter docs test
pnpm --filter docs run lint:links
pnpm turbo run build --filter=docs
```

Markdown 检查：

```bash
pnpm exec markdownlint-cli2
```

需要自动修复格式时，优先对相关文件运行聚焦命令，避免把无关文件卷进 PR：

```bash
uv run -m ruff format path/to/file.py
uv run -m ruff check --fix path/to/file.py
```

## 代码与测试原则

- 使用仓库已有模式，不为单个小改动引入新框架或新抽象。
- 处理用户可见行为、错误分支、边界条件和异步流程时补充测试。
- 修 bug 时优先写能复现问题的测试，再修实现。
- 未知异常不要随意吞掉；只捕获能明确处理并能给用户可读反馈的异常。
- 注释应解释不明显的原因或约束，不重复代码本身。
- 文档改动应简洁、可执行，避免和 CI、Taskfile 或实际目录结构不一致。
- Python 代码遵循 Ruff 规则（见 `pyproject.toml` 的 `[tool.ruff]`）。提交前运行 `uv run -m ruff check .` 和 `uv run -m ruff format --check .`。
- TypeScript 代码遵循 ESLint 规则（见 `packages/eslint-config/`）。提交前运行 `pnpm turbo run lint`。
- 函数签名参数数量应 ≤ 5（Ruff `PLR0913`）。如有需要，将相关参数合并为单个对象。
- 测试文件必须避免硬编码模块路径；改用直接对象引用。
- 迁移文件时，更新所有依赖引用（测试、i18n、文档、配置）以反映新路径。

## 提交规范

提交信息必须符合 gitmoji + Conventional Commits。首行由 `.husky/commit-msg` 强制校验，详细规则见 [.trae/rules/git-commit-message.md](../../.trae/rules/git-commit-message.md)。

```text
📝 docs: 重写贡献指南
🐛 fix(mute): 修复禁言失败反馈
✅ test(database): 覆盖 JSON5 存储异常分支
```

可运行 `task gitmoji` 查看中文速查表。交互式提交时，`.husky/prepare-commit-msg` 会尽量启动 `pnpm exec gitmoji --hook`；非交互环境可跳过交互钩子，但仍必须自行保证首行格式正确。

## 版本验证系统

Lingchu Bot 通过 CI 构建工作流自动化版本 bump。`👷-ci-builds.yml` 的 `versioned-build` job 从**分支名**推导 bump 级别与预发布段，因此正确命名 release 分支是贡献流程的一部分。

### 分支名约定

| 分支前缀 | `BUMP_LEVEL` | `BUMP_PRERELEASE` | 版本语义 |
| --- | --- | --- | --- |
| `dev-major-*` | `major` | （见预发布列） | 破坏性版本 bump，如 `1.0.0` |
| `dev-minor-*` | `minor` | （见预发布列） | 功能 bump，如 `0.1.0` |
| 其他 `dev-*` | `patch` | （见预发布列） | 补丁 bump，如 `0.0.2` |

预发布段独立推导：

| 分支前缀 | `BUMP_PRERELEASE` | 示例 tag |
| --- | --- | --- |
| `dev-alpha-*` | `alpha` | `0.1.0a1` |
| `dev-beta-*` | `beta` | `0.1.0b1` |
| `dev-rc-*` | `rc` | `0.1.0rc1` |
| `dev-stable-*` | `stable`（清除预发布段） | `0.1.0` |
| 其他 `dev-*` | `dev` | `0.1.0.dev1` |

### 校验任务

版本变更通过 `Taskfile.yml` 中三个受保护任务：

- `task ci:version:bump` — 接受 `BUMP_LEVEL`（默认 `patch`）与 `BUMP_PRERELEASE`（默认 `dev`）。智能处理 stable 与 pre-release tag：stable 标签需同时提供 level 与预发布段，同类 pre-release 标签仅 bump 预发布计数，`stable` 清除预发布段。
- `task ci:version:precheck` — 在版本写入前运行。校验 PEP 440 合规、候选版本大于所有现有 tag、源文件一致性（advisory）、拒绝重复 tag。
- `task ci:version:postcheck` — 在 `ci:version:write-config` 后运行。调用 `release:verify-version` 并校验 dev release 语义，确保损坏的版本不会进入构建产物。

提 release PR 时，请按上述前缀命名分支以匹配预期的 bump 与预发布语义。其余由 CI 完成；不要在 release 分支上手编辑 `core/config.py` 或 `package.json` 版本。

## Pull Request 要求

PR 描述应包含：

- 改动目的和用户可见效果。
- 关键实现点，尤其是公共接口、命令行为、配置、数据结构或兼容性变化。
- GitNexus/codegraph 影响分析结果；如果是 docs-only，可说明未修改代码符号。
- 已运行的检查命令和结果。
- 关联 Issue，例如 `Closes #123`。
- 任何未完成事项、已知风险或需要维护者确认的取舍。

### PR 命名规范

- PR 标题使用 `<type>(<scope>): <subject>` 格式，与提交信息风格一致（不含 gitmoji 前缀）。
- PR 标题控制在 50 字符以内。
- 使用小写 scope 名称：`auth`、`db`、`api`、`i18n`、`docs`、`frontend`、`core`、`handle`、`platforms`、`permissions`、`repositories`、`services`、`tests`。
- 在 PR 描述中使用 `Closes #123` 或 `Fixes #123` 关联相关 Issue。
- 破坏性变更在 type/scope 后加 `!`，并在 PR 正文中说明破坏性变更内容。

### PR 检查清单

请求审查前，逐项确认：

- 提交带 `Signed-off-by:` 尾注（开发者原创证书 DCO 1.1，见 <https://developercertificate.org/>）。`.husky/commit-msg` 流程会自动追加；若你 amend 或 rebase，请确认它仍存在。
- 用户可见行为、配置或兼容性变更在 `CHANGELOG.md` 的 `## [Unreleased]` 下有对应条目。
- 代码改动包含 GitNexus 影响分析结果（或说明未修改代码符号）。
- 已运行快速验证矩阵中相关检查并通过。
- Release PR（分支 `releases/**`）额外确认：版本由 `task ci:version:write-config` 写入、`ci:version:precheck` 与 `ci:version:postcheck` 均通过、构建产物带 SLSA Build L3 来源证明（`gh attestation verify` 命令见 [SECURITY.md](../../SECURITY.md)）。

## CI 与失败处理

- PR 会触发 GitHub Actions；`main` 和 `dev` 的 push 也会触发主要 CI。
- `🧪 Python CI` 的 Static Analysis 运行 `task ci:static`，Tests & Type Check 运行 Pyright、ty 和 pytest（多数据库矩阵）；`🧪 Frontend CI` 运行 Docs Check（Turbo lint、type check、link validation、docs test）。
- `👷 CI-builds` 运行 `task ci:build`；在 `main`、`dev`、`releases/**` 的 push 上还会执行版本写入、构建产物归档、来源证明和 tag 流程。
- `📚 Docs Deploy` 在 docs 相关路径 push 到 `main` 或 `dev` 时运行 pnpm/turbo lint、docs test 和 docs build，然后部署 GitHub Pages。
- `🧪 Python CI` 中 `main` 和 `dev` push 上的 auto-format job 会运行 `task ci:fix` 并可能自动提交格式修复。

如果 CI 失败，先打开失败 job 的日志，定位具体命令、规则和行号。修 CI 时只改导致失败的最小范围，并重新跑对应本地命令验证。

## 发布流程

正式版本使用 `releases/<version>` 分支。

1. 运行 `task release:prepare VERSION=0.0.1`。
2. 更新 `CHANGELOG.md`、`.github/releases/0.0.1.md`、README 状态说明和策略记录。
3. 运行 `task check && task test && task ci:build && task smoke`。
4. 通过 `task release:publish VERSION=0.0.1` 推送发布分支。
5. 验证 PyPI、GHCR 和 GitHub Release 产物。

发布工作流会在构建产物前运行 `scripts/clean-release-infra.sh`，避免 agent、CI 和本地工作区基础设施被复制进分发输出。
GitHub Release 正文来自 `.github/releases/<version>.md`；推送发行分支前应与 changelog 一起审阅该文件。

发布使用短期 OIDC 凭据，仓库中不存储长期包令牌：

- **PyPI** 通过 Trusted Publishing / OIDC 发布。PyPI 项目已配置信任本仓库 `🚀-release.yml` 工作流在 `releases/**` 分支 ref 上的发布。
- **GHCR**（`ghcr.io/xinvxueyuan/lingchu-bot`）使用临时 `GITHUB_TOKEN` 推送，权限为 `packages: write`。
- 构建产物（`dist/*`）通过 `actions/attest-build-provenance@v4.1.0` 生成 SLSA Build L3 来源证明。消费者可运行的 `gh attestation verify` 命令见 [SECURITY.md](../../SECURITY.md)。

## 代码审查流程

1. **自审**：请求审查前，重新阅读你的 diff，确认每处改动都是有意的。
2. **自动化检查**：CI 必须通过。如果检查失败，修复根本原因，而不是抑制警告。
3. **审查者分配**：维护者根据改动区域分配审查者。至少需要一位审查者批准。
4. **审查标准**：
   - 改动最小且聚焦于既定目标。
   - 测试覆盖新行为、错误分支和边界情况。
   - 没有无关的重构或格式化改动。
   - 公共接口、配置和数据结构变更已文档化。
   - 代码改动包含 GitNexus 影响分析。
5. **回应反馈**：回复每条评论。以新提交方式推送修复（审查期间不要 force-push，除非被要求）。
6. **合并**：维护者在审查通过且 CI 通过后合并 PR。默认采用 squash-merge 策略。

## Issue 与沟通

报告问题时请提供：

- 简短标题。
- 复现步骤。
- 预期结果和实际结果。
- 环境信息，例如系统、Python 版本、适配器或命令输入。
- 相关日志、截图或最小复现示例。

功能请求请说明使用场景、期望行为和可接受的取舍。安全问题请参考 [SECURITY.md](../../SECURITY.md)。

## 许可与行为准则

本项目采用**分阶段开源许可证栈**，详见
[Repository-Policy.md](../../Repository-Policy.md)。当前阶段覆盖
LGPL-3.0-or-later（代码）、FDL-1.3-or-later（文档）和 CC0-1.0
（视觉元素）；未来阶段在首次公开发行后一年 或 首次主版本变更
（取较早者）自动触发，覆盖 MIT-or-later 或 Apache-2.0-or-later（代码）
以及 CC-BY-SA-4.0-or-later（文档和视觉元素）。切换仅作用于触发日（含）之后
提交的贡献。

提交贡献即表示您接受 [CLA.md](../../CLA.md) 的条款，该协议授予本项目
执行上述切换所需的权利。

参与讨论和审查时请遵守 [CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md)。
保持具体、尊重和可验证，是让协作顺滑的最好方式。
