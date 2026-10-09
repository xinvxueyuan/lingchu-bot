import { Hono } from "hono";

import { config } from "./config.js";
import {
  loginHandler,
  logoutHandler,
  meHandler,
  qqAvatarHandler,
} from "./handlers.js";
import { proxyHandler } from "./proxy.js";
import { staticHandler } from "./static.js";
import { overviewHandler } from "./overview.js";
import { resolveNonebotBaseUrl } from "./discover.js";

/**
 * 构建 WebUI Hono 应用（dev 插件与生产入口共用同一构造）：
 *
 * - `/api/auth/*`：唯一真实 Auth（登录 / 登出 / 会话）。
 * - `/api/overview`：概览聚合（WebUI 后端聚合 nonebot 原子 API，前端不直连 nonebot）。
 * - `/api/qq/avatar/:qq`：QQ 头像 CDN 代理（WebUI 后端直连，不转发 nonebot）。
 * - `/api/*`（其余）：转发中间件（校验 UBT 后转发 NoneBot）。
 * - 非 `/api`：仅生产模式注册静态托管 + SSR 兜底；dev 下页面由 Vite 渲染。
 */
export function createWebuiApp(): Hono {
  const app = new Hono();

  // 1. 前后端真实 Auth（唯一 Auth）
  app.post("/api/auth/login", loginHandler);
  app.post("/api/auth/logout", logoutHandler);
  app.get("/api/auth/me", meHandler);

  // 1b. 概览聚合（WebUI 后端聚合 nonebot 原子 API，一次性返回；前端不直连 nonebot）
  app.get("/api/overview", overviewHandler);

  // 2b. QQ 头像（WebUI 后端直接处理 CDN 代理，不转发到 nonebot）
  app.get("/api/qq/avatar/:qq", qqAvatarHandler);

  // 2. 转发中间件：匹配 /api/*，但把 /api/auth/* 交还给上方 auth 路由（next），
  //    其余路径执行代理转发（校验 UBT 后转发到 NoneBot）。
  app.use("/api/*", async (c, next) => {
    if (c.req.path.startsWith("/api/auth")) {
      await next();
      return;
    }
    return proxyHandler(c);
  });

  // 3. 静态资源 + SSR 兜底（兜底所有非 /api 路径）。
  //    仅生产模式注册：dev 下页面由 react-router dev(Vite) 提供。
  if (config.productionMode) {
    app.get("*", staticHandler);
  }

  return app;
}

/**
 * 启动前准备：解析 NoneBot 上游 base URL（显式设置则直接采用，否则本机嗅探）。
 * dev 插件与生产入口在首次对外服务前调用，保证 `getResolvedNonebotBaseUrl()`
 * 返回的是解析后的值。
 */
export async function prepareWebuiRuntime(): Promise<void> {
  await resolveNonebotBaseUrl();
}
