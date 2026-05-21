---
icon: lucide/settings
title: Configuration
---

## Configuration

Lingchu Bot uses NoneBot plugin configuration and Pydantic models to manage core settings. The current core settings are concentrated in the `Config` model.

## Core settings

| Setting | Default | Description |
| --- | --- | --- |
| `core_version` | `0.0.0-dev0` | Core plugin version marker |
| `superuser_key` | `123456789abcdef` | Superuser authentication key |
| `data_dir` | localstore data directory | Data file directory |
| `config_dir` | localstore config directory | Configuration file directory |
| `cache_dir` | localstore cache directory | Cache file directory |

## Internationalization settings

Runtime translation reads these NoneBot configuration keys in order:

1. `lingchu_locale`
2. `lc_locale`
3. `locale`

The recommended project-specific key in `.env` is:

```env
LINGCHU_LOCALE=zh_CN
```

Available catalogs currently include `zh_CN` and `en_US`. Locale names are normalized before use, so `en-US` and `en_US.UTF-8` both become `en_US`. When the setting is missing, empty, or NoneBot has not been initialized, the default locale is `zh_CN`.

## Container environment flag

`in_containers` comes from global NoneBot configuration. It must be a Boolean value.

```env
IN_CONTAINERS=true
```

Do not write:

```env
IN_CONTAINERS=True
```

NoneBot configuration files only accept standard JSON lowercase `true` / `false`. If a string-like Boolean is passed in, the project raises a clear configuration error.

## Local runtime paths

`bot.py` sets:

```python
LOCALSTORE_USE_CWD = True
```

This means localstore-related directories prefer the current working directory, which is convenient for local development and debugging.
