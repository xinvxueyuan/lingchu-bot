/**
 * 会话状态（Cookie 会话，浏览器侧）。
 *
 * 登录态由 HttpOnly Cookie 承载，前端看不到也不该看到凭证本身，
 * 唯一的真相来源是 `auth/me` 过程。这里只提供路径与判定工具，
 * 不做任何本地 token 缓存。
 */

import { LOGIN_URL, client } from "@/orpc/client";

/** 应用 base 路径（无尾斜杠），供路由与链接复用。 */
export function getBasePath(): string {
  return LOGIN_URL.replace(/\/login$/, "");
}

/** 跳转登录页（整页跳转，确保 Vue/React 状态与 Cookie 状态一同重置）。 */
export function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  if (window.location.pathname === LOGIN_URL) return;
  window.location.assign(LOGIN_URL);
}

/**
 * 探测当前会话是否有效。
 *
 * `auth/me` 在 401 时返回未授权错误，其余错误（网络 / 上游）视为服务不可用，
 * 同样按未登录处理——登录页是唯一能恢复状态的入口。
 *
 * @returns 会话有效返回 true。
 */
export async function isAuthenticated(): Promise<boolean> {
  try {
    await client.auth.me();
    return true;
  } catch {
    return false;
  }
}
