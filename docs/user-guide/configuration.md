---
icon: lucide/settings
title: 配置
---

## 配置

Lingchu Bot 使用 NoneBot 插件配置和 Pydantic 模型管理核心配置。当前核心配置集中在 `Config` 模型中。

## 核心配置项

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `core_version` | `0.0.0-dev0` | 核心插件版本标识 |
| `superuser_key` | `123456789abcdef` | 超级用户认证密钥 |
| `data_dir` | localstore 数据目录 | 数据文件目录 |
| `config_dir` | localstore 配置目录 | 配置文件目录 |
| `cache_dir` | localstore 缓存目录 | 缓存文件目录 |

## 容器环境标记

`in_containers` 来自 NoneBot 全局配置。它必须是布尔值。

```env
IN_CONTAINERS=true
```

不要写成：

```env
IN_CONTAINERS=True
```

NoneBot 配置文件只接受 JSON 标准的小写 `true` / `false`。如果传入字符串形式的布尔值，项目会抛出明确的配置错误。

## 本地运行路径

`bot.py` 默认设置：

```python
LOCALSTORE_USE_CWD = True
```

这意味着 localstore 相关目录会优先落在当前工作目录，方便本地开发和调试。
