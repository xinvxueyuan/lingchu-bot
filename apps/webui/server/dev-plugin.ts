import path from "node:path";
import type { IncomingMessage, ServerResponse } from "node:http";
import type { Hono } from "hono";
import type { Plugin, ViteDevServer } from "vite";

import { createWebuiApp, prepareWebuiRuntime } from "./app.js";

/**
 * dev 统一运行时 Vite 插件（仅 dev 生效，排除在生产 tsconfig.server.json 构建外）：
 *
 * - 在 `configureServer` 中把现有 Hono app 挂载到 `/api`（同源直通，无代理）：
 *   `pnpm dev` = 单一 `react-router dev` 进程，一个 Node 进程同时提供页面（Vite dev + HMR）
 *   与 `/api` 后端（进程内 Hono）。
 * - env 合并：`server/config.ts` 导入时自动加载仓库根 `.env`（dev / prod 同一来源，
 *   替代旧 `tsx watch --env-file=../../.env` 约定）。
 * - `server/*` 变更经 watcher 自动 `server.restart()`（对齐旧 tsx watch 热重启体验）。
 *
 * 生产形态不受影响：build 时 `configureServer` 不执行；生产运行走
 * `server/index.ts`（`@hono/node-server` 独立进程，`/api` + 静态 + SSR）。
 */

/**
 * 将 Node Connect 的 IncomingMessage/ServerResponse 适配为 Web Request/Response，
 * 调用 Hono `app.fetch` 后回写响应（覆盖本项目场景的轻量转换：请求体较小，直接读入内存）。
 */
async function honoAdapter(
  app: Hono,
  req: IncomingMessage,
  res: ServerResponse,
): Promise<void> {
  const rawUrl = req.url ?? "/";
  const [pathname, search = ""] = rawUrl.split("?");
  const url = new URL(pathname + (search ? `?${search}` : ""), "http://localhost");

  const headers = new Headers();
  for (const [key, value] of Object.entries(req.headers)) {
    if (value === undefined) continue;
    headers.set(key, Array.isArray(value) ? value.join(", ") : value);
  }

  let body: BodyInit | undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    const chunks: Buffer[] = [];
    for await (const chunk of req) chunks.push(chunk as Buffer);
    if (chunks.length > 0) body = Buffer.concat(chunks);
  }

  const response = await app.fetch(
    new Request(url, { method: req.method, headers, body }),
  );

  res.statusCode = response.status;
  for (const [key, value] of response.headers) res.setHeader(key, value);
  res.end(response.body ? new Uint8Array(await response.arrayBuffer()) : undefined);
}

/** 仅处理 `/api` 路径；其余交还 Vite（dev 页面渲染 + HMR）。 */
function isApiRequest(req: IncomingMessage): boolean {
  const pathname = (req.url ?? "/").split("?")[0];
  return pathname === "/api" || pathname.startsWith("/api/");
}

export function webuiDevPlugin(): Plugin {
  let restartTimer: ReturnType<typeof setTimeout> | undefined;

  return {
    name: "lingchu-webui-dev-backend",
    apply: "serve",
    async configureServer(devServer: ViteDevServer) {
      const serverDir = path.resolve(process.cwd(), "server");

      // server/* 变更 → 整体重启 dev server（对齐旧 tsx watch 的即时热重启体验）。
      // `server.restart()` 会重新加载 vite 配置并再次执行 configureServer → Hono app 重新构建。
      const onServerFileChange = (file: string) => {
        const changed = path.resolve(file);
        if (changed !== serverDir && !changed.startsWith(serverDir + path.sep)) return;
        clearTimeout(restartTimer);
        restartTimer = setTimeout(() => {
          console.log("[webui] server/* 变更，正在重启 dev server…");
          void devServer.restart();
        }, 100);
      };
      devServer.watcher.on("add", onServerFileChange);
      devServer.watcher.on("change", onServerFileChange);
      devServer.watcher.on("unlink", onServerFileChange);

      // 首次对外服务前解析上游：显式 NONEBOT_BASE_URL 直接采用，否则本机嗅探（与生产入口一致）。
      await prepareWebuiRuntime();

      // dev 下 productionMode=false：createWebuiApp 只注册 /api 路由，页面由 Vite 渲染。
      const app = createWebuiApp();

      // 在 Vite 内部中间件之前挂载：/api 请求由进程内 Hono 同源直通处理（无代理、无二次握手），
      // 其余路径调 next() 交还给 Vite。
      devServer.middlewares.use((req, res, next) => {
        if (!isApiRequest(req)) {
          next();
          return;
        }
        honoAdapter(app, req, res).catch((error: unknown) => {
          console.error("[webui] /api 处理失败：", error);
          if (!res.headersSent) {
            res.statusCode = 500;
            res.end("WebUI backend error");
          }
        });
      });

      console.log(
        "[webui] 后端已挂载到 /api（同源直通，无代理）；修改 server/* 将自动重启 dev server",
      );
    },
  };
}
