---
name: delivery-loop
description: 用纪律化反馈循环完成调试、TDD 和代码审查验证。Use when 用户报告 bug、失败、flaky 测试、性能问题，要求 TDD/red-green-refactor，实现后验证，或 review 代码、branch、PR、worktree diff。
---

# 交付循环

当任务目标是把代码从“不确定”推进到“已验证”时使用：复现、测试、修复、审查、收紧。

## 路由

- Bug、崩溃、flaky、性能慢、“为什么失败”：读 `references/debug-investigation.md`。
- 明确要求 TDD 或 test-first：读 `references/tdd.md`。
- 代码、diff、branch、PR review：读 `references/change-review.md`，并以发现项开头。

## 循环

1. 改代码前先复现或检查当前状态。
2. 可行时选择最小有用的失败检查。
3. 窄范围实现，保留用户已有工作区改动。
4. 先跑目标验证；风险扩大时再跑更广检查。
5. 总结改动、验证命令和剩余风险。

需要依赖影响、执行流或 PR 结构时，回到 `engineering-workflow` 的 GitNexus 路由。

## 项目检查

按 `AGENTS.md` Quick Reference 选择最小相关检查。提交前还要按项目规则运行 GitNexus `detect_changes`。
