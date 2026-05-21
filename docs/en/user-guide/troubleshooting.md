---
icon: lucide/wrench
title: Troubleshooting
---

## Troubleshooting

This page collects the most common local startup and group management issues currently covered by the project.

## Dependency installation fails

First confirm that Python and uv are available:

```bash
python --version
uv --version
```

The project requires Python 3.13. Dependency installation should use:

```bash
uv sync --frozen
```

## Boolean configuration errors

If you see an `in_containers 配置错误` error, check `.env` or the NoneBot configuration file.

Correct:

```env
IN_CONTAINERS=true
```

Incorrect:

```env
IN_CONTAINERS=True
```

## Bot cannot connect to the platform

Check these first:

- Whether the Milky service has started.
- Whether NoneBot and Milky connection settings match.
- Whether the account, network, firewall, and platform permissions are usable.

## Group management command fails

Mute, unmute, and whole-group mute depend on platform permissions. When they fail, check:

- Whether the bot is in the target group.
- Whether the bot has the required management permission.
- Whether the target user can be operated on by the bot.
- Whether the Milky-side API reports a network error or rejected operation.

If feedback appears in an unexpected language, check whether `LINGCHU_LOCALE`, `lc_locale`, or `locale` is set to a supported catalog such as `zh_CN` or `en_US`. Unknown text falls back to the original message.

## CI or local checks fail

Read the failing command and line number, then fix only the related scope. Common checks include:

```bash
uv run -m ruff check . --output-format=github
uv run -m ruff format --check .
uv run -m pyright .
uv run -m ty check --output-format github
uv run -m pytest
```
