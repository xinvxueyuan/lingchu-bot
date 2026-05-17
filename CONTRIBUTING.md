# 贡献指南

欢迎参与 Lingchu Bot。这个项目欢迎代码、测试、文档、问题报告和功能建议；贡献时请尽量保持改动小而清晰，让维护者能快速理解意图、影响面和验证结果。

## 贡献前准备

- 使用 Python 3.13。
- 使用 `uv` 管理环境和依赖：

```bash
uv sync --frozen
```

- 开始前请阅读 [README.md](README.md)、[Repository-Policy.md](Repository-Policy.md) 和 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。
- 提交媒体、截图或示例数据时，遵守仓库策略中的许可和脱敏要求。

## 工作流程

1. 先确认问题、成功标准和影响范围。需求不清时，先在 Issue 或 PR 讨论中补齐上下文。
2. 开始前运行 `git status --short`，识别已有改动。不要回退、格式化或重写与当前任务无关的文件。
3. 按目标 PR 分支创建工作分支；常见目标分支是 `main` 或 `dev`，以维护者或 PR 页面要求为准。
4. 对较大的功能、重构或行为变化，先写计划，再实施。计划应说明目标、关键改动、测试方案和假设。
5. 实施时优先沿用仓库已有结构、工具和风格。保持改动范围最小，避免顺手重构。
6. 修改代码后运行必要检查，并在 PR 中写明实际执行过的命令和结果。

建议的分支命名：

- `feature/<short-description>`
- `fix/<short-description>`
- `docs/<short-description>`
- `refactor/<short-description>`

## GitNexus 代码智能要求

本仓库使用 GitNexus 辅助理解代码和评估影响面。修改函数、类或方法前必须先做影响分析。

- 修改符号前运行 upstream impact，例如：

```text
gitnexus_impact({target: "symbolName", direction: "upstream"})
```

- 在说明或 PR 中记录影响面：直接调用者、受影响流程和风险等级。
- 如果影响分析为 `HIGH` 或 `CRITICAL`，先暂停并说明风险，不要直接继续改动。
- 探索陌生代码时，优先用 GitNexus query/context 查执行流和符号上下文。
- 提交前运行 GitNexus detect changes，确认变更只影响预期符号和执行流。
- 重命名符号时使用 GitNexus rename，不要用全局查找替换。

## 开发与验证命令

CI 当前会检查 Ruff、Markdown、Pyright、ty 和 pytest。提交前尽量在本地跑与改动相关的检查。

Ruff 检查和格式检查：

```bash
uv run -m ruff check . --output-format=github
uv run -m ruff format --check .
```

类型检查：

```bash
uv run -m pyright .
uv run -m ty check --output-format github
```

测试：

```bash
uv run -m pytest
```

只改文档时，至少确认 Markdown 可以通过 CI 的 Markdown Check；如果本地没有 markdownlint，可在 PR 中说明已人工检查标题层级、链接和代码块围栏。

需要自动修复格式时，请只对相关文件运行格式化命令，避免把无关文件卷进 PR：

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
- 文档改动应简洁、可执行，避免和 CI 或实际目录结构不一致。

## Pull Request 要求

PR 描述应包含：

- 改动目的和用户可见效果。
- 关键实现点，尤其是公共接口、命令行为、配置、数据结构或兼容性变化。
- GitNexus 影响分析结果；如果是 docs-only，可说明未修改代码符号。
- 已运行的检查命令和结果。
- 关联 Issue，例如 `Closes #123`。
- 任何未完成事项、已知风险或需要维护者确认的取舍。

提交信息建议遵循 Conventional Commits：

```text
fix: 修复成员禁言成功反馈
docs: 重写贡献指南
test: 增加禁言异常处理覆盖
```

## CI 与失败处理

- PR 会触发 GitHub Actions；`main` 和 `dev` 的 push 也会触发 CI。
- Static Analysis 会运行 Ruff 和 Markdown Check。
- Tests & Type Check 会运行 Pyright、ty 和 pytest。
- 如果 CI 失败，先打开失败 job 的日志，定位具体命令、规则和行号。
- 修 CI 时只改导致失败的最小范围，并重新跑对应本地命令验证。

## Issue 与沟通

报告问题时请提供：

- 简短标题。
- 复现步骤。
- 预期结果和实际结果。
- 环境信息，例如系统、Python 版本、适配器或命令输入。
- 相关日志、截图或最小复现示例。

功能请求请说明使用场景、期望行为和可接受的取舍。安全问题请参考 [SECURITY.md](SECURITY.md)。

## 许可与行为准则

提交贡献即表示同意按本仓库许可发布。代码、文档和媒体文件的许可要求见 [Repository-Policy.md](Repository-Policy.md) 和相关许可证文件。

参与讨论和审查时请遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。保持具体、尊重和可验证，是让协作顺滑的最好方式。
