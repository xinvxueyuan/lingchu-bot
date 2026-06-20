---
name: tool-workflows
description: 统筹 Lingchu Bot 的当前文档查询、仓库 hooks、prek/Husky、Context7 和项目 skill 管理。Use when 用户询问库/框架/SDK/API/CLI/云服务当前文档，配置或运行 prek/Husky/pre-commit hooks，或整理、安装、编写、合并 Codex skills。
---

# 工具工作流

这是项目内工具类技能的统一入口。先选择最贴近的工具 reference；只有任务确实串联多个工具时才组合读取。

## 路由

- 当前库、框架、SDK、API、CLI、云服务文档：读 `references/context7-mcp/context7-mcp-skill.md`。开发文档优先 Context7。
- Git hooks、prek、Husky、pre-commit 校验、hook 失败排查：读 `references/prek/prek-skill.md`，并结合仓库 `AGENTS.md` 的 Git Hooks 规则。
- skill 查找、安装、编写、合并、归档、汉化：先读系统 `skill-creator`；项目内参考本文件和 `available-skills` 的路由结构。

## 快速约定

- 文档查询：用官方库名解析 library id，用用户完整问题查文档，不用记忆替代当前 API 细节。
- Hooks：先看仓库已有工具链和脚本；优先低侵入目标文件校验，再按风险扩大范围。
- Skills：合并前保留旧内容为 reference 或可追踪的 git 变更；复制来的旧 `SKILL.md` 必须改名，避免再次成为活跃入口。
- Windows 自动化：显式调用 PowerShell 时用 `pwsh.exe -NoProfile`。
