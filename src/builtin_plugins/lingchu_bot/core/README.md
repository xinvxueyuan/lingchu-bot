# 核心部分

本目录包含灵初机器人的核心功能和基础设施，确保机器人能够高效、稳定地运行。核心部分负责处理消息的接收与发送、插件管理、配置管理等关键任务。

## 目录结构

```src/builtin_plugins/lingchu_bot/

core/
├── index.py
├── module/
├── web/
├── database/
├── middleware/
└── README.md

```

## 目录说明

- `index.py`：核心部分的入口文件，负责初始化机器人并启动核心功能。
- `module/`：核心模块，包含机器人的核心功能和基础设施。
- `web/`：包含Web相关的代码，用于处理HTTP请求和响应。
- `database/`：数据库模块，负责与数据库进行交互。
- `middleware/`：中间件模块，用于处理各类事件的预处理和后处理。
- `README.md`：核心部分的说明文档。
