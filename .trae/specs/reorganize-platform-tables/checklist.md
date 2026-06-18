# Checklist

## 注册表模型

- [x] `database/models.py` 中存在 `Platform` 模型，表名为 `lingchu_platforms`，包含 `platform_id`(unique)、`display_name`、`capabilities`、`implemented` 字段
- [x] `database/models.py` 中存在 `Adapter` 模型，表名为 `lingchu_adapters`，包含 `adapter_id`(unique)、`platform_id`(indexed)、`display_name`、`nonebot_adapter_id` 字段
- [x] `database/models.py` 中存在 `ProtocolImplementation` 模型，表名为 `lingchu_protocol_implementations`，包含 `protocol_id`、`adapter_id`、`display_name`、`module_path` 字段，唯一约束 `(adapter_id, protocol_id)`

## 现有模型修改

- [x] `MessageRecord` 中 `platform` 列已重命名为 `platform_id`
- [x] `MessageRecord` 中 `adapter` 列已重命名为 `adapter_id`
- [x] `MessageRecord` 中新增 `protocol_id` 列（String(64), nullable, indexed）
- [x] `MessageRecord` 的唯一约束包含 `protocol_id`
- [x] `AuditRecord` 中 `platform` 列已重命名为 `platform_id`
- [x] `AuditRecord` 中 `adapter` 列已重命名为 `adapter_id`
- [x] `AuditRecord` 中新增 `protocol_id` 列（String(64), nullable, indexed）
- [x] `BlocklistEntry` 中新增 `protocol_id` 列（String(64), nullable, indexed）
- [x] `BlocklistEntry` 的 `platform_id`/`adapter_id` 列名保持不变

## registry.py 扩展

- [x] `platforms/registry.py` 中新增 `ProtocolImplementationInfo` 数据类
- [x] `platforms/registry.py` 中注册了所有协议实现（onebot11: default/llonebot/napcat，milky: default/llbot）
- [x] `platforms/registry.py` 中新增 `get_protocol_implementations(adapter_id)` 函数
- [x] `platforms/registry.py` 中新增 `export_registry_for_seeding()` 函数

## 种子数据同步

- [x] `repositories/registry.py` 中实现 `seed_registry_tables()` 函数
- [x] `start/startup.py` 中调用 `seed_registry_tables()`
- [x] 启动后 `lingchu_platforms` 表包含 `qq` 平台记录
- [x] 启动后 `lingchu_adapters` 表包含 `~onebot.v11` 和 `~milky` 适配器记录
- [x] 启动后 `lingchu_protocol_implementations` 表包含 5 条协议实现记录

## 仓储层更新

- [x] `repositories/message_store.py` 中所有 `platform=` 改为 `platform_id=`
- [x] `repositories/message_store.py` 中所有 `adapter=` 改为 `adapter_id=`
- [x] `repositories/message_store.py` 中 `record_event_received()` 接受 `protocol_id` 参数
- [x] `repositories/message_store.py` 中 `list_recent_messages()` 支持按 `protocol_id` 过滤
- [x] `repositories/blocklist.py` 中 `upsert_block()` 接受可选 `protocol_id` 参数

## 服务层更新

- [x] `services/messagestore.py` 中 `MessageIdentity` 包含 `protocol_id` 字段
- [x] `services/messagestore.py` 中 `normalize_message_event()` 解析 `protocol_id`
- [x] `services/messagestore.py` 中所有 repository 调用传递 `protocol_id`

## 迁移脚本

- [x] 迁移脚本包含 3 张注册表的 `create_table` 操作
- [x] 迁移脚本包含 `MessageRecord` 列重命名和新增 `protocol_id`
- [x] 迁移脚本包含 `AuditRecord` 列重命名和新增 `protocol_id`
- [x] 迁移脚本包含 `BlocklistEntry` 新增 `protocol_id`
- [x] `nb orm upgrade` 能成功执行（或 `ALEMBIC_STARTUP_CHECK=false` 时启动自动建表）

## 测试

- [x] `tests/repositories/test_message_store.py` 适配 `platform_id`/`adapter_id`/`protocol_id`
- [x] `tests/repositories/test_blocklist.py` 新增 `protocol_id` 参数测试
- [x] `tests/services/test_messagestore.py` 适配 `protocol_id`
- [x] 新增 `tests/database/test_registry_seed.py` 测试种子数据同步
- [x] `tests/database/test_orm_crud.py` 无需修改

## 检查通过

- [x] `task check` 通过（ruff + pyright + ty + markdownlint + ESLint + tsc）
- [x] `task test` 全部通过（367 Python + 62 frontend 测试）
- [x] `task lint` 通过（markdownlint + ESLint + tsc）

## 文档更新

- [x] `AGENTS.md` 文件树和架构图已更新
- [x] `CLAUDE.md` 文件树和 Lessons Learned 已更新
- [x] `.github/note/AGENTS-zh.md` 文件树和 Lessons Learned 已更新
