---
alwaysApply: true
scene: git_message
---

使用 gitmoji + Conventional Commits 规范编写提交信息。

## 格式

```
<gitmoji> <type>[!(<scope>)]?: <subject>

<body>?

<footer>?
```

- 首行（subject）由 `.husky/commit-msg` 钩子强制校验，必须严格匹配正则
- body 和 footer 可选，不做格式强制
- **破坏性变更**：在 `type` 后或 `)` 后紧跟 `!`，不限位置；也可在 footer 中写 `BREAKING CHANGE`

## 实用规范

- **subject 以祈使语气书写**："新增"而非"新增了"；"修复"而非"修复了"
- **subject 控制在 50 字符以内**（中文约 25 字），首字母无需大写，末尾不加句号
- **body 每行不超过 72 字符**，用空行与 subject 隔开，描述改动原因而非重复"做了什么"
- **scope 用小写简洁命名**：`auth`、`db`、`api`、`i18n` 等，无空格
- **中英文混排**：subject 可用中文或英文，保持项目一致即可；技术术语保留英文（如 OAuth2、RESTful）

## Type 与 Gitmoji 对应

| Type | 含义 | 推荐 Gitmoji |
|------|------|-------------|
| feat | 引入新功能 | ✨ |
| fix | 修复缺陷 | 🐛 |
| docs | 新增或更新文档 | 📝 |
| style | 代码格式调整(不影响逻辑) | 🎨 |
| refactor | 重构(非新功能非修缺陷) | ♻️ |
| perf | 提升性能 | ⚡️ |
| test | 新增、更新或通过测试 | ✅ |
| build | 构建系统或外部依赖 | 👷 |
| ci | CI 配置变更 | 💚 |
| chore | 杂项(配置、工具等) | 🔧 |
| revert | 回退变更 | ⏪️ |

> 优先使用上表推荐搭配，也可根据语义选用其他 gitmoji（如 💥 破坏性变更、🚑️ 紧急修复）。完整列表见 `task gitmoji`。

## 破坏性变更（`!`）

在常规格式中插入 `!` 标记破坏性变更，无需额外 commit type：

```
<gitmoji> <type>!(<scope>)?: <subject>
<gitmoji> <type>(<scope>)!:<subject>
```

- 示例：`✨ feat!(api): 移除旧版鉴权方式`
- 示例：`🐛 fix(db)!: 重写迁移脚本`
- 也可在 footer 追加 `BREAKING CHANGE: <描述>` 详述影响

## Scope（可选）

用括号标注影响范围：

- `✨ feat(auth): 新增 OAuth2 登录`
- `🐛 fix(db): 修复连接池泄漏`
- `♻️ refactor(i18n): 统一翻译键命名`

## Body 与 Footer

- body：用空行与 subject 隔开，回答"为什么"
- footer：使用 token 关联 issue / PR / 协作信息

常用 footer token：

| Token | 用途 |
|-------|------|
| `BREAKING CHANGE:` | 破坏性变更说明 |
| `Closes #issue` | 关闭 issue |
| `Fixes #issue` | 修复 issue |
| `Refs #issue` | 引用 issue（不关闭） |
| `Co-authored-by:` | 共同作者署名 |
| `Reviewed-by:` | 审阅者署名 |
| `Signed-off-by:` | 签署 DCO |

```
💥 feat!(api): 重写用户接口

旧接口无法支持批量操作，重新设计 RESTful 风格。

BREAKING CHANGE: /api/user/:id 参数从 path 移至 query string
Closes #42
Reviewed-by: @someone
```

## 常见场景速查

| 场景 | 推荐写法 |
|------|---------|
| 新增功能 | `✨ feat: 新增群管理功能` |
| 修复 bug | `🐛 fix(auth): 修复令牌过期` |
| 重构代码 | `♻️ refactor(handler): 拆分路由` |
| 性能优化 | `⚡️ perf(db): 为查询添加索引` |
| 补充测试 | `✅ test(mute): 补充边界用例` |
| 更新文档 | `📝 docs: 补充部署指南` |
| 升级依赖 | `🔧 chore(deps): 升级 ruff` |
| 降级依赖 | `⬇️ chore(deps): 降级 pydantic` |
| 移除代码 | `🔥 chore: 删除废弃模块` |
| 移动文件 | `🚚 refactor: 迁移 handle 到 group/` |
| 修复拼写 | `✏️ docs: 修正文档错别字` |
| CI 修复 | `💚 ci: 修复 pytest 超时` |
| 紧急修复 | `🚑️ fix: 紧急修复生产崩溃` |
| 安全修复 | `🔒️ fix(security): 修复 XSS` |
| 破坏性变更 | `💥 feat!(api): 移除 /v1 前缀` |
| 版本发布 | `🔖 chore(release): v1.2.0` |
| 回退变更 | `⏪️ revert: 回退 #42 的提交` |
| 合并分支 | `🔀 chore: 合并 feat/auth 到 main` |

## 正则原文

`.husky/commit-msg` 使用的校验正则：

```
^(<gitmoji>) (<type>)(!)?(\(<scope>\))?(!)?: <subject>
```

- `<gitmoji>` — 来自 gitmoji.dev 的 73 个官方 emoji（含 variation selector）
- `<type>` — `feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert`
- `(!)?` — 可选的破坏性变更标记，出现在 type 后
- `(<scope>)?` — 可选的作用域
- `(!)?` — 可选的破坏性变更标记，出现在 scope 后
- `: ` — 冒号 + 空格（必须）
- `<subject>` — 非空描述文本

## 反例

以下格式会被 `.husky/commit-msg` **拒绝**：

| 错误写法 | 问题 |
|----------|------|
| `feat: 新增功能` | 缺少 gitmoji |
| `😍 feat: 新增功能` | 😍 不在 gitmoji.dev 官方列表中 |
| `✨ feat新增功能` | type 与 subject 之间缺少 `: ` |
| `✨ foo: 做某事` | type 不在允许列表中 |
| `✨ feat:` | subject 为空 |
| `✨feat: 新增` | gitmoji 后缺少空格 |
| `✨ Feat: 新增` | type 大小写错误 |
| `✨ feat: 新增了功能。` | 末尾有句号（不推荐） |

## AI 代理提交指引

`prepare-commit-msg` 钩子调用交互式 `gitmoji --hook`，AI 无法参与交互。提交时可：

- 手动运行 `git commit` 在终端中通过交互界面选择 gitmoji
- 或在使用 `RunCommand` 时设置 `$env:HUSKY='0'` 跳过交互钩子，但必须自行确保首行格式正确
- CI 自动化提交场景（如 `ci:version:commit-tag`）已内置 `$env:HUSKY='0'`

## 完整示例

```
✨ feat: 新增群管理功能
🐛 fix(auth): 修复令牌过期不刷新的问题
📝 docs: 补充部署文档
♻️ refactor(handler): 拆分命令路由
⚡️ perf(db): 为查询添加索引
✅ test(mute): 补充禁言模块测试
💥 feat!(api): 移除 /v1 前缀
🚑️ fix: 紧急修复生产环境崩溃
🔒️ fix(security): 修复 XSS 注入漏洞
🔧 chore(deps): 升级 ruff 至 0.12
🔖 chore(release): v1.2.0
⏪️ revert: 回退 "feat: 新增群管理"
```
