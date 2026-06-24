# Security Policy

> English | [中文](.github/note/SECURITY-zh.md)

## Supported Versions

This project is currently in active development. No historical versions are supported for security updates.

| Version | Supported |
|---------|-----------|
| `main` branch | Active development |
| `dev` branch | Active development |
| Tagged releases | Latest release only |

## Reporting a Vulnerability

### How to report

Please report security vulnerabilities through **GitHub's private vulnerability reporting** feature:

1. Navigate to [github.com/xinvxueyuan/lingchu-bot/security/advisories/new](https://github.com/xinvxueyuan/lingchu-bot/security/advisories/new).
2. Click **"Report a vulnerability"**.
3. Fill in the advisory form with the details below.

Alternatively, if you cannot use GitHub's private reporting, open a regular [GitHub Issue](https://github.com/xinvxueyuan/lingchu-bot/issues) and tag it with the `security` label. However, **private reporting is strongly preferred** to avoid exposing vulnerability details publicly before a fix is available.

<Callout type="warn" title="Do not open public issues for critical vulnerabilities">

If the vulnerability may allow remote code execution, data exfiltration, or authentication bypass, use private vulnerability reporting only. Do not disclose these details in public issues, pull requests, or discussions.

</Callout>

### Report format

Include the following information in your report:

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

### Response timeline

| Stage | Target timeframe |
|-------|-----------------|
| Acknowledgment of report | Within 48 hours |
| Initial assessment (severity triage) | Within 5 business days |
| Status update to reporter | Weekly until resolved |
| Fix or mitigation released | Within 30 days for High/Critical; 90 days for Medium/Low |
| Public disclosure (after fix) | Within 14 days after release |

These timeframes are targets, not guarantees. The maintainer will communicate any delays to the reporter.

### Disclosure policy

- **Coordinated disclosure**: Vulnerabilities are disclosed publicly only after a fix has been released and users have had reasonable time to update.
- **Embargo period**: Reporters are asked to keep vulnerability details private until the fix is published. The maintainer will coordinate a disclosure date with the reporter.
- **Credit**: Reporters who follow coordinated disclosure will be credited in the security advisory and release notes, unless they prefer to remain anonymous.
- **Public advisory**: After the fix is released, a GitHub Security Advisory is published with a CVE assignment (if applicable) and a summary of the vulnerability and fix.

## Scope

The following are considered in-scope for security reports:

- Authentication or authorization bypass (e.g., superuser escalation, permission bypass)
- Remote code execution through bot commands or API endpoints
- Sensitive data exposure (e.g., configuration secrets, user data leakage)
- Denial of service through crafted messages or API abuse
- Injection vulnerabilities (SQL injection, command injection, path traversal)

The following are **out of scope**:

- Vulnerabilities in third-party dependencies (report to the upstream project)
- Self-XSS or issues requiring the victim to run malicious commands on their own account
- Theoretical issues without a working proof of concept
- Issues in deprecated/removed adapters (Milky, QQ, OneBot V12)

## Hardening recommendations

When deploying Lingchu Bot in production:

- Set `LINGCHU_SUPERUSERS` to a minimal set of trusted accounts.
- Use `ALEMBIC_STARTUP_CHECK=true` in production to enforce schema migration checks.
- Disable `FASTAPI_DOCS_URL` and `FASTAPI_REDOC_URL` in production to avoid exposing API documentation.
- Run the bot in a container with minimal filesystem permissions.
- Regularly update Python and Node.js dependencies (`uv sync --upgrade` and `pnpm update`).
