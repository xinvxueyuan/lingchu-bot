# 移除权限系统 Spec

## Why
项目中存在一个处于半残废开发状态的权限系统，包含复杂的权限树、身份组、原生角色映射等功能。该系统增加了代码复杂度，但实际使用价值有限。彻底移除该系统可以简化代码库，降低维护成本。

## What Changes
- **BREAKING**: 移除所有权限系统相关的源代码文件
- **BREAKING**: 移除权限系统相关的数据库模型（12个表）
- **BREAKING**: 移除权限系统相关的服务层和仓库层代码
- **BREAKING**: 移除命令处理器中的权限守卫机制
- **BREAKING**: 移除启动时的权限状态初始化
- **BREAKING**: 移除菜单系统中的权限管理功能展示
- **BREAKING**: 移除命令触发器中的权限相关命令定义
- **BREAKING**: 移除运行时配置中的 `lingchu_superusers` 配置项
- **BREAKING**: 移除平台配置中的角色预设定义
- **BREAKING**: 移除权限系统相关的测试文件

## Impact
- Affected specs: 无（这是一个移除操作）
- Affected code:
  - `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/group/permission.py` (删除)
  - `src/plugins/nonebot_plugin_lingchu_bot/services/permissions.py` (删除)
  - `src/plugins/nonebot_plugin_lingchu_bot/repositories/permissions.py` (删除)
  - `src/plugins/nonebot_plugin_lingchu_bot/database/models.py` (移除12个模型类)
  - `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/group/common.py` (移除权限守卫)
  - `src/plugins/nonebot_plugin_lingchu_bot/start/startup.py` (移除权限初始化)
  - `src/plugins/nonebot_plugin_lingchu_bot/handle/menu.py` (移除权限管理菜单项)
  - `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/group/command_triggers.py` (移除权限命令)
  - `src/plugins/nonebot_plugin_lingchu_bot/core/runtime_config.py` (移除 superusers 配置)
  - `src/plugins/nonebot_plugin_lingchu_bot/platforms/config.py` (移除角色预设)
  - `tests/services/test_permissions.py` (删除)
  - `tests/start/test_startup.py` (移除权限相关测试)
  - `tests/core/test_runtime_config.py` (移除 superuser 配置测试)
  - `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/onebot/v11/default/menu.py` (移除权限相关导入)
  - `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/milky/v1_2/default/menu.py` (移除权限相关导入)
  - `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/group/block.py` (移除权限相关导入)
  - `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/group/announcement.py` (移除权限相关导入)
  - `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/group/lifecycle.py` (移除权限相关导入)
  - `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/group/mute.py` (移除权限相关导入)
  - `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/group/member.py` (移除权限相关导入)
  - `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/group/profile.py` (移除权限相关导入)
  - `apps/docs/content/docs/user-guide/configuration.mdx` (移除 superuser 配置说明)
  - `apps/docs/content/docs/user-guide/configuration.zh.mdx` (移除超级用户配置说明)
  - `README.md` (移除权限系统相关说明)
  - `README-zh.md` (移除权限系统相关说明)

## REMOVED Requirements

### Requirement: 权限树管理
**Reason**: 权限树系统过于复杂，实际使用价值有限
**Migration**: 无需迁移，直接移除

### Requirement: 身份组管理
**Reason**: 身份组功能与原生角色映射功能重叠，增加维护成本
**Migration**: 无需迁移，直接移除

### Requirement: 原生角色映射
**Reason**: 原生角色映射功能未完全实现，使用率低
**Migration**: 无需迁移，直接移除

### Requirement: 权限审计日志
**Reason**: 审计日志功能增加系统开销，实际使用有限
**Migration**: 无需迁移，直接移除

### Requirement: 超级用户管理
**Reason**: 超级用户管理功能可以后续通过更简单的方式实现
**Migration**: 无需迁移，直接移除

### Requirement: 平台权限开关
**Reason**: 平台权限开关功能未完全实现
**Migration**: 无需迁移，直接移除

### Requirement: 能力契约
**Reason**: 能力契约系统过于复杂
**Migration**: 无需迁移，直接移除

## MODIFIED Requirements

### Requirement: 命令处理
修改后的命令处理将不再包含权限守卫，所有命令对所有用户开放（除了平台本身的权限限制）。

#### Scenario: 用户执行命令
- **WHEN** 用户执行任何群管理命令
- **THEN** 命令直接执行，不再进行权限检查

### Requirement: 菜单系统
修改后的菜单系统将不再显示权限管理相关的功能项。

#### Scenario: 用户查看菜单
- **WHEN** 用户查看功能菜单
- **THEN** 菜单中不再包含"权限管理"分类及相关命令

### Requirement: 启动流程
修改后的启动流程将不再初始化权限状态。

#### Scenario: 应用启动
- **WHEN** 应用启动时
- **THEN** 不再调用权限状态初始化函数

## ADDED Requirements

无新增功能需求。
