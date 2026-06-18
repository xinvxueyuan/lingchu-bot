# 重组数据库与 JSON 存储结构 Spec

## Why

当前项目存在两套并行的数据库体系：(1) 全局 ORM（`nonebot_plugin_orm`）管理 `BlocklistEntry` 和一个未使用的 `MessageRecord`；(2) 适配器级独立 SQLite（直接 SQLAlchemy）管理 `MessageRecord`、`PlatformMessageRecord`、`AuditRecord`，包含完整的自定义引擎管理代码。这导致命名冲突（两个同名 `MessageRecord` 类）、代码分散（`message_storage.py` 同时承担模型定义、引擎管理、查询助手三重职责）、缺少迁移系统（依赖 `create_all`），以及死代码（全局 `MessageRecord` 从未被导入使用）。

## What Changes

- **BREAKING**: 移除 `database/models.py` 中未使用的全局 `MessageRecord`（死代码，无任何导入引用）
- **BREAKING**: 将适配器级 `MessageRecord`、`AuditRecord` 迁移到 `database/models.py`，改用 `nonebot_plugin_orm.Model` 基类
- **BREAKING**: 移除 `PlatformMessageRecord` 投影表（统一 ORM 后可直接按 platform/adapter 过滤查询，无需跨库投影）
- **BREAKING**: 删除 `database/message_storage.py`（全部自定义引擎管理代码被 nonebot_plugin_orm 替代）
- **BREAKING**: 重写 `repositories/message_store.py`，改用 `orm_crud.py` 通用 CRUD 函数
- 新增 Alembic 迁移系统，使用 `nonebot_plugin_orm` 内置的 `nb orm` 命令管理 schema
- 将 `database/json5_store.py` 重组为 `database/json5_store/` 包，仅做代码组织，不改变 API
- 更新所有受影响的测试文件
- 更新 `__init__.py` 导出
- 更新 `.env.example` 添加 `ALEMBIC_STARTUP_CHECK` 配置

## Impact

- Affected specs: 无（这是基础设施重组）
- Affected code:
  - `src/plugins/nonebot_plugin_lingchu_bot/database/models.py` — 移除死代码 `MessageRecord`，新增 `MessageRecord`（合并版）和 `AuditRecord`
  - `src/plugins/nonebot_plugin_lingchu_bot/database/message_storage.py` — **删除**
  - `src/plugins/nonebot_plugin_lingchu_bot/database/json5_store.py` — 重组为 `json5_store/` 包
  - `src/plugins/nonebot_plugin_lingchu_bot/repositories/message_store.py` — 重写为使用 `orm_crud.py`
  - `src/plugins/nonebot_plugin_lingchu_bot/__init__.py` — 更新导出
  - `tests/repositories/test_message_store.py` — 重写测试
  - `tests/database/test_json5_store.py` — 更新导入路径
  - `tests/services/test_messagestore.py` — 更新 mock 路径
  - `.env.example` — 添加 `ALEMBIC_STARTUP_CHECK` 配置
  - 新增 `migrations/` 目录及初始迁移脚本

## ADDED Requirements

### Requirement: 统一数据库模型

系统 SHALL 将所有 ORM 模型统一使用 `nonebot_plugin_orm.Model` 基类，通过 `get_session()` 获取会话，不再维护自定义引擎管理代码。

#### Scenario: 消息记录存储

- **WHEN** 消息事件到达时
- **THEN** 通过 `orm_crud.upsert()` 将消息记录写入统一数据库，不再区分适配器级和全局级数据库

#### Scenario: 审计日志存储

- **WHEN** API 调用或机器人生命周期事件发生时
- **THEN** 通过 `orm_crud.create()` 将审计记录写入统一数据库

#### Scenario: 跨适配器消息查询

- **WHEN** 查询消息记录时未指定 adapter
- **THEN** 直接在统一表中按 `platform` 字段过滤查询，无需投影表

### Requirement: 数据库迁移系统

系统 SHALL 提供 Alembic 迁移脚本，通过 `nb orm upgrade` 命令同步数据库 schema。

#### Scenario: 首次部署

- **WHEN** 用户首次部署机器人
- **THEN** 执行 `nb orm upgrade` 创建所有数据库表

#### Scenario: 开发环境

- **WHEN** 开发者设置 `ALEMBIC_STARTUP_CHECK=false`
- **THEN** 启动时自动同步 schema，无需手动迁移

### Requirement: JSON5 存储包化

系统 SHALL 将 `json5_store.py` 重组为 `json5_store/` 包，保持所有公共 API 不变。

#### Scenario: 现有调用方

- **WHEN** `runtime_config.py` 或其他模块导入 `RobustAsyncJSON5DB`
- **THEN** 导入路径 `from ..database.json5_store import RobustAsyncJSON5DB` 仍然有效

## MODIFIED Requirements

### Requirement: 消息存储仓储

修改后的 `repositories/message_store.py` 将使用 `orm_crud.py` 的通用 CRUD 函数操作统一 ORM 模型，不再直接管理数据库引擎和会话。

#### Scenario: 记录消息接收

- **WHEN** 调用 `record_event_received()`
- **THEN** 使用 `orm_crud.upsert()` 按 `(platform, adapter, bot_id, conversation_id, message_id)` 唯一约束写入记录

#### Scenario: 清理过期消息

- **WHEN** 调用 `cleanup_expired_messages()`
- **THEN** 使用 `orm_crud.delete()` 按 `created_at` 过期条件删除 `MessageRecord` 和 `AuditRecord`，不再遍历多个数据库文件

### Requirement: 启动流程

修改后的启动流程不再调用适配器级数据库的初始化函数，改为依赖 `nonebot_plugin_orm` 的启动检查。

#### Scenario: 应用启动

- **WHEN** 应用启动时
- **THEN** `initialize_message_store()` 仅记录日志，不再初始化自定义引擎

## REMOVED Requirements

### Requirement: 适配器级独立 SQLite 引擎

**Reason**: 统一到 `nonebot_plugin_orm` 后，不再需要自定义 `Base`、`_ENGINES` 缓存、`session_for()`、`storage_target()`、`adapter_slug()` 等引擎管理代码
**Migration**: 所有数据访问改用 `orm_crud.py` + `get_session()`

### Requirement: 平台消息投影表

**Reason**: `PlatformMessageRecord` 投影表的存在是为了支持跨适配器查询，统一 ORM 后可直接在单表中按 `platform` 字段过滤
**Migration**: `list_recent_messages()` 改为直接查询 `MessageRecord` 表

### Requirement: 全局 MessageRecord（死代码）

**Reason**: `models.py` 中的全局 `MessageRecord` 从未被任何模块导入使用，其 `api_name`/`api_result_summary` 字段的功能已由 `AuditRecord` 承担
**Migration**: 无需迁移，直接删除

### Requirement: JSON5 单文件存储

**Reason**: `json5_store.py` 约 1000 行，异常类、同步助手、异步数据库类混在一个文件中
**Migration**: 重组为 `json5_store/` 包，`__init__.py` 保持全部公共 API 导出
