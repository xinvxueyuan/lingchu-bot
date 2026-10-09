# ADR-0005: WebUI 前后端统一打包、统一运行时

- **Status**: Accepted
- **Date**: 2026-08-27
- **Decider**: 用户部署决策（`.trae/specs/bundle-webui-unified-runtime/spec.md`）→ 取代 `webui-deploy-topology-layout` 的「三组件可分离部署」
- **Supersedes**: `.trae/specs/webui-deploy-topology-layout/spec.md`（「前端可独立静态托管 / `PUBLIC_API_BASE` 跨机」）、`.trae/specs/restore-webui-ssr/spec.md`（「`PUBLIC_API_BASE` 跨机能力保留」）
- **Note**: 沿用 ADR-0002 的编号约定（0001/0003/0004 为保留候选号），新决策从 0005 起按序记录。

## Context

WebUI 的 dev 与 prod 长期是**两套运行形态、多进程**：

1. **dev 双进程**：`dev:server`（`tsx watch` 跑 Hono）+ `dev:web`（Vite dev server + `/api` 代理）两个独立进程，用 `concurrently` 编排；改 `server/*` 时 `tsx watch` 单独重启后端，Vite 前端无感。
2. **prod 单进程但代码重复**：`server/index.ts` 同时做「创建 Hono app」与「启动监听」两件事，dev 插件无法复用同一份 app 组装逻辑——dev 走代理、prod 走进程内挂载，两条路径各自实现"把 `/api` 交给 Hono"。

部署产物同样分裂：`apps/webui/Dockerfile` 是 React Router 脚手架遗留模板（`npm ci` + `package-lock.json` + `my-app` 端口 3000 + `CMD npm run start`），在 pnpm monorepo 下必然失败；npm 包产物（`pnpm pack`）不含构建产物，解包不可直接运行。

此外，**pnpm filtered install 的一个反直觉行为**放大了 Docker 构建的难度：`pnpm install --filter <pkg>...` 会把 workspace root 的 devDependencies 也纳入安装范围（`...` 向上穿透）。root devDeps 中含 `gitnexus@1.6.9` → `@huggingface/transformers` → `onnxruntime-node`/`onnxruntime-web` 的巨型二进制链（数百 MB），官方 registry 下载超时；改用 npmmirror 镜像后，`gitnexus@1.6.9` 的 tarball 又因镜像同步滞后而 404，且 `--frozen-lockfile` 强制按 lockfile 固定版本拉取，无法绕过。

## Decision

**WebUI 前后端统一打包为一个 npm 包 / 一个 Docker 镜像，dev 与 prod 均为「单进程、单命令」，共享同一套 app 组装逻辑。**

1. **dev 统一运行时**：`pnpm dev` 收敛为单一 `react-router dev` 进程。新增 Vite 插件（`server/dev-plugin.ts`）在 `configureServer` 中通过 `honoAdapter` 将 Hono app 挂载到 `/api`（同源直通，无代理）；`server/*` 变更经防抖 watcher 触发 `devServer.restart()`，对齐旧 `tsx watch` 体验。移除 `dev:server` / `dev:web` / `concurrently` / vite `/api` 代理。
2. **生产统一运行时**：`server/index.ts` 拆出 `createApp()`，dev 插件与生产入口（`main`）复用同一函数组装 Hono app；生产单进程同时服务 `/api`（auth + 转发）与静态资源 + SSR，拓扑与既有一致，仅由共享代码保证不漂移。
3. **单体打包产物**：
   - `apps/webui/Dockerfile` 重写为 pnpm 多阶段构建：builder 阶段安装 webui（含 dev）依赖并产出 `build/client`、`build/server`、`dist/server`；runtime 阶段仅 `--prod` 安装 + 复制产物，`NODE_ENV=production` 单进程 `node dist/server/index.js` 启动。
   - **Docker 内删除 root devDependencies 后做非 frozen install**：webui 的依赖闭包（dependencies + devDependencies 均无 workspace 引用、无 root 依赖）完全独立于 root devDeps；删除后可绕开 gitnexus/onnxruntime 链，同时规避 npmmirror 对 lockfile 固定版本的同步滞后（非 frozen 让 pnpm 在容器内自行重新解析）。
   - `prepack` 先构建（`react-router build` → `build/client` + `build/server`，再 `build:server` → `dist/server`），保证 `pnpm pack` 产物开箱可运行。root `package.json` 的 `prepare` 改为 `husky || true`，避免容器内 `--prod` 安装时因无 husky 而 ELIFECYCLE。
