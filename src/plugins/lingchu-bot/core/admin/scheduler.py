""" 
# 这是一个QQ机器人任务系统的核心需求文档，包含了系统类型、技术栈、核心需求和代码要求等信息。
{
  "系统类型": "QQ机器人任务系统",
  "技术栈": {
    "框架": "nonebot2",
    "适配器": "onebot11",
    "实现库": "llonebot",
    "定时模块": "nonebot-plugin-apscheduler",
    "数据库": "SQLite"
  },
  "核心需求": {
    "任务功能": [
      "类型支持：全局任务（所有群） / 单群任务（指定群）",
      "触发方式：定时任务（循环） / 单次任务（一次性）",
      "操作类型：",
      "  • 全员禁言",
      "  • 全员解禁",
      "  • 发送群公告"
    ],
    "数据存储": [
      "自动初始化数据库表结构",
      "SQLite存储任务数据（含全局/单群标识）",
      "字段包含：任务类型、群号、触发方式、时间参数、操作指令等"
    ],
    "权限管理": [
      {
        "用户层级": "普通管理员",
        "权限": [
          "查询本群所有任务（含全局任务）",
          "创建本群单群任务",
          "删除本群单群任务"
        ]
      },
      {
        "用户层级": "特殊权限用户",
        "权限": [
          "查询本群所有任务（含全局任务）",
          "创建全局任务",
          "删除全局任务"
        ]
      }
    ],
    "命令格式": "任务 [全局|单群] [定时|单次] <时间周期> <操作指令>",
    "示例命令": [
      "任务 全局 定时 1天2小时 全员禁言",
      "任务 单群 单次 30分钟 群公告 重要通知！"
    ],
    "任务执行逻辑": [
      "单次任务执行后自动删除",
      "定时任务持续执行直至手动删除"
    ],
    "初始化处理": [
      "启动时自动恢复数据库中的任务",
      "清理过期单次任务",
      "新增群聊时自动同步全局任务",
      "退出群聊时删除关联任务"
    ]
  },
  "代码要求": {
    "语言": "Python",
    "规范": "Pylance规范（严格类型注解）",
    "输出格式": "完整可运行代码"
  }
} 
"""
