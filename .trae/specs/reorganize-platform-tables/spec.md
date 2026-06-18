# 重组平台/适配器/协议库表结构 Spec

## Why

上一轮存储重组将数据库体系统一到 `nonebot_plugin_orm`，但现有库表结构仍存在三个问题：(1) 命名不一致——`MessageRecord`/`AuditRecord` 用 `platform`/`adapter`，`BlocklistEntry` 用 `platform_id`/`adapter_id`；(2) 协议维度缺失——handle 层有三级结构（平台→适配器→协议实现如 `default`/`napcat`/`llonebot`），但数据库表无法区分同一适配器的不同协议实现；(3) 无注册表——平台/适配器/协议元数据硬编码在 `registry.py`，无法通过数据库查询/关联。

## What Changes

- **BREAKING**: `MessageRecord` 重命名 `platform` → `platform_id`、`adapter` → `adapter_id`，新增 `protocol_id` 列
- **BREAKING**: `AuditRecord` 重命名 `platform` → `platform_id`、`adapter` → `adapter_id`，新增 `protocol_id` 列
- **BREAKING**: `BlocklistEntry` 新增 `protocol_id` 列（nullable，支持协议级黑名单）
- **BREAKING**: 新增 `Platform` 注册表（`lingchu_platforms`），存储平台元数据
- **BREAKING**: 新增 `Adapter` 注册表（`lingchu_adapters`），存储适配器元数据
- **BREAKING**: 新增 `ProtocolImplementation` 注册表（`lingchu_protocol_implementations`），存储协议实现元数据
- 新增启动时种子数据机制，从 `registry.py` 同步元数据到注册表
- 更新 `repositories/message_store.py` 和 `repositories/blocklist.py` 适配新列名
- 更新 `services/messagestore.py` 传递 `protocol_id`
- 更新所有受影响的测试文件
- 编写新 Alembic 迁移脚本（仅新部署，不保留旧数据）

## Impact

- Affected specs: `reorganize-storage-structure`（上一轮重组的延续）
- Affected code:
  - `src/plugins/nonebot_plugin_lingchu_bot/database/models.py` — 重命名列、新增 `protocol_id`、新增 3 个注册表模型
  - `src/plugins/nonebot_plugin_lingchu_bot/repositories/message_store.py` — 适配 `platform_id`/`adapter_id`/`protocol_id`
  - `src/plugins/nonebot_plugin_lingchu_bot/repositories/blocklist.py` — 新增 `protocol_id` 参数
  - `src/plugins/nonebot_plugin_lingchu_bot/services/messagestore.py` — 传递 `protocol_id`
  - `src/plugins/nonebot_plugin_lingchu_bot/platforms/registry.py` — 新增协议实现注册、种子数据导出
  - `src/plugins/nonebot_plugin_lingchu_bot/start/` — 启动时种子数据同步
  - `tests/repositories/test_message_store.py` — 适配新列名
  - `tests/repositories/test_blocklist.py` — 适配新 `protocol_id` 参数
  - `tests/services/test_messagestore.py` — 适配 `protocol_id`
  - 新增 `tests/database/test_registry_seed.py` — 注册表种子数据测试
  - 新增 Alembic 迁移脚本

## ADDED Requirements

### Requirement: 平台注册表

系统 SHALL 提供 `lingchu_platforms` 表存储平台元数据，包括平台标识、显示名、能力集合和实现状态。

#### Scenario: 启动时种子数据

- **WHEN** 应用启动时
- **THEN** 从 `registry.py` 的 `PlatformProfile` 定义同步平台元数据到 `lingchu_platforms` 表（upsert）

#### Scenario: 查询平台能力

- **WHEN** 需要查询某平台的能力集合时
- **THEN** 可通过 `platform_id` 关联 `lingchu_platforms` 表获取 `capabilities` 字段

### Requirement: 适配器注册表

系统 SHALL 提供 `lingchu_adapters` 表存储适配器元数据，包括适配器标识、所属平台、显示名和 NoneBot 适配器 ID。

#### Scenario: 启动时种子数据

- **WHEN** 应用启动时
- **THEN** 从 `registry.py` 的 `adapter_name_map` 同步适配器元数据到 `lingchu_adapters` 表（upsert）

### Requirement: 协议实现注册表

系统 SHALL 提供 `lingchu_protocol_implementations` 表存储协议实现元数据，包括协议标识、所属适配器、显示名和模块路径。

#### Scenario: 启动时种子数据

- **WHEN** 应用启动时
- **THEN** 从 `handle/qq/adapters/__init__.py` 的 `_ADAPTER_MODULES` 配置同步协议实现元数据到 `lingchu_protocol_implementations` 表（upsert）

#### Scenario: 协议实现唯一性

- **WHEN** 同一适配器下注册协议实现时
- **THEN** `(adapter_id, protocol_id)` 组合唯一

### Requirement: 协议维度追踪

系统 SHALL 在消息记录、审计记录和黑名单条目中支持 `protocol_id` 列，用于追踪数据来源的具体协议实现。

#### Scenario: 消息记录包含协议信息

- **WHEN** 消息事件通过特定协议实现处理时
- **THEN** `MessageRecord.protocol_id` 记录协议标识（如 `napcat`、`llonebot`），未确定时为 NULL

#### Scenario: 审计记录包含协议信息

- **WHEN** API 调用通过特定协议实现发起时
- **THEN** `AuditRecord.protocol_id` 记录协议标识

## MODIFIED Requirements

### Requirement: 统一命名规范

所有运行时表 SHALL 使用 `platform_id`/`adapter_id` 作为列名，不再混用 `platform`/`adapter`。

#### Scenario: MessageRecord 列名统一

- **WHEN** 查询消息记录时
- **THEN** 使用 `platform_id`/`adapter_id` 作为筛选条件，而非 `platform`/`adapter`

#### Scenario: AuditRecord 列名统一

- **WHEN** 查询审计记录时
- **THEN** 使用 `platform_id`/`adapter_id` 作为筛选条件

### Requirement: 消息存储仓储

修改后的 `repositories/message_store.py` 将使用 `platform_id`/`adapter_id`/`protocol_id` 作为字段名。

#### Scenario: 记录消息接收

- **WHEN** 调用 `record_event_received()`
- **THEN** 使用 `platform_id`/`adapter_id`/`protocol_id` 字段写入，唯一约束包含 `protocol_id`

#### Scenario: 查询消息记录

- **WHEN** 调用 `list_recent_messages()`
- **THEN** 支持按 `platform_id`/`adapter_id`/`protocol_id` 过滤

### Requirement: 黑名单仓储

修改后的 `repositories/blocklist.py` 将支持 `protocol_id` 参数。

#### Scenario: 协议级黑名单

- **WHEN** 需要针对特定协议实现设置黑名单时
- **THEN** 可通过 `protocol_id` 参数限定作用域

## REMOVED Requirements

### Requirement: 混合命名规范

**Reason**: `MessageRecord`/`AuditRecord` 使用 `platform`/`adapter`，`BlocklistEntry` 使用 `platform_id`/`adapter_id`，命名不一致导致查询和代码理解困难
**Migration**: 统一为 `platform_id`/`adapter_id`，编写新迁移脚本（仅新部署）
