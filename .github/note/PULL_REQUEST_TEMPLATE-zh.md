# 拉取请求

> 提交前请阅读 [CONTRIBUTING.md](../../CONTRIBUTING.md) 与
> [Repository-Policy.md](../../Repository-Policy.md)；英文模板见
> [.github/PULL_REQUEST_TEMPLATE.md](../PULL_REQUEST_TEMPLATE.md)。

感谢你抽出时间贡献 Lingchu Bot！请填写以下章节，便于审查者快速理解
改动意图、影响范围与验证方式。

## 概要

<!-- 1-3 句话：本次 PR 做了什么、为什么。 -->

## 关联 Issue

<!-- 关联的 Issue：Closes #123、Fixes #456、Refs #789。 -->

## 改动类型

<!-- 在适用的方框中填入 `x`。 -->

- [ ] Bug 修复（不影响现有功能的修复）
- [ ] 新功能（不影响现有功能的添加）
- [ ] 破坏性变更（修复或功能会导致现有行为变化）
- [ ] 文档更新
- [ ] 重构 / 清理
- [ ] 构建 / CI / 工具
- [ ] 仅测试

## 提交前自检

<!-- 确认后在每个方框中填入 `x`。 -->

- [ ] 我已阅读 [CONTRIBUTING.md](../../CONTRIBUTING.md) 与
      [CLA.md](../../CLA.md)。
- [ ] 我同意 [CLA.md](../../CLA.md) 的条款；本贡献可依据
      [Repository-Policy.md](../../Repository-Policy.md) 中的分阶段
      许可证栈规则被再许可。
- [ ] 我的提交携带 `Signed-off-by:` 行（DCO 1.1）——使用
      `git commit -s`，或手动追加 `Signed-off-by: 姓名 <邮箱>`。
- [ ] 对于用户可见或行为变更，我已在 `CHANGELOG.md` 的
      `## [Unreleased]` 节下按子节（Added / Changed / Deprecated /
      Removed / Fixed / Security）添加条目。
- [ ] 对于代码改动，我已运行 `gitnexus_impact`（或等效分析）并在下方
      记录影响范围。
- [ ] 对于代码改动，我已在本地运行 `uv run -m ruff check .`、
      `uv run -m ruff format --check .`、`uv run -m pyright .` 和
      `uv run -m ty check .`。
- [ ] 对于文档站改动，我已在本地运行 `pnpm --filter docs lint` 与
      `pnpm --filter docs test`。
- [ ] 我已添加或更新覆盖本改动的测试。
- [ ] 我已按需更新相关文档、i18n 文案、运行时配置与 handle 默认值。

### Release PR 自检（仅适用于 `releases/**` 分支）

<!-- 若本 PR 指向 `releases/<version>` 分支，请确认供应链证明流程；
否则删除本小节。 -->

- [ ] 版本号由 `dev-minor*` / `dev-major*` / `dev-alpha*` /
      `dev-beta*` / `dev-rc*` / `dev-stable*` 分支名驱动，
      `ci:version:precheck` 通过（PEP 440、大于所有现有 tag、无重复
      tag、源文件一致）。
- [ ] `ci:version:write-config` 之后 `ci:version:postcheck` 通过
      （调用 `release:verify-version`、三源文件同步、dev release
      语义有效）。
- [ ] `pyproject.toml`、`package.json` 与
      `src/plugins/nonebot_plugin_lingchu_bot/core/config.py` 版本
      完全一致，且由 `task ci:version:write-config` 写入。
- [ ] `dist/*` 中的构建产物携带来自
      `actions/attest-build-provenance@v4.1.0` 的 SLSA Build L3 证明；
      下游消费者可用
      `gh attestation verify <产物> --repository xinvxueyuan/lingchu-bot`
      验证。
- [ ] `CHANGELOG.md` 有 `## [<版本>] - <日期>` 节，条目从
      `## [Unreleased]` 迁入，并在底部补充 compare 链接。

## 影响分析（GitNexus / codegraph）

<!-- 简要描述涉及的符号、直接调用方与风险等级。若仅为文档改动，请
明确说明。 -->

## 如何验证

<!-- 审查者可执行的复现命令。 -->

```bash
# 例如
uv run -m pytest tests/path/to/test_xxx.py
pnpm --filter docs test
```

## 截图 / 日志

<!-- 仅在必要时附上。若截图包含个人信息或第三方内容，请遵守
Repository-Policy.md 的脱敏规则。 -->

## 其他说明

<!-- 审查者需要了解的事项：取舍、后续工作、已知限制。 -->
