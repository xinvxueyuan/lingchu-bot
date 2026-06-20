---
alwaysApply: true
scene: git_message
---

提交信息 MUST 遵循 gitmoji + Conventional Commits 规范，由 `.husky/commit-msg` 钩子强制校验。

## 格式与正则

```
<gitmoji> <type>[!](<scope>)?[!]: <subject>

<body>?

<footer>?
```

`.husky/commit-msg` 校验正则：

```
^(<gitmoji>) (<type>)(!)?(\(<scope>\))?(!)?: <subject>
```

- `<gitmoji>` — MUST 为 gitmoji.dev 官方 73 个 emoji（含 variation selector）
- `<type>` — MUST 为 `feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert` 之一
- `<scope>` — 可选，MUST 为小写无空格简洁命名（如 `auth`、`db`、`api`、`i18n`）
- `<subject>` — MUST 非空，以祈使语气书写，控制在 50 字符以内（中文约 25 字），首字母不大写，末尾不加句号
- 破坏性变更 MUST 在 `type` 后或 `)` 后紧跟 `!`，或在 footer 中写 `BREAKING CHANGE:`

## Type 与 Gitmoji 强制对应

| Type | Gitmoji | Type | Gitmoji |
|------|---------|------|---------|
| feat | ✨ | refactor | ♻️ |
| fix | 🐛 | perf | ⚡️ |
| docs | 📝 | test | ✅ |
| style | 🎨 | build | 👷 |
| ci | 💚 | chore | 🔧 |
| revert | ⏪️ | | |

每个 type MUST 使用上表对应 gitmoji，禁止混用。

## Body 与 Footer

- body MUST 用空行与 subject 隔开，每行不超过 72 字符，描述改动原因而非重复"做了什么"
- footer MUST 使用以下 token：`BREAKING CHANGE:`、`Closes #issue`、`Fixes #issue`、`Refs #issue`、`Co-authored-by:`、`Reviewed-by:`、`Signed-off-by:`

## 撰写原则

- `apps/docs` 为文档目录，`src` 为代码目录
- 同时包含 docs 与 code 变更时，MUST 抑制 docs 权重，仅保留针对 code 变更的标题，docs 变更作为 body 一项展示
- 仅包含 code 变更时，MUST 增强 fix/refactor/perf/test/build/ci/chore/revert 的权重
- 仅包含 docs 变更时，MUST 增强 docs 的权重
- 变更复杂时，MUST 增强 body/refactor 的权重

## 反例

以下格式 MUST NOT 出现：

- `feat: 新增功能` → 缺少 gitmoji
- `😍 feat: 新增功能` → 😍 不在 gitmoji.dev 官方列表
- `✨ feat新增功能` → type 与 subject 间缺少 `: `
- `✨ feat:` → subject 为空
- `✨ Feat: 新增` → type 大小写错误

## 核心示例

```
✨ feat(auth): 新增 OAuth2 登录
🐛 fix(db)!: 重写迁移脚本

BREAKING CHANGE: 迁移脚本不再兼容旧 schema
Closes #42
```
