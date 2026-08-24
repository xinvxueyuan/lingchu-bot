# 缺陷修复批次报告 — fix/defects-20260824-fail-closed-hardening

- 分支：`fix/defects-20260824-fail-closed-hardening`（基于 `main` @ `6d3e8d9`）
- 日期：2026-08-24
- 主题：fail-open 收敛、静默失败治理、性能与防御纵深加固
- 提交数：9（每缺陷域一笔，gitmoji + Conventional Commits）

## 1. 缺陷清单与优先级

| # | 严重度 | 类别 | 缺陷 | 位置 | 提交 |
| --- | --- | --- | --- | --- | --- |
| D01 | 高 | 安全/功能 | URL 图片下载在默认 driver 下静默失效（`get_session` 缺失返回 None 且零日志） | `core/http_security.py` | `6470486` |
| D02 | 高 | 安全 | `download_public_http_bytes` 无默认超时，httpx driver 把 `timeout=None` 解释为全部超时禁用，慢速服务器可无限挂起协程（SSRF 慢速滴流绕过） | `core/http_security.py` | `6470486` |
| D03 | 高 | 性能 | 菜单权限过滤 N+1：每个 command_key 4 条 SQL，单次菜单渲染 120+ 条串行查询 | `permissions/service.py` | `d28b630` |
| D04 | 高 | 安全 | 目标特权检查 fail-open ×2：`ActionFailed` 时放行，admin/owner 保护闸门被跳过 | `onebot11/default/common.py`、`remote.py` | `6bd36f5` |
| D05 | 高 | 安全 | `_can_recall_sender` fail-open：无法确认角色时允许撤回，可能撤回 admin/owner 消息 | `onebot11/default/mute.py` | `4400954` |
| D06 | 中 | 稳定 | recall 链路只捕获 `ActionFailed`，`NetworkError` 使命令中途崩溃、统计失真 | `onebot11/default/mute.py` | `4400954` |
| D07 | 中 | 性能 | 同一 sender 角色查询无缓存：撤回同用户 100 条 = 100 次 `no_cache` 成员查询 | `onebot11/default/mute.py` | `4400954` |
| D08 | 中 | 安全 | 菜单 fail-open：event 为 None 时返回 None 被下游当"不过滤"，全量命令暴露，违反 AGENTS.md "Menus fail closed" | `onebot11/default/menu.py`、`telegram/default/menu.py` | `7eee709` |
| D09 | 中 | 稳定 | `event_preprocessor` / `on_called_api` 无兜底 try/except，存储 bug 会终止事件分发（所有群命令无响应） | `hooks/handlers/` | `351a1c7` |
| D10 | 中 | 稳定 | `execute_persistent_job` 读路径无保护：DB 短暂不可用/payload 损坏直接向 APScheduler 抛异常 | `services/scheduler.py` | `585d425` |
| D11 | 中 | 稳定 | `remove_persistent_job` 未捕获 `SchedulerNotRunningError` | `services/scheduler.py` | `585d425` |
| D12 | 中 | 安全纵深 | uniseg `image.path` 无边界校验直接透传 `Path()`，未来适配器填充该字段即构成任意文件读取外发（当前不可达） | `commands/announcement.py`、`profile.py` | `963d006` |
| D13 | 低 | 健壮 | 图片 raw 类型假定非 BytesIO 即 bytes，memoryview 触发 `TypeError` 炸命令 | `commands/announcement.py`、`profile.py` | `963d006` |
| D14 | 低 | 可观测 | `ensure_config_files` 吞异常无原因；重启反馈非异常失败分支静默；shutdown 失败只记类名；recall 依赖注入缺失静默返回 | `core/`、`services/`、`hooks/` | `4d92619`、`351a1c7`、`4400954` |

遗留项执行（补充批次，提交 `45ff210` 后追加）：

