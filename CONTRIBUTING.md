# 贡献指南

欢迎您参与 **Lingchu Bot** 项目的贡献！本指南旨在帮助贡献者顺利参与协作、提交代码与文档。我们鼓励各种形式的贡献，包括代码改进、文档编写、测试添加、问题报告和功能建议。

---

## 目录

- [贡献指南](#贡献指南)
  - [目录](#目录)
  - [贡献流程](#贡献流程)
  - [分支与工作流](#分支与工作流)
    - [示例操作](#示例操作)
  - [提交规范](#提交规范)
    - [示例](#示例)
  - [Pull Request 要求](#pull-request-要求)
  - [代码风格与质量](#代码风格与质量)
  - [测试与 CI](#测试与-ci)
  - [文档与翻译](#文档与翻译)
  - [报告 Issue 与请求新功能](#报告-issue-与请求新功能)
  - [社区守则与联系方式](#社区守则与联系方式)
  - [贡献许可与署名](#贡献许可与署名)
  - [常见问题解答](#常见问题解答)
  - [资源与链接](#资源与链接)

---

## 贡献流程

我们欢迎所有贡献者参与项目开发。以下是标准的贡献流程：

1. **讨论与规划**：对于重大改动或新功能，请先在 [Issues](https://github.com/lingchu-bot/lingchu-bot/issues) 中讨论，获取维护者反馈。
2. **设置环境**：Fork 仓库，克隆到本地，并设置开发环境（详见 [README.md](README.md)）。
3. **创建分支**：基于 `dev` 分支创建功能或修复分支。
4. **实现改动**：编写代码、添加测试，并确保通过本地检查。
5. **提交 PR**：推送分支并发起 Pull Request，提供详细描述。
6. **审查与合并**：通过代码审查、CI 测试后，维护者将合并您的贡献。

如果您是首次贡献者，建议从修复小错误或添加单元测试开始，以熟悉代码库。

---

## 分支与工作流

项目采用 Git Flow 工作流：

- **主分支**：
  - `main`：稳定发布分支，仅用于正式版本。
  - `dev`：日常开发分支，所有新功能在此合并。

- **分支命名**：
  - 功能分支：`feature/描述`，例如 `feature/add-login-api`。
  - 修复分支：`fix/描述`，例如 `fix/readme-typo`。
  - 发布分支：`release/v1.2.0`。

### 示例操作

```bash
# 从 dev 创建功能分支
git checkout dev
git pull origin dev
git checkout -b feature/your-feature-name

# 开发完成后提交
git add .
git commit -m "feat: 添加用户登录功能"
git push origin feature/your-feature-name
```

外部贡献者请 Fork 仓库，基于 Fork 的 `dev` 创建分支，然后发起 PR 到上游 `dev` 分支。

---

## 提交规范

提交信息应清晰、简洁，并遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

- **格式**：`<type>(<scope>): <description>`
  - `type`：如 `feat`（新功能）、`fix`（修复）、`docs`（文档）、`style`（格式）、`refactor`（重构）、`test`（测试）、`chore`（杂项）。
  - `scope`：可选，影响范围，如 `api`、`ui`。
  - `description`：简短描述。

### 示例

- `feat: 添加用户认证接口`
- `fix: 修复数据库连接超时问题`
- `docs: 更新 API 文档`

避免提交调试代码、大文件或无关改动。若修改公共 API，请在提交信息中注明兼容性。

---

## Pull Request 要求

每个 PR 应包含以下内容：

- **标题**：清晰描述改动。
- **描述**：包括目的、实现思路、影响范围和测试说明。
- **关联 Issue**：使用 `Closes #123` 引用相关 Issue。
- **变更清单**：
  - [ ] 代码通过 lint 和格式检查。
  - [ ] 添加或更新相关测试。
  - [ ] 更新文档（如需要）。
  - [ ] 通过本地测试。

PR 将由维护者审查，重点关注代码质量、性能和安全性。请耐心等待反馈，并根据建议修改。

---

## 代码风格与质量

- **语言**：项目使用 Python，主要遵循 PEP 8 标准。
- **工具**：使用 `ruff` 进行代码检查和格式化。运行 `ruff check` 和 `ruff format` 确保代码质量。
- **原则**：
  - 函数职责单一，避免复杂逻辑。
  - 添加适当注释和文档字符串。
  - 处理边界条件和异常。

新增功能务必包含单元测试。使用 `pytest` 运行测试。

---

## 测试与 CI

- **本地测试**：提交前运行 `pytest` 执行所有测试。
- **CI 流程**：PR 触发 GitHub Actions，自动运行 lint、测试和构建。
- **覆盖率**：目标测试覆盖率 > 80%。使用 `coverage` 工具检查。

若 PR 需要特殊环境，请在描述中提供复现步骤。

---

## 文档与翻译

- **更新文档**：新增功能时，更新 [docs/](docs/) 目录下的相关文件。
- **格式**：使用 Markdown，保持一致性。
- **翻译**：欢迎提供多语言支持，保持术语一致。

文档是项目的重要组成部分，请确保其准确和易懂。

---

## 报告 Issue 与请求新功能

高质量 Issue 有助于快速解决问题：

- **标题**：简洁概述。
- **描述**：包括复现步骤、预期/实际结果、环境信息（OS、Python 版本等）。
- **标签**：使用 `bug`、`enhancement` 等。
- **示例**：提供最小复现代码。

功能请求请说明使用场景和替代方案。

---

## 社区守则与联系方式

我们致力于创建友好、包容的社区：

- 尊重他人观点，避免攻击性语言。
- 保持专业，提供建设性反馈。

联系方式：通过 [Issues](https://github.com/lingchu-bot/lingchu-bot/issues) 或 [Discussions](https://github.com/lingchu-bot/lingchu-bot/discussions) 与维护者沟通。

---

## 贡献许可与署名

提交贡献即表示同意在项目许可下发布（详见 [LICENSE](LICENSE-code)）。贡献者将获得署名。

---

## 常见问题解答

**Q: 如何设置开发环境？**  
A: 参考 [README.md](README.md) 的安装指南。

**Q: PR 被拒绝怎么办？**  
A: 查看反馈，修改后重新提交，或在 Issue 中讨论。

**Q: 我可以贡献什么？**  
A: 代码、文档、测试、设计等任何有益内容。

---

## 资源与链接

- [项目主页](https://github.com/lingchu-bot/lingchu-bot)
- [文档](docs/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)

感谢您的贡献！如果有疑问，请随时提问。
