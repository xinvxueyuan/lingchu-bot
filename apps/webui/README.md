# Lingchu Bot WebUI

Lingchu Bot 的 Web UI：基于 React Router 8（SSR / framework 模式）+ Hono 的**前后端统一单进程运行时**。同一 Node 进程同时承载

- `/api` 后端：Auth（签发 / 校验 UBT）+ 转发中间件（附密码头 → NoneBot 校验端点 + 上游 API）
- 页面：SSR 渲染 + `build/client` 静态资源

dev 与 prod 均为「单进程、单命令」。

## Development

本仓库为 pnpm monorepo（workspace root 在仓库根）。在仓库根执行：

```bash
pnpm install
pnpm dev
```

`pnpm dev` 只启动**一个** `react-router dev`（Vite）进程：Vite 插件在 `configureServer` 中把后端 Hono app 挂载到 `/api`（同源直通，无代理）。页面默认 `http://localhost:5173`。

- 修改 frontend 代码 → HMR 即时生效。
- 修改 `server/*.ts` → watcher 自动 `server.restart()`，无需手动重启，也无需预先 `pnpm build`（dev 下页面由 Vite 渲染，后端仅 /api）。

dev 后端监听 `LINGCHU_WEBUI_PORT`（默认 4173）仅供独立校验（如顺手访问 `/api/auth/me`）；开发时主要访问 5173 即可。

## Building for Production

```bash
pnpm build          # react-router build → build/client + build/server
pnpm build:server   # tsc -p tsconfig.server.json → dist/server
```

产物：

```
dist/server/    # 服务端编译产物（入口 dist/server/index.js）
build/client/   # 静态资源
build/server/   # SSR 运行时（react-router build 的 request handler）
```

`package.json` 的 `files` 已含三者；`prepack` 会自动执行完整构建，保证 `pnpm pack` 产物开箱可运行。

## Deployment

### 单体 Docker 镜像（推荐）

前后端进入**同一镜像、单进程启动**。从仓库根构建（需要 root `.dockerignore` 允许携带 webui 源码与 workspace 清单）：

```bash
docker build -f apps/webui/Dockerfile -t lingchu-bot-webui .

docker run -p 4173:4173 \
  -e WEBUI_JWT_SECRET='<强随机值>' \
  -e LINGCHU_WEBUI_PASSWORD='<与 NoneBot .env 一致的密码>' \
  -e NONEBOT_BASE_URL='http://host.docker.internal:8080' \
  lingchu-bot-webui
```

- 多阶段构建：builder 安装 webui（含 dev）依赖并产出三份产物；runtime 仅 `--prod` 安装 + 复制产物，**不含构建工具**（无 vite / typescript / react-router dev），`NODE_ENV=production` 单进程 `node dist/server/index.js` 启动。
- 默认 registry 为 npmmirror 镜像（`--build-arg NPM_REGISTRY=...` 可覆盖）。
- 容器内不安装 root devDependencies（gitnexus → onnxruntime 数百 MB 二进制链与 webui 闭包无关），故镜像构建走非 frozen install，本地仍保持 `--frozen-lockfile` 严格校验。

### DIY Deployment

```bash
pnpm build
pnpm build:server
NODE_ENV=production node dist/server/index.js
```

或一行（`start` 内部依次执行 `react-router build` → `build:server` → 以 `NODE_ENV=production` 启动）：

```bash
pnpm start
```

生产模式下：`/api/*` 走 auth / 转发；其余路径由静态资源 + SSR 渲染页面（同时需要 `build/client` 与 `build/server`）。

## Environment variables

| 变量 | 说明 |
| --- | --- |
| `LINGCHU_WEBUI_PORT` | WebUI 后端监听端口（默认 `4173`；dev 与生产共用） |
| `NONEBOT_BASE_URL` | NoneBot 上游地址；显式设置后走覆盖模式，否则启动时嗅探本机端口（`LINGCHU_WEBUI_DISCOVER_PORTS`） |
| `LINGCHU_WEBUI_BASE_PATH` | 转发到上游的前缀路径（默认 `/lingchu-bot/webui/v1`） |
| `WEBUI_JWT_SECRET` | UBT JWT 签名密钥，生产环境必须配置强随机值 |
| `LINGCHU_WEBUI_PASSWORD` | WebUI 登录唯一密钥（NoneBot 校验端点对比用），生产环境必须配置 |

首页概览卡片无需额外配置：前端仅请求 `/api/overview` 聚合端点，WebUI 后端内部并发聚合 NoneBot 各只读端点（login-info / status / version-info / groups / friends / 灵初 status）一次性返回前端。前端不直连 NoneBot，也不接触任何内部细节；单区块失败时展示独立错误引导。

## Related docs

- 部署 / 运行决策：`docs/adr/0005-webui-unified-runtime.md`
- 实现 spec：`.trae/specs/bundle-webui-unified-runtime/spec.md`
