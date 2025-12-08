# 数据库

用于存储机器人的运行时数据。

## 目录结构

```src/builtin_plugins/lingchu_bot/core/

database/
├── model/
├── client.py
└── README.md
```

## 目录说明

- `model/`：包含数据库模型定义的目录。
- `client.py`：数据库客户端模块，负责与数据库进行交互。
- `README.md`：数据库模块的说明文档。

## 功能说明

- `model/`：定义了数据库的模型，包括表结构和字段。
- `client.py`：提供了数据库客户端的接口，用于执行数据库操作。
