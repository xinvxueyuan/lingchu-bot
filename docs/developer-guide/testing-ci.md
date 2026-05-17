---
icon: lucide/check-circle
title: 测试与 CI
---

## 测试与 CI

CI 由 GitHub Actions 运行，主要包含静态检查、类型检查、测试和文档部署。

## 静态检查

```bash
uv run -m ruff check . --output-format=github
uv run -m ruff format --check .
```

## 类型检查

```bash
uv run -m pyright .
uv run -m ty check --output-format github
```

## 测试

```bash
uv run -m pytest
```

如果只改了某个模块，可以先跑相关测试文件，再按需要扩大范围。

## Markdown 检查

```bash
npx markdownlint-cli2 "docs/**/*.md"
```

## 文档构建

文档部署工作流使用：

```bash
uvx zensical build --clean
```

本地修改 `zensical.toml` 或 `docs/` 后，建议运行同一条命令确认站点能构建。

## CI 失败处理

打开失败 job 日志，定位命令、规则和行号。修复时只改导致失败的最小范围，并重新运行对应本地命令。
