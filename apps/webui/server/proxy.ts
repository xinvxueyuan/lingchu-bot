import type { Context } from "hono";
import { config } from "./config.js";
import { extractBearer, verifyToken } from "./auth.js";
import { getResolvedNonebotBaseUrl } from "./discover.js";
import { getCachedWebuiPassword } from "./password-cache.js";

/**
 * 转发中间件（交换组件）：
 * 对 `/api/*` 中不属于 `/api/auth/*` 的请求，先校验 UBT（否则 401），
 * 剥离客户端 Authorization，按前缀转发到
 * `NONEBOT_BASE_URL + LINGCHU_WEBUI_BASE_PATH + 余下路径`，
 * 并附加请求头 `X-Lingchu-Webui-Password`（登录时缓存的内存密钥，浏览器不可见）。
 *
 * 转发方法、请求头（除 Authorization）、查询与 body；将上游响应体 /
 * 状态码 / Content-Type 回传。
 */
export async function proxyHandler(c: Context): Promise<Response> {
  // 1. 校验 UBT
  const token = extractBearer(c.req.header("Authorization"));
  const claims = token ? await verifyToken(token) : null;
  if (!claims) {
    return c.json({ error: "unauthorized" }, 401);
  }

  // 2. 计算上游路径：去掉客户端 `/api` 前缀，拼接 base path 与查询串。
  const rest = c.req.path.replace(/^\/api/, "") || "/";
  const query = new URL(c.req.url).search;
  const upstream = `${getResolvedNonebotBaseUrl()}${config.webuiBasePath}${rest}${query}`;

  // 3. 构造上游请求头：复制除 Authorization 外的所有请求头。
  const headers = new Headers();
  for (const [key, value] of c.req.raw.headers) {
    if (key.toLowerCase() === "authorization") continue;
    headers.set(key, value);
  }
  // 附加仅服务端可见的密码头（登录时缓存的唯一密钥；未登录时为空 → 上游 401）。
  headers.set("X-Lingchu-Webui-Password", getCachedWebuiPassword() ?? "");

  // 4. 转发 body（GET/HEAD 不带 body）。
  const method = c.req.method;
  const init: RequestInit = { method, headers };
  if (method !== "GET" && method !== "HEAD") {
    const body = await c.req.arrayBuffer();
    if (body.byteLength > 0) init.body = body;
  }

  // 5. 请求上游并回传响应。
  let upstreamRes: Response;
  try {
    upstreamRes = await fetch(upstream, init);
  } catch {
    return c.json({ error: "bad_gateway" }, 502);
  }

  const responseHeaders = new Headers();
  const contentType = upstreamRes.headers.get("content-type");
  if (contentType) responseHeaders.set("content-type", contentType);

  return new Response(upstreamRes.body, {
    status: upstreamRes.status,
    headers: responseHeaders,
  });
}
