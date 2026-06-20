---
name: engineering-workflow
description: 统筹 Lingchu Bot 的代码理解、GitNexus 影响分析、调试交付、设计原型、前端质量和议题规划。Use when 用户要理解架构、追踪影响、修 bug、做 TDD/代码审查、设计 API/UI/架构方案、打磨 docs 站点、拆 PRD/issue/QA/refactor 计划，或需要 GitNexus/knowledge graph/onboarding 相关工作。
---

# 工程工作流

这是项目内工程类技能的统一入口。先判断用户真正需要的是理解、影响分析、调试交付、设计探索、前端质量，还是计划拆解；只读取对应 reference。

## 路由

- 代码理解、架构解释、onboarding、知识图谱：读 `references/gitnexus/gitnexus-exploring/guide.md`，或按下面 GitNexus 路由选择更细 guide。
- 改动前影响分析、blast radius、风险评估：读 `references/gitnexus/gitnexus-impact-analysis/guide.md`。
- GitNexus CLI、索引、status、clean、wiki：读 `references/gitnexus/gitnexus-cli/guide.md`。
- GitNexus 工具、schema、资源说明：读 `references/gitnexus/gitnexus-guide/guide.md`。
- GitNexus 辅助调试：读 `references/gitnexus/gitnexus-debugging/guide.md`。
- GitNexus 辅助重构：读 `references/gitnexus/gitnexus-refactoring/guide.md`。
- PR 或 diff review：优先读 `references/gitnexus/gitnexus-pr-review/guide.md`；需要一般审查循环时再读 `references/delivery-loop/delivery-loop-skill.md`。
- Bug、失败追踪、性能或 flaky、TDD、实现后验证：读 `references/delivery-loop/delivery-loop-skill.md`。
- 产品/API/UI/架构设计、方案对比、grill 提问、一次性原型：读 `references/design-prototyping/design-prototyping-skill.md`。
- React/docs 站点诊断、可访问性、响应式、视觉打磨、浏览器验证：读 `references/frontend-quality/frontend-quality-skill.md`。
- PRD、issue 拆分、triage、QA 会话、重构计划：读 `references/issue-planning/issue-planning-skill.md`。

## 项目规则

1. 先看当前工作区状态、用户最新要求和相关 AGENTS 规则，再相信旧图谱或旧计划。
2. 修改函数、类或方法前，按项目 GitNexus 规则做影响分析；如果返回 HIGH/CRITICAL 风险，先提醒用户。
3. 用户要 review 时保持审查姿态：发现项优先，附文件和行号。
4. 用户要实现时不要停在建议；完成编辑、针对性验证，并说明结果。
5. reference 内若提到脚本或子 reference，路径按该 reference 所在目录解析。
