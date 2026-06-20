---
name: prek
description: 配置、运行或排查 prek/Git hooks。Use when 用户要设置或运行 prek、Husky、pre-commit、commit-msg、lint/format/type/test hooks，或排查混合 Windows/Bash hook 失败。
---

# prek 与仓库 Hooks

Lingchu Bot 使用 hook 做条件校验。先复现实际 hook 或目标命令，再决定是否扩大到全量检查。

## 本仓库优先规则

1. 看 `AGENTS.md` 的 Git Hooks 和 Quick Reference。
2. Windows 自动化显式调用 PowerShell 时用 `pwsh.exe -NoProfile`。
3. 优先低侵入命令：`uv run prek run --config prek.toml --files <changed files>`。
4. `.husky/pre-commit` 更重；除非用户要求或准备提交前验证，否则不要随手跑全量。
5. 混合 Windows/Bash 失败时，在实际 shell 里复现；`.cmd` shim 可能需要 `cmd.exe /c`。

## 常用命令

- `prek validate-config`
- `prek list`
- `prek run --files <paths>`
- `prek run --all-files`
- `prek run -vvv`

如果问题涉及 prek 当前语法或版本行为，按 `tool-workflows` 的 Context7/文档查询规则获取最新文档。
