# Lingchu Bot WebUI

Lingchu Bot 的 Web UI：**纯静态 SPA + oRPC 契约**，由 Python（NoneBot 同进程）托管。

> **不再有 Node 服务端进程。** 本目录只做两件事：把 React 应用构建成静态产物、把产物交给 Python 打包发布。
> 旧版的 `server/*.ts`（Hono 后端、JWT 签发、`/api/*` 反向代理、SSR）已整体移除。

## 架构

```text
浏览器  ──cookie 会话──▶  NoneBot（Python，同进程）  ──▶  OneBot V11 实现
   │                          │
   └──  GET  {base}/assets/* ─┤ StaticFiles（长缓存，文件名带构建哈希）
   └──  GET  {base}/*      ───┤ SPA fallback → index.html（深链刷新不 404）
   └──  {base}/v1/rpc/*    ───┘ oRPC 过程路由（services/webui/orpc.py）
```

- **单一接口层**：前端只与 oRPC 契约对话（`src/orpc/contract.ts`），后端由 `services/webui/orpc.py` 实现同一批过程。
  响应约定：成功 `{"json": ...}`；业务错误 `{"error": {"code","message","data"}}` 且 HTTP 200；
  仅**鉴权失败**为 HTTP 401（前端统一拦截跳登录页），输入非法为 400。
- **单一会话**：登录后由 Python 签发 HMAC 签名 Cookie（`lingchu_webui_session`），
  无 JWT、无 Node 侧口令缓存；Cookie 收窄到 `Path={base}`，进程重启即全部失效。
- **前缀单点派生**：全部对外路径由 `services/webui/paths.py` 生成，默认 `/lc/webui`。
- **产物随 wheel 发布**：`dist/client` → `src/plugins/nonebot_plugin_lingchu_bot/webui/dist/client`。

决策记录见 [ADR-0006](../../docs/adr/0006-webui-orpc-static-bundle.md)（取代 [ADR-0005](../../docs/adr/0005-webui-unified-runtime.md)）。

## 开发

先启动 NoneBot（默认 `http://127.0.0.1:8080`），再启动前端开发服务器：

```bash
pnpm install          # 仓库根
pnpm dev              # turbo → apps/webui 的 vite dev
```

`vite.config.ts` 的 `server.proxy` 把 `/lc/webui/v1/rpc` 代理到 `127.0.0.1:8080`，
因此 dev 与生产走同一条 oRPC 路径、同一套 Cookie 语义，不需要为开发单独实现一套接口。

- 改前端代码 → HMR 即时生效。
- 改 Python 侧（`services/webui/`）→ 需重启 NoneBot；前端无需重新构建。
- 未在 NoneBot 侧启用 WebUI 时，登录页会拿到 `password_not_configured`（`LINGCHU_WEBUI_PASSWORD` 为空即禁用登录）。
  可发送「启动WebUI」命令，或设置 `LINGCHU_WEBUI_AUTOMOUNT=true` 让 bot 启动即挂载。

## 构建与打包

```bash
pnpm webui:build      # react-router build → apps/webui/dist/client
pnpm webui:stage      # 复制到 src/plugins/nonebot_plugin_lingchu_bot/webui/dist/client
uv build              # 产出含 WebUI 的 wheel
```

- **顺序有依赖**：`webui:stage` 必须先于 `uv build`，否则 wheel 内没有页面。
  运行时缺失产物不会静默 404，而是返回 503 并附上构建提示。
- 产物目录：
  - `apps/webui/dist/client/` —— 构建输出（gitignore）；
  - `src/plugins/nonebot_plugin_lingchu_bot/webui/dist/client/` —— 打包落点（随 wheel 分发）。
- 开发机上看构建产物的真实效果：让 NoneBot 跑在 `8080`，直接访问 `http://127.0.0.1:8080/lc/webui/`。

## 测试

```bash
pnpm --filter lingchu-bot-webui test        # vitest run
```

- `src/__tests__/orpc-client.test.ts` —— `buildRpcUrl(base)` 的路径派生契约（与 `paths.py` 同源）。
- `src/__tests__/contract-parity.test.ts` —— overview 输出 schema 的等价性断言：
  全字段可解析、`errors` 接受任意字符串值、可选块缺失仍可解析（`errors` 必须存在）。

## 环境变量

全部由 Python 侧读取（`core/config.py` ↔ NoneBot 配置透传），前端不读任何环境变量。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LINGCHU_WEBUI_PASSWORD` | 空 | 登录口令。**空值 = 禁用登录（fail-closed）** |
| `LINGCHU_WEBUI_BASE_PATH` | `/lc/webui` | 挂载前缀。非法值（含空白、`..`、命中 `/api` `/onebot` `/docs` 等保留路径）降级为默认值并告警，不阻断启动 |
| `LINGCHU_WEBUI_SESSION_TTL` | `43200` | 会话有效期（秒），非正值回退默认 |
| `LINGCHU_WEBUI_AUTOMOUNT` | `false` | `true` 时 bot 启动即挂载 WebUI |

已移除（仅为旧 Node 层存在）：`LINGCHU_WEBUI_PORT`、`LINGCHU_WEBUI_DISCOVER_PORTS`、
`NONEBOT_BASE_URL`、`WEBUI_JWT_SECRET`。

## 目录结构

```text
apps/webui/
  src/
    orpc/            # oRPC 契约与客户端（契约是前后端唯一真相源）
    routes/          # SPA 路由
    components/      # 页面组件与 shadcn/ui 组件源
    __tests__/       # Vitest
  dist/client/       # 构建输出（gitignore）
```

## 相关文档

- 架构决策：[ADR-0006](../../docs/adr/0006-webui-orpc-static-bundle.md)
- 被取代的决策：[ADR-0005](../../docs/adr/0005-webui-unified-runtime.md)
