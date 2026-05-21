---
icon: lucide/smile-plus
title: Commit Style
---

## Commit Style

Project commit messages are based on Conventional Commits and may use [Gitmoji](https://gitmoji.dev/) before the type to express the change intent. Gitmoji is only a readability supplement. It does not replace a clear type, scope, and summary.

## Recommended format

```text
<emoji> <type>(<scope>): <summary>
```

The scope is optional:

```text
<emoji> <type>: <summary>
```

## Common examples

```text
✨ feat(command): 增加新的群管理命令
🐛 fix(mute): 修正禁言失败反馈
📝 docs: 更新快速开始说明
✅ test(database): 覆盖 JSON5 存储异常分支
♻️ refactor(config): 简化配置加载流程
```

## Guidance

- Use a short imperative or descriptive summary that explains what changed.
- Keep each commit focused on one primary purpose and avoid mixing unrelated code and documentation changes.
- If unsure which emoji to use, run `pnpm exec gitmoji -c` and select one interactively.
- Add background, risk, or breaking-change details in the commit body when needed.

## Local checks

Before committing, run the relevant checks. Documentation changes should at least confirm that Markdown structure, links, and fenced code blocks are sound. Code changes should use the commands in [Testing and CI](testing-ci.md).

The repository `prepare-commit-msg` hook helps check commit messages. In non-interactive environments, confirm hook behavior before rewriting unpushed commits so unrelated files are not included.
