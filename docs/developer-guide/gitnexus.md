---
icon: lucide/network
title: GitNexus 工作流
---

## GitNexus 工作流

本仓库使用 GitNexus 做代码理解和影响面分析。修改代码符号前必须先确认上游依赖。

## 修改前

修改函数、类或方法前运行 upstream impact：

```text
gitnexus_impact({target: "symbolName", direction: "upstream"})
```

记录以下信息：

- 直接调用者。
- 受影响流程。
- 风险等级。

如果风险是 `HIGH` 或 `CRITICAL`，先暂停并说明风险，不要直接继续改动。

## 探索代码

陌生区域优先使用 query/context：

```text
gitnexus_query({query: "mute command flow"})
gitnexus_context({name: "milkybot_mute"})
```

这样可以先理解执行流，再决定改动位置。

## 提交前

提交前运行 detect changes：

```text
gitnexus_detect_changes()
```

确认变更集中在预期符号和执行流。如果结果包含无关文件或流程，先检查工作区。

## 重命名

不要用全局查找替换重命名符号。需要重命名时使用 GitNexus rename，以便同时处理调用关系和引用点。
