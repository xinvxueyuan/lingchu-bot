# Tasks

- [x] Task 1: 统一数据库模型到 `database/models.py`
  - [x] SubTask 1.1: 移除 `models.py` 中未使用的全局 `MessageRecord`（死代码）
  - [x] SubTask 1.2: 将适配器级 `MessageRecord` 迁移到 `models.py`，改用 `nonebot_plugin_orm.Model` 基类，表名改为 `lingchu_message_records`，保留 `raw_message`、`raw_event` 字段，移除 `api_name`/`api_result_summary`（由 `AuditRecord` 承担）
  - [x] SubTask 1.3: 将 `AuditRecord` 迁移到 `models.py`，改用 `nonebot_plugin_orm.Model` 基类，表名改为 `lingchu_audit_records`
  - [x] SubTask 1.4: 移除 `PlatformMessageRecord`（统一 ORM 后不再需要投影表）
  - [x] SubTask 1.5: 保留 `BlocklistEntry` 不变

- [x] Task 2: 删除 `database/message_storage.py`
  - [x] SubTask 2.1: 删除整个文件（`Base`、`_EngineState`、`_ENGINES`、`session_for()`、`storage_target()`、`adapter_slug()`、`message_store_root()`、`close_engines()`、`copy_message_fields()`、`cleanup_table()`、`fetch_one_message()` 等全部移除）
  - [x] SubTask 2.2: 确认无其他模块直接导入 `message_storage`（仅 `repositories/message_store.py` 和测试文件引用）

- [x] Task 3: 重写 `repositories/message_store.py`
  - [x] SubTask 3.1: `record_event_received()` 改用 `orm_crud.upsert()` 按 `(platform, adapter, bot_id, conversation_id, message_id)` 唯一约束写入
  - [x] SubTask 3.2: `record_matcher_result()` 改用 `orm_crud.get_one()` + `orm_crud.update()` 更新处理状态
  - [x] SubTask 3.3: `record_api_call()` 改用 `orm_crud.create()` 写入 `AuditRecord`
  - [x] SubTask 3.4: `list_recent_messages()` 改用 `orm_crud.list_items()` 直接查询 `MessageRecord` 表，按 `platform`/`adapter`/`conversation_id`/`user_id` 过滤
  - [x] SubTask 3.5: `cleanup_expired_messages()` 改用 `orm_crud.delete()` 按 `created_at` 过期条件删除 `MessageRecord` 和 `AuditRecord`
  - [x] SubTask 3.6: 移除 `_upsert_platform_projection()` 和所有对 `message_storage` 模块的引用

- [x] Task 4: 重组 `database/json5_store.py` 为 `json5_store/` 包
  - [x] SubTask 4.1: 创建 `database/json5_store/__init__.py`，重新导出所有公共 API（`RobustAsyncJSON5DB`、`load_json5_dict_sync`、`ensure_json5_dict_file_sync` 及所有异常类）
  - [x] SubTask 4.2: 创建 `database/json5_store/exceptions.py`，迁移所有异常类（`DatabaseError`、`InvalidDefaultTypeError`、`InvalidJSON5RootTypeError`、`JSON5FileReadError`、`DatabaseClosedError`、`InvalidKeyPathError`、`EmptyPathSegmentError`、`LoadTaskCancelledError`、`LoadStateMismatchError`、`CallbackTypeError`、`AtomicReplacementError`、`WatchAlreadyRunningError`、`IntermediateListNoneError`、`ParentPathResolutionError`、`TerminalPathResolutionError`）
  - [x] SubTask 4.3: 创建 `database/json5_store/_sync.py`，迁移 `load_json5_dict_sync()` 和 `ensure_json5_dict_file_sync()` 及其依赖的异步助手（`_deepcopy_async`、`_json5_loads_async`、`_json5_dumps_async`）
  - [x] SubTask 4.4: 创建 `database/json5_store/_async_db.py`，迁移 `RobustAsyncJSON5DB` 类
  - [x] SubTask 4.5: 删除原 `database/json5_store.py` 文件
  - [x] SubTask 4.6: 确认 `core/runtime_config.py` 中的导入路径 `from ..database.json5_store import ...` 仍然有效

- [x] Task 5: 添加 Alembic 迁移系统
  - [x] SubTask 5.1: 在 `.env.example` 中添加 `ALEMBIC_STARTUP_CHECK=false`（开发环境自动同步）
  - [x] SubTask 5.2: 执行 `nb orm revision -m "initial schema" --branch-label nonebot_plugin_lingchu_bot` 生成初始迁移脚本
  - [x] SubTask 5.3: 检查生成的迁移脚本，确保包含 `lingchu_message_records`、`lingchu_blocklist_entries`、`lingchu_audit_records` 三张表的 `create_table` 操作
  - [x] SubTask 5.4: 在 `pyproject.toml` 的 `[tool.nonebot]` 中确认 `nonebot_plugin_lingchu_bot` 已注册（若未注册则添加）

- [x] Task 6: 更新 `__init__.py` 导出
  - [x] SubTask 6.1: 确认 `from .database import models as models` 仍然有效（包化后 json5_store 导入路径不变）
  - [x] SubTask 6.2: 确认 `from .database import json5_store as json5_store` 仍然有效（包化后导入路径不变）
  - [x] SubTask 6.3: 确认 `from .database import orm_crud as orm_crud` 仍然有效

- [x] Task 7: 更新测试文件
  - [x] SubTask 7.1: 重写 `tests/repositories/test_message_store.py`，移除对 `message_storage` 的直接引用，改用 mock `orm_crud` 函数测试仓储逻辑
  - [x] SubTask 7.2: 更新 `tests/services/test_messagestore.py`，更新 mock 路径（`repositories.message_store` 内部不再引用 `message_storage`）
  - [x] SubTask 7.3: 更新 `tests/database/test_json5_store.py`，确认导入路径从 `database.json5_store` 包导入仍然有效
  - [x] SubTask 7.4: 确认 `tests/database/test_orm_crud.py` 和 `tests/database/test_blocklist.py` 无需修改（API 未变）

- [x] Task 8: 运行全部检查
  - [x] SubTask 8.1: 运行 `task check`（ruff + pyright + ty）
  - [x] SubTask 8.2: 运行 `task test`（全部 Python 测试）
  - [x] SubTask 8.3: 运行 `task lint`（markdownlint + ESLint + tsc，若涉及文档变更）

# Task Dependencies

- [Task 3] depends on [Task 1] 和 [Task 2]（仓储层依赖统一模型和 message_storage 删除）
- [Task 5] depends on [Task 1]（迁移脚本依赖最终模型定义）
- [Task 7] depends on [Task 3] 和 [Task 4]（测试更新依赖仓储重写和 json5_store 包化）
- [Task 8] depends on [Task 1]-[Task 7]（全部检查在所有变更完成后执行）
- [Task 1] 和 [Task 2] 可并行（模型迁移和文件删除互不依赖）
- [Task 4] 和 [Task 1]-[Task 3] 可并行（json5_store 重组与数据库统一互不依赖）
- [Task 6] 可与 [Task 4] 并行（导出检查与 json5_store 包化相关但不阻塞）
