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
npx markdownlint-cli2 "docs/**/*.md" "README.md" "CHANGELOG.md" "CONTRIBUTING.md" "CODE_OF_CONDUCT.md" ".github/**/*.md"
```

## 文档构建

文档部署工作流使用：

```bash
uvx zensical build --clean
uvx zensical build --config-file zensical.en.toml --clean
```

本地修改 `zensical.toml` 或 `docs/` 后，建议运行同一条命令确认站点能构建。

## 国际化检查

修改可翻译字符串后运行：

```bash
task i18n:extract
task i18n:update
task i18n:compile
```

如果只修改文档中的 i18n 说明，不需要重新生成 gettext catalog。

## CI 失败处理

打开失败 job 日志，定位命令、规则和行号。修复时只改导致失败的最小范围，并重新运行对应本地命令。
