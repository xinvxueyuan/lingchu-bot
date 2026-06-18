# Tasks

- [x] Task 1: 新增注册表模型
  - [x] SubTask 1.1: 在 `database/models.py` 中新增 `Platform` 模型（表名 `lingchu_platforms`），字段：`id`、`platform_id`(unique)、`display_name`、`capabilities`(Text JSON)、`implemented`(Boolean)、`created_at`、`updated_at`
  - [x] SubTask 1.2: 在 `database/models.py` 中新增 `Adapter` 模型（表名 `lingchu_adapters`），字段：`id`、`adapter_id`(unique)、`platform_id`(indexed)、`display_name`、`nonebot_adapter_id`、`created_at`、`updated_at`
  - [x] SubTask 1.3: 在 `database/models.py` 中新增 `ProtocolImplementation` 模型（表名 `lingchu_protocol_implementations`），字段：`id`、`protocol_id`(indexed)、`adapter_id`(indexed)、`display_name`、`module_path`、`created_at`、`updated_at`，唯一约束 `(adapter_id, protocol_id)`

- [x] Task 2: 修改现有模型列名和新增 protocol_id
  - [x] SubTask 2.1: `MessageRecord` 重命名 `platform` → `platform_id`、`adapter` → `adapter_id`，新增 `protocol_id`(String(64), nullable, indexed)，更新唯一约束包含 `protocol_id`
  - [x] SubTask 2.2: `AuditRecord` 重命名 `platform` → `platform_id`、`adapter` → `adapter_id`，新增 `protocol_id`(String(64), nullable, indexed)
  - [x] SubTask 2.3: `BlocklistEntry` 新增 `protocol_id`(String(64), nullable, indexed)

- [x] Task 3: 扩展 registry.py 支持协议实现注册
  - [x] SubTask 3.1: 在 `platforms/registry.py` 中新增 `ProtocolImplementationInfo` 数据类，包含 `protocol_id`、`adapter_id`、`display_name`、`module_path`
  - [x] SubTask 3.2: 新增 `_PROTOCOL_IMPLEMENTATIONS` 字典，注册当前所有协议实现（onebot11: default/llonebot/napcat，milky: default/llbot）
  - [x] SubTask 3.3: 新增 `get_protocol_implementations(adapter_id)` 函数返回指定适配器的协议实现列表
  - [x] SubTask 3.4: 新增 `export_registry_for_seeding()` 函数，返回可用于数据库种子数据的结构化元数据

- [x] Task 4: 实现启动时种子数据同步
  - [x] SubTask 4.1: 新增 `repositories/registry.py`，实现 `seed_registry_tables()` 函数，从 `export_registry_for_seeding()` 读取元数据并 upsert 到三张注册表
  - [x] SubTask 4.2: 在 `start/startup.py` 中调用 `seed_registry_tables()`（在适配器加载之后）

- [x] Task 5: 更新仓储层适配新列名
  - [x] SubTask 5.1: `repositories/message_store.py` 中所有 `platform=` 改为 `platform_id=`，`adapter=` 改为 `adapter_id=`，新增 `protocol_id` 参数
  - [x] SubTask 5.2: `repositories/blocklist.py` 新增 `protocol_id` 参数（可选），传入 `BlocklistEntry` 的 `protocol_id` 列

- [x] Task 6: 更新服务层传递 protocol_id
  - [x] SubTask 6.1: `services/messagestore.py` 中 `MessageIdentity` 新增 `protocol_id` 字段
  - [x] SubTask 6.2: `normalize_message_event()` 解析协议标识（从 bot 对象或适配器模块推断）
  - [x] SubTask 6.3: 所有 `repository.record_event_received()` / `record_matcher_result()` / `record_api_call()` 调用传递 `protocol_id`

- [x] Task 7: 编写 Alembic 迁移脚本
  - [x] SubTask 7.1: 执行 `nb orm revision -m "platform adapter protocol tables"` 生成迁移脚本
  - [x] SubTask 7.2: 手动编写迁移脚本，包含：新建 3 张注册表 + 修改 3 张现有表（重命名列、新增 protocol_id 列、更新唯一约束）
  - [x] SubTask 7.3: 删除旧数据库文件，验证 `nb orm upgrade` 能成功创建新 schema

- [x] Task 8: 更新测试文件
  - [x] SubTask 8.1: 更新 `tests/repositories/test_message_store.py`，适配 `platform_id`/`adapter_id`/`protocol_id` 新列名
  - [x] SubTask 8.2: 更新 `tests/repositories/test_blocklist.py`，新增 `protocol_id` 参数测试
  - [x] SubTask 8.3: 更新 `tests/services/test_messagestore.py`，适配 `protocol_id`
  - [x] SubTask 8.4: 新增 `tests/database/test_registry_seed.py`，测试种子数据同步逻辑
  - [x] SubTask 8.5: 确认 `tests/database/test_orm_crud.py` 无需修改（API 未变）

- [x] Task 9: 更新 __init__.py 导出和文档
  - [x] SubTask 9.1: `__init__.py` 导出新增的 `Platform`、`Adapter`、`ProtocolImplementation` 模型（通过 `from .database import models as models` 自动导出）
  - [x] SubTask 9.2: 更新 `AGENTS.md`、`CLAUDE.md`、`.github/note/AGENTS-zh.md` 的文件树和 Lessons Learned

- [x] Task 10: 运行全部检查
  - [x] SubTask 10.1: 运行 `task check`（ruff + pyright + ty）
  - [x] SubTask 10.2: 运行 `task test`（全部 Python 测试）
  - [x] SubTask 10.3: 运行 `task lint`（markdownlint + ESLint + tsc）

# Task Dependencies

- [Task 2] depends on [Task 1]（修改现有模型时需确认新模型不冲突）
- [Task 3] depends on [Task 1]（协议实现注册需要模型定义）
- [Task 4] depends on [Task 1] 和 [Task 3]（种子数据同步依赖注册表模型和 registry 导出）
- [Task 5] depends on [Task 2]（仓储层适配依赖模型列名变更）
- [Task 6] depends on [Task 5]（服务层传递依赖仓储层参数变更）
- [Task 7] depends on [Task 1]-[Task 2]（迁移脚本依赖最终模型定义）
- [Task 8] depends on [Task 5]-[Task 6]（测试更新依赖仓储和服务层变更）
- [Task 9] depends on [Task 1]-[Task 8]
- [Task 10] depends on [Task 1]-[Task 9]
- [Task 1] 和 [Task 2] 可并行（新模型和修改现有模型互不依赖）
- [Task 3] 可与 [Task 1]-[Task 2] 并行（registry.py 扩展不依赖模型定义）
