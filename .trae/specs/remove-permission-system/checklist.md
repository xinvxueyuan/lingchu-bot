# 移除权限系统检查清单

## 文件删除检查
- [ ] `src/plugins/nonebot_plugin_lingchu_bot/handle/qq/group/permission.py` 已删除
- [ ] `src/plugins/nonebot_plugin_lingchu_bot/services/permissions.py` 已删除
- [ ] `src/plugins/nonebot_plugin_lingchu_bot/repositories/permissions.py` 已删除
- [ ] `tests/services/test_permissions.py` 已删除

## 数据库模型检查
- [ ] `PermissionNode` 模型已从 models.py 移除
- [ ] `PermissionGroup` 模型已从 models.py 移除
- [ ] `PermissionGroupMember` 模型已从 models.py 移除
- [ ] `LingchuUser` 模型已从 models.py 移除
- [ ] `PlatformAccount` 模型已从 models.py 移除
- [ ] `PermissionIdentityGroupMember` 模型已从 models.py 移除
- [ ] `PlatformPermissionState` 模型已从 models.py 移除
- [ ] `NativeRoleAssignment` 模型已从 models.py 移除
- [ ] `PermissionGrant` 模型已从 models.py 移除
- [ ] `NativeRoleMapping` 模型已从 models.py 移除
- [ ] `CapabilityContract` 模型已从 models.py 移除
- [ ] `PermissionAuditLog` 模型已从 models.py 移除

## 命令处理检查
- [ ] `common.py` 中的 `_permission_guard` 函数已移除
- [ ] `common.py` 中的 `_SUPERUSER_COMMAND_KEYS` 常量已移除
- [ ] `common.py` 中对权限服务的导入已移除
- [ ] `selected_adapter_handle` 装饰器不再调用权限守卫
- [ ] `command_triggers.py` 中所有权限相关命令已移除（12个命令）

## 启动流程检查
- [ ] `startup.py` 中 `ensure_default_permission_state` 调用已移除
- [ ] `startup.py` 中 `sync_superuser_identities` 调用已移除
- [ ] 相关导入语句已清理

## 菜单系统检查
- [ ] `menu.py` 中 `permission-management` 页面已移除
- [ ] `menu.py` 中所有权限管理相关的 `MenuFeature` 已移除
- [ ] 菜单渲染逻辑不再依赖权限系统

## 配置系统检查
- [ ] `runtime_config.py` 中 `lingchu_superusers` 字段已移除
- [ ] `runtime_config.py` 中 `LingchuSuperusersValidationError` 类已移除
- [ ] 相关验证函数和验证器已清理
- [ ] `platforms/config.py` 中 `PlatformRolePreset` 类已移除
- [ ] `platforms/config.py` 中所有角色预设常量已移除
- [ ] 相关辅助函数已清理

## 测试文件检查
- [ ] `tests/services/test_permissions.py` 已删除
- [ ] `tests/start/test_startup.py` 中权限相关测试已移除
- [ ] `tests/core/test_runtime_config.py` 中 superuser 配置测试已移除

## 命令处理器导入检查
- [ ] `handle/qq/group/block.py` 中权限相关导入已移除
- [ ] `handle/qq/group/announcement.py` 中权限相关导入已移除
- [ ] `handle/qq/group/lifecycle.py` 中权限相关导入已移除
- [ ] `handle/qq/group/mute.py` 中权限相关导入已移除
- [ ] `handle/qq/group/member.py` 中权限相关导入已移除
- [ ] `handle/qq/group/profile.py` 中权限相关导入已移除

## 适配器菜单处理器检查
- [ ] `handle/qq/onebot/v11/default/menu.py` 中权限相关导入已移除
- [ ] `handle/qq/milky/v1_2/default/menu.py` 中权限相关导入已移除

## 导入引用检查
- [ ] 项目中无对已删除模块的导入
- [ ] 无循环依赖问题
- [ ] 无悬挂引用

## 测试验证检查
- [ ] `task test` 所有测试通过
- [ ] `task lint` 无 lint 错误
- [ ] `task check` 类型检查通过

## 功能完整性检查
- [ ] 非权限相关命令（禁言、踢人、黑名单等）可正常执行
- [ ] 菜单功能正常显示（不含权限管理部分）
- [ ] 应用启动流程正常完成
- [ ] 数据库连接正常（无模型引用错误）

## 文档更新检查
- [ ] `apps/docs/content/docs/user-guide/configuration.mdx` 中 superuser 配置说明已移除
- [ ] `apps/docs/content/docs/user-guide/configuration.zh.mdx` 中超级用户配置说明已移除
- [ ] `README.md` 中权限系统相关说明已移除
- [ ] `README-zh.md` 中权限系统相关说明已移除
- [ ] 相关文档中权限系统说明已更新或移除
- [ ] 命令文档中权限相关命令已移除
