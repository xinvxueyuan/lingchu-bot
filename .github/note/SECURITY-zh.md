# 安全策略

> [English](../../SECURITY.md) | 中文

## 支持的版本

本项目目前处于活跃开发阶段，不支持任何历史版本的安全更新。

| 版本 | 支持情况 |
|---------|-----------|
| `main` 分支 | 活跃开发 |
| `dev` 分支 | 活跃开发 |
| 已发布的标签版本 | 仅最新版本 |

## 报告漏洞

### 如何报告

请通过 **GitHub 私有漏洞报告** 功能报告安全漏洞：

1. 访问 [github.com/xinvxueyuan/lingchu-bot/security/advisories/new](https://github.com/xinvxueyuan/lingchu-bot/security/advisories/new)。
2. 点击 **"Report a vulnerability"**。
3. 在公告表单中填写以下所述的详细信息。

如果无法使用 GitHub 私有报告，也可以提交普通的 [GitHub Issue](https://github.com/xinvxueyuan/lingchu-bot/issues) 并添加 `security` 标签。但**强烈推荐使用私有报告**，以避免在修复方案发布前公开暴露漏洞细节。

<Callout type="warn" title="不要为严重漏洞提交公开 issue">

如果漏洞可能导致远程代码执行、数据泄露或身份验证绕过，请仅使用私有漏洞报告。请勿在公开 issue、Pull Request 或讨论中披露这些细节。

</Callout>

### 报告格式

请在报告中包含以下信息：

```markdown
**Vulnerability title**: [Brief one-line summary]

**Severity**: [Critical / High / Medium / Low]

**Affected component**: [e.g., OneBot V11 adapter, permission system, message store]

**Description**:
[Detailed description of the vulnerability]

**Reproduction steps**:
1. [Step 1]
2. [Step 2]
3. [Step N]

**Expected behavior**: [What should happen]
**Actual behavior**: [What actually happens]

**Impact**: [Who is affected, what an attacker could achieve]

**Environment**:
- OS: [e.g., Windows 11, Ubuntu 24.04]
- Python version: [e.g., 3.13.x]
- Adapter: [e.g., OneBot V11, NapCat]
- Lingchu Bot version/commit: [e.g., v0.0.1 or commit hash]

**Suggested fix** (optional): [If you have a proposed fix]
```

### 响应时间线

| 阶段 | 目标时间 |
|-------|-----------------|
| 报告确认 | 48 小时内 |
| 初步评估（严重性分级） | 5 个工作日内 |
| 向报告者同步状态 | 每周一次，直至解决 |
| 发布修复或缓解措施 | 高/严重级别 30 天内；中/低级别 90 天内 |
| 公开披露（修复后） | 发布后 14 天内 |

上述时间为目标值，不作保证。维护者会向报告者同步任何延迟情况。

### 披露策略

- **协调披露**：仅在修复方案发布且用户有合理时间升级后，漏洞才会被公开披露。
- **Embargo 期**：在修复方案发布前，请报告者对漏洞细节保密。维护者将与报告者协调披露日期。
- **致谢**：遵循协调披露的报告者将在安全公告和发布说明中获得致谢，除非其希望匿名。
- **公开公告**：修复方案发布后，将发布 GitHub Security Advisory，并（在适用时）分配 CVE 编号，附带漏洞和修复方案的摘要。

## 范围

以下情况视为安全报告的范围内：

- 身份验证或授权绕过（例如，超级用户提权、权限绕过）
- 通过机器人命令或 API 端点实现远程代码执行
- 敏感数据泄露（例如，配置密钥、用户数据泄露）
- 通过构造消息或 API 滥用造成拒绝服务
- 注入漏洞（SQL 注入、命令注入、路径穿越）

以下情况**不在范围内**：

- 第三方依赖中的漏洞（请向上游项目报告）
- Self-XSS 或需要受害者在自己账户上运行恶意命令的问题
- 无可用概念验证的理论性问题
- 已弃用/已移除的适配器中的问题（Milky、QQ、OneBot V12）

## 加固建议

在生产环境部署 Lingchu Bot 时：

- 将 `LINGCHU_SUPERUSERS` 设置为最小化的可信账户集合。
- 在生产环境中使用 `ALEMBIC_STARTUP_CHECK=true` 以强制执行 schema 迁移检查。
- 在生产环境中禁用 `FASTAPI_DOCS_URL` 和 `FASTAPI_REDOC_URL`，避免暴露 API 文档。
- 在容器中运行机器人，并赋予最小文件系统权限。
- 定期更新 Python 和 Node.js 依赖（`uv sync --upgrade` 和 `pnpm update`）。

## 供应链来源证明

本仓库发布的构建产物附带 **SLSA Build L3** 来源证明。`👷-ci-builds.yml` 的 `versioned-build` job 使用 [`actions/attest-build-provenance@v4.1.0`](https://github.com/actions/attest-build-provenance)（SHA 锁定）为 `dist/*` 产物生成来源证明。该证明将每个产物绑定到生成它的确切工作流运行、源代码提交和构建环境。

消费者和运维人员在信任已下载的产物（wheel、sdist 或容器镜像）前，可使用 GitHub CLI 验证来源证明：

```bash
# 验证已下载的 wheel 或 sdist
gh attestation verify ./nonebot_plugin_lingchu_bot-0.0.1-py3-none-any.whl \
  --repository xinvxueyuan/lingchu-bot

# 验证从 GHCR 拉取的容器镜像
gh attestation verify oci://ghcr.io/xinvxueyuan/lingchu-bot:0.0.1 \
  --repository xinvxueyuan/lingchu-bot
```

验证成功会打印来源信息（`👷-ci-builds.yml` 工作流在 `releases/**` ref 上的运行）并确认产物由所声明的提交构建。若验证失败，请勿安装或运行该产物——通过上方私密漏洞报告渠道报告。

补充供应链说明：

- 所有第三方 GitHub Actions 均按 40 字符提交 SHA 锁定并附 `# vX.Y.Z` 注释；不使用 tag 锁定引用。
- PyPI 发布使用 OIDC Trusted Publishing（仓库密钥中不存储长期 API 令牌）。
- GHCR 推送使用临时 `GITHUB_TOKEN`，权限为 `packages: write`。
