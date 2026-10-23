# ADR-0006: WebUI 静态 SPA + oRPC、Python 同进程托管

- **Status**: Accepted
- **Date**: 2026-10-23
- **Decider**: 用户部署决策（"WebUI 改为纯静态 SPA + oRPC，Python 同进程托管"）
- **Supersedes**: `docs/adr/0005-webui-unified-runtime.md`（"单进程单命令"的统一 Node 运行时）、`.trae/specs/bundle-webui-unified-runtime/spec.md`

## Context

ADR-0005 把 WebUI 收敛为「一个 Node 进程同时承载前端与 `/api`」，解决了 dev 双进程与实现漂移，但保留了 Node 运行时这一层。这层运行时的成本在落地后变得明显：

1. **多一个部署单元**。WebUI 是 bot 的附带功能，却要求部署方维护第二个进程（端口、健康检查、镜像内 `pnpm install`、与 NoneBot 的端口嗅探），与「一个 bot、一个容器」的心智模型相悖。
2. **重复实现与状态**。Node 侧做 JWT 签发 + 口令内存缓存 + `/api/overview` 聚合 + `/api/*` 反向代理，而这些数据的唯一来源是 NoneBot 同进程内的 OneBot 只读透传与插件自有信息。跨进程复制一层"恰好也是只读"的 API，本质是把进程内调用改写成了 HTTP 自调用。
3. **两套会话语义**。JWT（`WEBUI_JWT_SECRET`）+ 内存口令缓存意味着"进程重启后会话是否失效"取决于两处实现；同时 `WEBUI_JWT_SECRET` 与 `NONEBOT_BASE_URL` / `LINGCHU_WEBUI_DISCOVER_PORTS` / `LINGCHU_WEBUI_PORT` 都是只为这一层存在的配置项。
4. **产物分发困难**。前端产物要随 Python wheel 发布才有部署价值，而"能不能`pnpm pack`"与"能不能随 wheel 走"是两件事；ADR-0005 解决的是前者。

## Decision

**WebUI 改为纯静态 SPA + oRPC 契约，全部由 Python（NoneBot 同进程）托管，不存在 Node 服务端进程。**

1. **SPA 静态化**：前端只保留客户端渲染与静态产物（`dist/client`），不再有 SSR / `dist/server` / `server/*.ts` 运行时。
2. **oRPC 契约作为唯一接口真相源**：接口定义收敛为类型化契约（前端 `apps/webui/src/orpc/contract.ts`，后端 `services/webui/orpc.py`）。所有过程只读；响应沿用 oRPC 约定——成功 `{"json": ...}`，业务错误 `{"error": {"code","message","data"}}` 且 HTTP 200；仅**鉴权失败**保持 HTTP 401（便于前端统一拦截跳登录页），输入非法返回 400。
3. **Python 同进程托管**：`services/webui/launcher.py` 在 NoneBot 底层 Starlette 应用上先注册 oRPC 过程路由、再挂载静态应用（顺序不可颠倒，否则 SPA 兜底会把 RPC 请求吞成 `index.html`）；静态应用同时处理 `{base}/assets/*`（长缓存）与 `GET {base}/*` → `index.html`（深链刷新不 404）。
4. **挂载前缀可配置且单点派生**：默认 `/lc/webui`，`LINGCHU_WEBUI_BASE_PATH` 可覆盖。页面入口、静态资源、RPC 路由、旧兼容端点、会话 Cookie 的 `Path` 全部由 `services/webui/paths.py` 派生，任何消费方不得自行拼接前缀。前缀非法（含空白、遍历段、命中 `/api` / `/onebot` / `/docs` 等保留路径）时**降级为默认值并告警**，不阻断 bot 启动。
5. **产物入 wheel**：前端构建产物 `apps/webui/dist/client` 经 `pnpm webui:stage` 落到 `src/plugins/nonebot_plugin_lingchu_bot/webui/dist/client`，随 wheel 一起分发；源码环境下缺失则页面返回明确的 503 提示（提示运维执行 `pnpm webui:build && pnpm webui:stage`）。
6. **cookie 会话取代 JWT**：会话收敛为单个 HMAC 签名的无状态 Cookie（`lingchu_webui_session`）：载荷只含过期时间与随机 nonce，签名密钥由"配置口令 + 进程启动 nonce"派生，因此进程重启即让既有会话全部失效；Cookie 收窄到 `Path={base}`。`LINGCHU_WEBUI_PASSWORD` 为空即**禁用登录（fail-closed）**。
7. **配置收敛**：删除 `LINGCHU_WEBUI_PORT`、`LINGCHU_WEBUI_DISCOVER_PORTS`、`NONEBOT_BASE_URL`、`WEBUI_JWT_SECRET`；新增 `LINGCHU_WEBUI_BASE_PATH` / `LINGCHU_WEBUI_SESSION_TTL` / `LINGCHU_WEBUI_AUTOMOUNT`。

