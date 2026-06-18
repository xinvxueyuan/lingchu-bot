# Checklist

## 模型统一

- [x] `database/models.py` 中不再存在未使用的全局 `MessageRecord`（无 `api_name`/`api_result_summary` 字段的旧版本）
- [x] `database/models.py` 中的 `MessageRecord` 使用 `nonebot_plugin_orm.Model` 基类，包含 `raw_message` 和 `raw_event` 字段
- [x] `database/models.py` 中的 `AuditRecord` 使用 `nonebot_plugin_orm.Model` 基类，表名为 `lingchu_audit_records`
- [x] `database/models.py` 中不再存在 `PlatformMessageRecord`
- [x] `database/models.py` 中的 `BlocklistEntry` 保持不变
- [x] `database/message_storage.py` 文件已删除
- [x] 项目中不存在对 `message_storage` 模块的任何导入引用

## 仓储层重写

- [x] `repositories/message_store.py` 不再导入 `message_storage` 模块
- [x] `repositories/message_store.py` 中 `record_event_received()` 使用 `orm_crud.upsert()`
- [x] `repositories/message_store.py` 中 `record_matcher_result()` 使用 `orm_crud.get_one()` + `orm_crud.update()`
- [x] `repositories/message_store.py` 中 `record_api_call()` 使用 `orm_crud.create()`
- [x] `repositories/message_store.py` 中 `list_recent_messages()` 使用 `orm_crud.list_items()` 直接查询 `MessageRecord`
- [x] `repositories/message_store.py` 中 `cleanup_expired_messages()` 使用 `orm_crud.delete()` 删除过期记录
- [x] `repositories/message_store.py` 中不再存在 `_upsert_platform_projection()` 函数
- [x] `repositories/message_store.py` 中不再存在对 `StorageTarget`、`session_for()`、`storage_target()` 等的引用

## JSON5 存储包化

- [x] `database/json5_store/` 目录存在，包含 `__init__.py`、`exceptions.py`、`_sync.py`、`_async_db.py`
- [x] `database/json5_store.py` 单文件已删除
- [x] `database/json5_store/__init__.py` 重新导出所有公共 API（`RobustAsyncJSON5DB`、`load_json5_dict_sync`、`ensure_json5_dict_file_sync` 及所有异常类）
- [x] `core/runtime_config.py` 中的 `from ..database.json5_store import ...` 导入路径仍然有效
- [x] `__init__.py` 中的 `from .database import json5_store as json5_store` 仍然有效

## 迁移系统

- [x] `.env.example` 中包含 `ALEMBIC_STARTUP_CHECK` 配置项
- [x] 迁移脚本目录存在且包含初始迁移脚本
- [x] 迁移脚本包含 `lingchu_message_records`、`lingchu_blocklist_entries`、`lingchu_audit_records` 三张表的创建操作
- [x] `nb orm upgrade` 命令能成功执行（或 `ALEMBIC_STARTUP_CHECK=false` 时启动自动建表）

## 测试

- [x] `tests/repositories/test_message_store.py` 不再导入 `message_storage` 模块
- [x] `tests/repositories/test_message_store.py` 使用 mock `orm_crud` 函数测试仓储逻辑
- [x] `tests/services/test_messagestore.py` 中 mock 路径已更新
- [x] `tests/database/test_json5_store.py` 导入路径从 `database.json5_store` 包导入仍然有效
- [x] `tests/database/test_orm_crud.py` 无需修改（API 未变）
- [x] `tests/database/test_blocklist.py` 无需修改（API 未变）

## 检查通过

- [x] `task check` 通过（ruff + pyright + ty）
- [x] `task test` 全部通过
- [x] 无残留的 `message_storage` 导入引用（通过 Grep 验证）
- [x] 无残留的 `PlatformMessageRecord` 引用（通过 Grep 验证）
- [x] 无残留的 `session_for` 或 `storage_target` 引用（通过 Grep 验证）

## 文档更新

- [x] `AGENTS.md` 中文件树和架构图已更新（移除 `message_storage.py`，`json5_store.py` 改为 `json5_store/` 包，新增 `migrations/` 目录）
- [x] `apps/docs/content/docs/developer-guide/introduction.mdx` 已更新（移除 `message_storage.py`，`json5_store.py` 改为 `json5_store/` 包）
- [x] `apps/docs/content/docs/developer-guide/introduction.zh.mdx` 已更新（移除 `message_storage.py`，`json5_store.py` 改为 `json5_store/` 包）
