# Tasks

## 阶段一：删除核心权限文件
- [x] Task 1: 删除权限命令处理器文件
  - [x] 删除 `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/group/permission.py`

- [x] Task 2: 删除权限服务层文件
  - [x] 删除 `src/plugins/nonebot_plugin_lingchu_bot/services/permissions.py`

- [x] Task 3: 删除权限仓库层文件
  - [x] 删除 `src/plugins/nonebot_plugin_lingchu_bot/repositories/permissions.py`

## 阶段二：清理数据库模型
- [ ] Task 4: 从 models.py 移除权限相关模型
  - [ ] 移除 `PermissionNode` 类
  - [ ] 移除 `PermissionGroup` 类
  - [ ] 移除 `PermissionGroupMember` 类
  - [ ] 移除 `LingchuUser` 类
  - [ ] 移除 `PlatformAccount` 类
  - [ ] 移除 `PermissionIdentityGroupMember` 类
  - [ ] 移除 `PlatformPermissionState` 类
  - [ ] 移除 `NativeRoleAssignment` 类
  - [ ] 移除 `PermissionGrant` 类
  - [ ] 移除 `NativeRoleMapping` 类
  - [ ] 移除 `CapabilityContract` 类
  - [ ] 移除 `PermissionAuditLog` 类

## 阶段三：清理命令处理依赖
- [ ] Task 5: 从 common.py 移除权限守卫
  - [ ] 移除 `_permission_guard` 函数
  - [ ] 移除 `_SUPERUSER_COMMAND_KEYS` 常量
  - [ ] 移除对 `services.permissions` 的导入
  - [ ] 修改 `selected_adapter_handle` 装饰器，移除权限守卫调用

- [ ] Task 6: 从 command_triggers.py 移除权限命令
  - [ ] 移除 `permission` 命令定义
  - [ ] 移除 `grant_permission` 命令定义
  - [ ] 移除 `sync_permissions` 命令定义
  - [ ] 移除 `create_permission_group` 命令定义
  - [ ] 移除 `delete_permission_group` 命令定义
  - [ ] 移除 `native_mapping` 命令定义
  - [ ] 移除 `permission_refresh` 命令定义
  - [ ] 移除 `permission_platform` 命令定义
  - [ ] 移除 `add_identity_group` 命令定义
  - [ ] 移除 `remove_identity_group` 命令定义
  - [ ] 移除 `clear_identity_group` 命令定义
  - [ ] 移除 `view_identity_group` 命令定义

## 阶段四：清理启动流程
- [ ] Task 7: 从 startup.py 移除权限初始化
  - [ ] 移除对 `ensure_default_permission_state` 的导入和调用
  - [ ] 移除对 `sync_superuser_identities` 的导入和调用

## 阶段五：清理菜单系统
- [ ] Task 8: 从 menu.py 移除权限管理菜单
  - [ ] 移除 `permission-management` 页面定义
  - [ ] 移除所有 `permission-management` 分区的 `MenuFeature` 定义
  - [ ] 更新 `MENU_PAGES` 元组
  - [ ] 更新 `MENU_FEATURES` 元组

## 阶段六：清理配置系统
- [ ] Task 9: 从 runtime_config.py 移除超级用户配置
  - [ ] 移除 `lingchu_superusers` 字段
  - [ ] 移除 `LingchuSuperusersValidationError` 类
  - [ ] 移除 `_decode_lingchu_superusers` 函数
  - [ ] 移除 `_validate_lingchu_uid` 函数
  - [ ] 移除 `_normalize_lingchu_accounts` 函数
  - [ ] 移除 `_normalize_lingchu_superusers` 验证器

- [ ] Task 10: 从 platforms/config.py 移除角色预设
  - [ ] 移除 `PlatformRolePreset` 类
  - [ ] 移除 `QQ_OWNER_COMMANDS` 常量
  - [ ] 移除 `QQ_ADMIN_COMMANDS` 常量
  - [ ] 移除 `QQ_MEMBER_COMMANDS` 常量
  - [ ] 移除 `QQ_ROLE_PRESETS` 常量
  - [ ] 移除 `PLATFORM_ROLE_PRESETS` 常量
  - [ ] 移除 `iter_platform_role_presets` 函数
  - [ ] 移除 `role_preset_for_group` 函数
  - [ ] 移除 `self_only_command_keys_for_group` 函数

## 阶段七：删除测试文件
- [ ] Task 11: 删除权限系统测试文件
  - [ ] 删除 `tests/services/test_permissions.py`

- [ ] Task 12: 更新其他测试文件
  - [ ] 从 `tests/start/test_startup.py` 移除权限相关测试
  - [ ] 从 `tests/core/test_runtime_config.py` 移除 superuser 配置测试

## 阶段八：清理命令处理器导入
- [ ] Task 13: 清理各命令处理器的权限导入
  - [ ] 从 `handle/qq/group/block.py` 移除权限相关导入
  - [ ] 从 `handle/qq/group/announcement.py` 移除权限相关导入
  - [ ] 从 `handle/qq/group/lifecycle.py` 移除权限相关导入
  - [ ] 从 `handle/qq/group/mute.py` 移除权限相关导入
  - [ ] 从 `handle/qq/group/member.py` 移除权限相关导入
  - [ ] 从 `handle/qq/group/profile.py` 移除权限相关导入

- [ ] Task 14: 清理适配器菜单处理器的权限导入
  - [ ] 从 `handle/qq/onebot/v11/default/menu.py` 移除权限相关导入
  - [ ] 从 `handle/qq/milky/v1_2/default/menu.py` 移除权限相关导入

## 阶段九：更新文档
- [ ] Task 15: 更新配置文档
  - [ ] 从 `apps/docs/content/docs/user-guide/configuration.mdx` 移除 superuser 配置说明
  - [ ] 从 `apps/docs/content/docs/user-guide/configuration.zh.mdx` 移除超级用户配置说明

- [ ] Task 16: 更新 README 文档
  - [ ] 从 `README.md` 移除权限系统相关说明
  - [ ] 从 `README-zh.md` 移除权限系统相关说明

## 阶段十：验证与清理
- [ ] Task 17: 运行测试验证
  - [ ] 执行 `task test` 确保所有剩余测试通过
  - [ ] 检查是否有未清理的权限系统引用

- [ ] Task 18: 清理导入引用
  - [ ] 搜索并移除所有对已删除模块的导入
  - [ ] 确保没有循环依赖或悬挂引用

## 任务依赖关系
- Task 1-3 可以并行执行（删除独立文件）
- Task 4 依赖 Task 1-3（需要确保没有代码引用这些模型）
- Task 5-6 依赖 Task 1-3（需要确保权限服务已删除）
- Task 7 依赖 Task 1-3（启动流程依赖权限服务）
- Task 8 依赖 Task 6（菜单依赖命令触发器定义）
- Task 9-10 可以并行执行（配置清理）
- Task 11-12 依赖 Task 1-3（测试依赖被测代码）
- Task 13-14 依赖 Task 1-3（命令处理器依赖权限服务）
- Task 15-16 可以在任何时候执行（文档更新）
- Task 17 依赖所有前置任务
- Task 18 贯穿整个过程