4. **文档与记录**：新增 `docs/adr/0005-webui-unified-runtime.md`（本文件）；旧 spec 头部标注被取代；README / 环境变量表对齐。

## Consequences

**Positive:**

- **单进程、单命令**：dev 与 prod 都只有一个 Node 进程；`/api` 与页面同源，无代理转发环节，心智模型一致。
- **单一组装逻辑**：`createApp()` 被 dev 插件与生产入口共享，"`/api` 交给 Hono" 只有一份实现，dev 与 prod 不会漂移。
- **构建产物单一交付**：npm 包与 Docker 镜像都是「前后端一体」，部署模型收敛为「WebUI 单进程 + nonebot 独立进程」两进程模型；镜像不含构建工具（无 vite / typescript / react-router dev），体积与攻面更小。
- **Docker 构建可用且快**：删除 root devDeps 后，镜像安装不再触碰 onnxruntime 等巨型二进制；npmmirror 镜像加速国内拉取，`--fetch-retries/--fetch-timeout` 容忍网络抖动。
- **`pnpm pack` 开箱即用**：`prepack` 保证产物三件套齐备，解包后直接 `node dist/server/index.js` 运行。

**Negative:**

- Docker 镜像构建使用**非 frozen install**，与本地 `--frozen-lockfile` 严格校验不同：容器内的解析结果可能与 lockfile 有细微出入（仅影响 webui 闭包内包版本的宽松解析，`overrides` 仍由 `pnpm-workspace.yaml` 强制执行）。维护者需理解这一取舍，不得在容器内重新引入 root devDeps 依赖。
- root `prepare: husky || true` 代价：本地 husky 依然生效；容器内忽略失败。若未来 CI 依赖 `prepare` 强制失败语义，需另行处理。
- 前端不再可作独立静态产物跨机托管；`PUBLIC_API_BASE` 跨机能力移除（代码本就同源 `/api`，此为文档/心智对齐，非功能回退）。

## Alternatives considered

- **保留双进程 dev / 代理**：拒绝。与「统一运行时」目标冲突；代理是额外故障点，且 dev 与 prod 行为不一致。
- **保留脚手架 Dockerfile（`npm ci` + `my-app`）**：拒绝。monorepo 下无 `package-lock.json`，`npm ci` 必然失败；`npm run start` 依赖构建工具，`--omit=dev` 安装后不可用。
- **Docker 内继续 `--frozen-lockfile` + 官方 registry**：拒绝。frozen 强制拉取 lockfile 固定版本 gitnexus@1.6.9，官方 registry 上其 onnxruntime 二进制链下载超时；npmmirror 同步滞后（latest=1.6.6，tarball 404），均不可行。
- **filtered install 排除 root devDeps**：`--filter=!gitnexus`、`--include-workspace-root=false`、`pnpm deploy --legacy` 均经验证失败——pnpm 的 filtered install 总是包含 root devDeps 的第三方闭包。最终方案（容器内删除 root devDependencies + 非 frozen install）为最小可复现实验验证后得出结论。
- **分离打包（前端静态 + 后端容器）**：拒绝。SSR 前端必须由 Node 运行时承载，无法静态托管；且与用户「前后端一体」决策相悖。

## References

- Implementing spec: `.trae/specs/bundle-webui-unified-runtime/spec.md`
- Superseded specs: `.trae/specs/webui-deploy-topology-layout/spec.md`、`.trae/specs/restore-webui-ssr/spec.md`
- 格式基线: `docs/adr/0002-adapter-module-path-registry.md`
- 相关代码：`apps/webui/server/dev-plugin.ts`（Vite 插件挂载 Hono 到 `/api`）、`apps/webui/server/index.ts`（`createApp()`）、`apps/webui/Dockerfile`（单体镜像）
