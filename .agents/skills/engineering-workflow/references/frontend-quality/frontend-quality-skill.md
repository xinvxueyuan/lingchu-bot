---
name: frontend-quality
description: 打磨和诊断 Lingchu Bot docs 站点的 React/frontend 质量。Use when 任务涉及 apps/docs 的响应式、视觉一致性、可访问性、lint、测试、bundle、架构、React Doctor 或浏览器验证。
---

# 前端质量

用于 `apps/docs` 的视觉、可用性和工程质量检查。先确认用户是要诊断问题、打磨界面，还是验证改动。

## 路由

- React 健康检查、hook/组件结构、React Doctor：读 `references/react-doctor.md`。
- 视觉打磨、响应式、可访问性、浏览器验收：读 `references/frontend-polish.md`。

## 项目规则

1. 遵循现有 Fumadocs/Next.js/Tailwind 结构，不引入无关设计系统。
2. `apps/docs` 的 server components、route handlers 和 lib functions 默认保持 async。
3. UI 改动需要真实浏览器或截图验证时，启动 dev server 后检查桌面和移动视口。
4. 最小检查通常是 `pnpm --filter docs lint`、`pnpm --filter docs test` 和 docs TypeScript 检查；按风险扩大。
