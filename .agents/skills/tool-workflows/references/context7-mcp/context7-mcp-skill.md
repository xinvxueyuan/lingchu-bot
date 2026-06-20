---
name: context7-mcp
description: 查询库、框架、SDK、API、CLI 和云服务的当前文档。Use when 用户问 setup/config/API reference、需要依赖当前版本的代码示例，或提到 React、Next.js、NoneBot2、Alconna、Prisma、Tailwind 等具体库。
---

# Context7 文档查询

当问题依赖库或平台的当前 API 时，用 Context7 获取文档，不靠记忆猜。

## 步骤

1. 用官方库名和用户完整问题调用 `resolve-library-id`。
2. 选择最匹配的结果：名称精确、描述相关、snippet 多、来源可信、benchmark 高；用户提版本时优先版本化 ID。
3. 用选中的 library id 和用户完整问题调用 `query-docs`。
4. 基于取回文档回答；涉及版本时说明版本或文档来源。

## 约定

- 不把查询词缩成单个关键词；完整问题能提升相关性。
- 多个结果相近时优先官方/主包，少选社区 fork。
- OpenAI 产品/API 问题优先 `openai-docs`。