- `record_audit_fire_and_forget` 去除伪 async：改为同步函数，24 处调用方去掉无意义 `await`，避免空转协程开销。
- `message_store` 序列化移出事件循环：拆分轻量 `extract_message_identity`（同步取 identity 写 state），重活 `normalize_message_event`（整事件 JSON 序列化）移入后台 job，事件循环每条消息不再被 CPU 序列化阻塞。
- API 审计写入加背压：有界队列（1000）+ 单 worker 批量落库（单事务串行化，缓解 SQLite 锁竞争）；队列满时丢弃并间隔告警；shutdown 时先停 worker 再 flush 队列，再执行清理任务。

## 2. 关键决策记录

| 决策 | 依据 |
| --- | --- |
| 特权检查 fail-open → fail-closed（CRITICAL 影响面） | 与项目既有基线 `operator_is_superuser_onebot11`（DB 异常返回 False）对齐；AGENTS.md 菜单 fail-closed 原则同源。影响 7 条执行流（kick/member/block/mute），行为变更方向为"更保守" |
| HTTP 下载强制默认 10s 超时（HIGH 影响面） | NoneBot httpx driver 将 `timeout=None` 解释为 `httpx.Timeout(None)`（四项全禁用），是唯一被绕过的超时防线；10s 覆盖公告图片/头像场景 |
| 图片 path 校验仅放行 localstore data/cache 目录 | url/raw 分支产物均落入 `plugin_config.cache_dir`；path 分支当前不可达（uniseg OneBot V11 builder 不填充），属防御纵深而非行为收缩 |
| 菜单空集而非"不过滤" | AGENTS.md "Menus fail closed. Hide commands the current identity or implementation cannot execute." |
| hooks 兜底用 `except Exception` + `logger.exception` | fail-soft 设计与 AGENTS.md BLE001 例外条款一致；已按治理规则登记 `pyproject.toml` per-file-ignores 并附理由 |
| 自动提交设置 `$env:HUSKY='0'` | AGENTS.md 明确允许自动化提交跳过钩子；全量检查（ruff/format/pyright/ty/pytest/smoke）已在本批次内手动执行通过 |

## 3. 测试报告

| 检查项 | 命令 | 结果 |
| --- | --- | --- |
| Lint | `uv run -m ruff check .` | 通过 |
| 格式 | `uv run -m ruff format --check .` | 通过 |
| 类型（Pyright strict） | `uv run -m pyright` | 0 errors / 0 warnings |
| 类型（ty） | `uv run -m ty check` | 通过 |
| 全量测试 | `uv run -m pytest` | **991 passed**，覆盖率 88.73%（门槛 88.5%） |
| 运行时冒烟（dev） | `ENVIRONMENT=dev nb.exe run` | `Application startup complete.`；OneBot V11 连接、双适配器 handler 导入无签名错误、事件循环流经修改后的 preprocessor/CalledAPI 钩子 |

新增/更新测试 18 个用例，覆盖：默认超时与缺会话告警、批量授权查询调用次数断言、特权检查 3 处 fail-closed、recall 网络异常与角色缓存、菜单 fail-closed、hooks 兜底、调度器 DB/解码异常、图片路径拒绝与 memoryview 兼容。

## 4. 验证与合规

- `detect_changes()`（GitNexus）：61 个符号变更、44 个受影响符号、25 个文件，与预期修复面一致；提交前对 `check_target_privilege`（CRITICAL）、`download_public_http_bytes`（HIGH）等核心符号执行了 impact 分析并向用户通报风险。
- 提交规范：9 笔提交全部符合 gitmoji + Conventional Commits（`.husky/commit-msg` 正则）。
- REUSE：新增 `.md` 由 `REUSE.toml` `**/*.md` glob（GFDL-1.3-or-later）覆盖。
- AGENTS/CLAUDE/中文镜像：本批次未新增仓库级规则，无需同步（BLE001 登记遵循既有治理条目）。

## 5. 验收建议

1. 重点关注行为变更面：特权检查拒绝路径（D04/D05）与菜单空集（D08）在真实群环境的体验。
2. `.env` 若未配置带 HTTP 客户端的 driver（`~fastapi+~httpx`），公告/头像 URL 图片现会输出明确告警而非静默跳过。
3. 后续可选立项：API 审计写入背压、`bulk_create` 的 `commit` 参数改名、`_conversation_id` 兜底前缀规范化。
