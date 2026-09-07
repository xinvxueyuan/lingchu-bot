import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { createRequestHandler } from "react-router";
import type { RequestHandler } from "react-router";
import type { Context, Handler } from "hono";
import { config } from "./config.js";

const MIME: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".webp": "image/webp",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".eot": "application/vnd.ms-fontobject",
  ".txt": "text/plain; charset=utf-8",
  ".map": "application/json; charset=utf-8",
};

function contentTypeFor(filePath: string): string {
  return MIME[path.extname(filePath).toLowerCase()] ?? "application/octet-stream";
}

/**
 * SSR request handler 单例（懒加载缓存）。
 * 首次调用时动态 import `build/server/index.js`（react-router build 的 named exports
 * 模块，无 default 导出），交给 `createRequestHandler(build, "production")` 生成 handler。
 * 构建产物缺失时返回 null（由调用方给出友好提示），不抛错。
 */
let ssrHandler: RequestHandler | null = null;

async function getSsrHandler(): Promise<RequestHandler | null> {
  if (ssrHandler) return ssrHandler;
  if (!fs.existsSync(config.serverEntry)) return null;
  // 动态 import 需要 file:// URL（Windows 盘符路径下 NodeNext 无法直接 import 绝对路径）。
  const build = await import(pathToFileURL(config.serverEntry).href);
  ssrHandler = createRequestHandler(build, "production");
  return ssrHandler;
}

/**
 * 静态托管 build/client + SSR 兜底：
 * - 对真实静态资源（build/client 内文件）直接返回；
 * - 对其余非 /api 请求交给 react-router 的 SSR request handler 渲染；
 * （不再使用 history fallback 回退 index.html，SSR 模式下页面由服务端渲染。）
 */
export const staticHandler: Handler = async (c: Context) => {
  // 仅处理非 /api 路径（auth / proxy 路由已先行注册）。
  const requestPath = decodeURIComponent(c.req.path);
  if (requestPath.startsWith("/api")) {
    return c.json({ error: "not_found" }, 404);
  }

  const relative = requestPath === "/" ? "/index.html" : requestPath;
  const filePath = path.normalize(path.join(config.clientDir, relative));

  // 防止路径穿越：解析后的路径必须仍位于 clientDir 内。
  if (!path.resolve(filePath).startsWith(path.resolve(config.clientDir) + path.sep)) {
    return c.json({ error: "not_found" }, 404);
  }

  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    const data = fs.readFileSync(filePath);
    return new Response(data, {
      headers: { "content-type": contentTypeFor(filePath) },
    });
  }

  // SSR 兜底：非真实文件（即前端路由）→ 懒加载 server build 并渲染。
  let handler: RequestHandler | null;
  try {
    handler = await getSsrHandler();
  } catch (error) {
    console.error("[webui] SSR 构建产物加载失败：", error);
    return new Response(
      "SSR 构建产物加载失败，请检查 build/server 产物或重新运行 `pnpm build`。",
      { status: 500, headers: { "content-type": "text/plain; charset=utf-8" } },
    );
  }
  if (!handler) {
    return new Response(
      "页面尚未构建，请先运行 `pnpm build`（react-router build）后再访问。",
      { status: 503, headers: { "content-type": "text/plain; charset=utf-8" } },
    );
  }

  try {
    return await handler(c.req.raw);
  } catch (error) {
    console.error("[webui] SSR 渲染失败：", error);
    return new Response("服务端渲染失败，请查看服务端日志。", {
      status: 500,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }
};
