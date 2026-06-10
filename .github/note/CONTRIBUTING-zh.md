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
pnpm exec markdownlint-cli2 "apps/**/*.md" "packages/**/*.md" "!**/node_modules/**" "!**/out/**" "README.md" "CHANGELOG.md" "CONTRIBUTING.md" "CODE_OF_CONDUCT.md" "Repository-Policy.md" ".github/**/*.md"
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

## 提交规范

提交信息必须符合 gitmoji + Conventional Commits。首行由 `.husky/commit-msg` 强制校验，详细规则见 [.trae/rules/git-commit-message.md](../.trae/rules/git-commit-message.md)。

```text
📝 docs: 重写贡献指南
🐛 fix(mute): 修复禁言失败反馈
✅ test(database): 覆盖 JSON5 存储异常分支
```

可运行 `task gitmoji` 查看中文速查表。交互式提交时，`.husky/prepare-commit-msg` 会尽量启动 `pnpm exec gitmoji --hook`；非交互环境可跳过交互钩子，但仍必须自行保证首行格式正确。

## Pull Request 要求

PR 描述应包含：

- 改动目的和用户可见效果。
- 关键实现点，尤其是公共接口、命令行为、配置、数据结构或兼容性变化。
- GitNexus/codegraph 影响分析结果；如果是 docs-only，可说明未修改代码符号。
- 已运行的检查命令和结果。
- 关联 Issue，例如 `Closes #123`。
- 任何未完成事项、已知风险或需要维护者确认的取舍。

## CI 与失败处理

- PR 会触发 GitHub Actions；`main` 和 `dev` 的 push 也会触发主要 CI。
- `🧪 CI` 的 Static Analysis 运行 `task ci:static`；Tests & Type Check 运行 Pyright、ty 和 pytest；Docs Check 运行 Turbo lint/type check 和 docs test。
- `👷 CI-builds` 运行 `task ci:build`；在 `main`、`dev`、`releases/**` 的 push 上还会执行版本写入、构建产物归档、来源证明和 tag 流程。
- `📚 文档部署` 在 docs 相关路径 push 到 `main` 或 `dev` 时运行 pnpm/turbo lint、docs test 和 docs build，然后部署 GitHub Pages。
- `main` 和 `dev` push 上的 auto-format job 会运行 `task ci:fix` 并可能自动提交格式修复。

如果 CI 失败，先打开失败 job 的日志，定位具体命令、规则和行号。修 CI 时只改导致失败的最小范围，并重新跑对应本地命令验证。

## Issue 与沟通

报告问题时请提供：

- 简短标题。
- 复现步骤。
- 预期结果和实际结果。
- 环境信息，例如系统、Python 版本、适配器或命令输入。
- 相关日志、截图或最小复现示例。

功能请求请说明使用场景、期望行为和可接受的取舍。安全问题请参考 [SECURITY.md](../../SECURITY.md)。

## 许可与行为准则

提交贡献即表示同意按本仓库许可发布。代码、文档和媒体文件的许可要求见 [Repository-Policy.md](../../Repository-Policy.md) 和相关许可证文件。

参与讨论和审查时请遵守 [CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md)。保持具体、尊重和可验证，是让协作顺滑的最好方式。
