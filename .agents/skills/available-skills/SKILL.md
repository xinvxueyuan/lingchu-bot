---
name: available-skills
description: Lingchu Bot 项目本地 skill 与外部插件的紧凑路由索引。Use when agent 需要为文档查询、代码理解、GitNexus、调试交付、前端质量、hook 校验、制品处理、部署或 skill 编写选择应该加载的技能。
---

# 可用技能

把这里当作路由表使用。不要预先加载所有技能；只有用户请求命中触发条件后，再读取对应 `SKILL.md` 或 reference。

## 强制文档规则

当用户询问库、框架、SDK、API、CLI 工具或云服务时，使用 Context7 MCP 或 `find-docs` 获取当前文档。除非用户给出精确 `/org/project` ID，否则先 `resolve-library-id`，再用用户完整问题查询文档。开发文档优先 Context7，而不是普通 web 搜索。

## 项目本地入口

- `engineering-workflow`：工程类统一入口。覆盖 GitNexus 代码理解/影响分析/调试/重构/PR review、delivery loop、handle 变更跨面检查、设计原型、前端质量和 issue/PRD/QA 拆解。
- `tool-workflows`：工具类统一入口。覆盖 Context7 文档查询、prek/Husky/hooks、skill 管理与合并汉化。
- `interactive-runtime-debugging`：交互式运行时调试入口。覆盖 Lingchu/NapCat/QQ 实机复现、handle 命令现场故障、实时日志、数据库证据、跨边界追踪和复测。
- `available-skills`：只在需要选择技能或更新项目 skill 索引时读取。

## 外部代码与仓库技能

- `github:*`：检查 GitHub 仓库、PR、issue、review comment、CI 失败和发布流程。
- `openai-docs`：回答 OpenAI 产品和 API 问题，优先官方文档。
- `context7` / `find-docs`：获取当前开发者文档；项目本地路由在 `tool-workflows`。

## 前端与浏览器技能

- `browser` / Playwright / Chrome：本地网页验证、截图、点击、表单和浏览器流程调试。
- `vercel:*`：Next.js、React best practices、shadcn/ui、部署、Vercel API/CLI、存储、认证、函数、workflow、observability 和 AI SDK。

## 云平台技能

- `cloudflare:*`：Workers、Wrangler、Durable Objects、Agents SDK、MCP servers、sandbox SDK 和 Cloudflare 平台工作。
- `vercel:*`：Vercel 部署、运行时、API、队列、存储和平台集成。

## 制品与媒体技能

- `documents`：创建、编辑、批注、校验 Word 文档。
- `presentations`：创建、编辑、渲染、校验 slide deck。
- `spreadsheets`：创建、编辑、分析、可视化、导出 spreadsheet。
- `pdf`：阅读、创建或审查 PDF；布局重要时做视觉检查。
- `imagegen`：生成或编辑位图图片。

## Skill 与插件编写

- `skill-creator`：创建或更新技能，保持 `SKILL.md` 简洁，并按需使用 `references/`、`scripts/`、`assets/`。
- `skill-installer`：安装 Codex skills。
- `plugin-creator`：脚手架化 Codex plugins。
