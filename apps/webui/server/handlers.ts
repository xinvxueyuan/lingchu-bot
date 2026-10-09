import type { Context, Handler } from "hono";
import { extractBearer, revokeToken, signToken, verifyToken } from "./auth.js";
import { config } from "./config.js";
import { getResolvedNonebotBaseUrl } from "./discover.js";
import { setCachedWebuiPassword } from "./password-cache.js";
import { getQQAvatarUrl } from "./qq.js";

/** 校验前端 UBT（与代理中间件一致的鉴权要求）。 */
async function requireUBT(c: Context): Promise<boolean> {
  const token = extractBearer(c.req.header("Authorization"));
  const claims = token ? await verifyToken(token) : null;
  return claims !== null;
}

const QQ_ID_RE = /^\d{4,15}$/;

interface LoginBody {
  password?: unknown;
}

/** POST /api/auth/login —— 单用户系统：用户名锁定 root，密码委托 nonebot 校验端点对比 .env 唯一密钥。 */
export const loginHandler: Handler = async (c: Context) => {
  const body = await c.req.json<LoginBody>().catch(() => ({}) as LoginBody);
  const password = typeof body.password === "string" ? body.password : "";

  // 不再本地协商：转交 nonebot 暴露的校验端点（对比 .env 中 LINGCHU_WEBUI_PASSWORD）。
  const verifyUrl = `${getResolvedNonebotBaseUrl()}${config.webuiBasePath}/verify-password`;
  let upstreamRes: Response;
  try {
    upstreamRes = await fetch(verifyUrl, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ password }),
      signal: AbortSignal.timeout(5000),
    });
  } catch {
    return c.json({ error: "upstream_unreachable" }, 502);
  }
  if (!upstreamRes.ok) {
    if (upstreamRes.status === 401 || upstreamRes.status === 403) {
      return c.json({ error: "invalid_password" }, 401);
    }
    return c.json({ error: "upstream_error" }, 502);
  }

  // 校验通过：内存缓存唯一密钥（供代理转发附加密码头），随后签发 UBT。
  setCachedWebuiPassword(password);
  const token = await signToken();
  return c.json({ token });
};

/** POST /api/auth/logout */
export const logoutHandler: Handler = async (c: Context) => {
  const token = extractBearer(c.req.header("Authorization"));
  if (token) {
    const claims = await verifyToken(token);
    if (claims?.jti) revokeToken(claims.jti);
  }
  return c.json({ ok: true });
};

/** GET /api/auth/me */
export const meHandler: Handler = async (c: Context) => {
  const token = extractBearer(c.req.header("Authorization"));
  const claims = token ? await verifyToken(token) : null;
  if (!claims) {
    return c.json({ error: "unauthorized" }, 401);
  }
  return c.json({ sub: claims.sub, exp: claims.exp });
};

/** GET /api/qq/avatar/:qq?size=100 —— 代理 QQ 公共头像（CDN，无需登录）。 */
export const qqAvatarHandler: Handler = async (c: Context) => {
  if (!(await requireUBT(c))) return c.json({ error: "unauthorized" }, 401);
  const qq = c.req.param("qq") ?? "";
  if (!QQ_ID_RE.test(qq)) return c.json({ error: "invalid_qq" }, 400);
  const spec = Number(c.req.query("size") ?? 100);
  const upstream = getQQAvatarUrl(qq, Number.isFinite(spec) ? spec : 100);
  let upstreamRes: Response;
  try {
    upstreamRes = await fetch(upstream, { signal: AbortSignal.timeout(8000) });
  } catch {
    return c.json({ error: "upstream_error" }, 502);
  }
  if (!upstreamRes.ok) return c.json({ error: "upstream_error" }, 502);
  return new Response(upstreamRes.body, {
    status: 200,
    headers: {
      "content-type": upstreamRes.headers.get("content-type") ?? "image/jpeg",
      "cache-control": "public, max-age=86400",
    },
  });
};