## Consequences

**Positive:**

- **部署单元回到一个**：bot 容器即 WebUI 服务，无第二进程、无端口嗅探、无跨进程反向代理，也不再需要为 WebUI 单独构建镜像。
- **会话语义单一且可预测**：签名密钥绑定进程生命周期，"重启即失效"是结构性保证，不需要清理表、缓存或吊销逻辑。
- **接口漂移变成机械可测**：契约是唯一真相源，迁移前后的数据结构等价性可由测试断言（而非人工比对）保证。
- **产物随 wheel 分发**：安装含 WebUI 的发行包即可用，不依赖额外的前端 CI 产物分发通道。
- **配置面收敛**：4 个仅为 Node 层存在的环境变量消失，剩下的 3 个都有明确默认值。

**Negative:**

- 前端首屏不再是 SSR：若将来要求 SEO 或首屏性能，需要重新引入服务端渲染，属于决策回退。
- WebUI 与 bot 生死绑定：bot 未启动或未挂载时 WebUI 不可用（旧方案下 Node 进程可独立存活，尽管其时也拿不到数据）。
- 前端产物进入 wheel 意味着**构建顺序有依赖**：发版流程必须先 `pnpm webui:build && pnpm webui:stage` 再 `uv build`，否则 wheel 内无页面（运行时表现为 503 提示，不会静默 404）。
- 契约由两份语言各自实现：`orpc.py` 与 `contract.ts` 必须同步改动，任何单边修改都会被前端解析或后端校验打回。

## Alternatives considered

- **保留 Node 后端、仅静态化前端**：拒绝。静态前端仍需一个承载 `/api` 的进程，成本与 ADR-0005 相同，只是把 SSR 换成了 SPA。
- **前端直连 NoneBot 既有只读端点（不经聚合层）**：拒绝。浏览器会拿到多个端点、多个错误形态与鉴权细节；聚合端点把"五块并发 + 单块失败独立降级"收敛为一次请求、一个契约。
- **JWT + 独立密钥（沿用旧方案）**：拒绝。需要额外密钥管理与过期/吊销策略，而单用户系统的会话需求只是"登录后一段时间内有效、重启后失效"，签名 Cookie 已完全覆盖。
- **前缀硬编码为 `/lc/webui`**：拒绝。同端口可能已有其它应用占用该路径，用户需要可改；改为可配置后，所有派生点必须单点化，否则会立刻出现"页面能开、API 404"的漂移。
- **前端产物单独发布（npm 包 / 独立静态托管）**：拒绝。WebUI 与 bot 版本强耦合（接口契约同步演进），分开分发会引入版本错配。

## References

- 被取代的决策: `docs/adr/0005-webui-unified-runtime.md`
- 相关代码：
  - `src/plugins/nonebot_plugin_lingchu_bot/services/webui/paths.py`（路径单点派生）
  - `src/plugins/nonebot_plugin_lingchu_bot/services/webui/orpc.py`（oRPC 过程路由）
  - `src/plugins/nonebot_plugin_lingchu_bot/services/webui/static.py`（静态资源 + SPA fallback）
  - `src/plugins/nonebot_plugin_lingchu_bot/services/webui/launcher.py`（幂等挂载与状态汇总）
  - `src/plugins/nonebot_plugin_lingchu_bot/core/webui_session.py`（HMAC 签名会话 Cookie）
  - `apps/webui/src/orpc/contract.ts`（前端契约真相源）
- 前端说明: `apps/webui/README.md`
- 格式基线: `docs/adr/0002-adapter-module-path-registry.md`
