# 中间件

用于兼容不同的OneBot实现，提供统一的接口。

## 目录结构

```src/builtin_plugins/lingchu_bot/core/

middleware/
├── index.py
├── napcat/
├── llonebot/
└── README.md

```

## 目录说明

- `index.py`：中间件的入口文件，负责加载和管理不同的OneBot实现的中间件。
- `napcat/`：Napcat实现的中间件。
- `llonebot/`：LLOneBot实现的中间件。
- `README.md`：中间件模块的说明文档。
