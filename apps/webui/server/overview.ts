/**
 * `/api/overview` 聚合端点：WebUI 后端一次性聚合多个原子 API，
 * 组装为前端直接消费的概览结构，不向前端暴露 nonebot 上游细节。
 *
 * 内部并发：
 * - nonebot 各只读端点（login-info / status / version-info / groups / friends / 灵初 status）
 * 各区块失败互不影响，统一收敛到 `errors` 供前端逐块渲染。
 */

import type { Context, Handler } from "hono";
import { extractBearer, verifyToken } from "./auth.js";
import { config } from "./config.js";
import { getResolvedNonebotBaseUrl } from "./discover.js";
import { getCachedWebuiPassword } from "./password-cache.js";

/** nonebot get_login_info 返回值。 */
type LoginInfo = { user_id: number; nickname: string };

/** OneBot get_status 返回值（仅取前端展示字段）。 */
type OnebotStatus = { online?: boolean; good?: boolean };

/** OneBot get_version_info 返回值（仅取前端展示字段）。 */
type VersionInfo = { app_name?: string; app_version?: string };

/** OneBot get_group_list 数组元素。 */
type GroupInfo = { group_id: number; group_name?: string };

/** OneBot get_friend_list 数组元素。 */
type FriendInfo = { user_id: number; nickname?: string };

/** 灵初自身状态（/status，非 result 包装）。 */
type LingchuStatus = { status: string; plugin: string; version: string };

/** 概览聚合返回结构（前端 OverviewData 的映射）。 */
export type OverviewPayload = {
  loginInfo?: LoginInfo;
  status?: OnebotStatus;
  versionInfo?: VersionInfo;
  groups?: GroupInfo[];
  friends?: FriendInfo[];
  lingchuVersion?: string;
  /** 失败区块集合：键存在（值为错误码/信息）即表示该区块失败。 */
  errors: Partial<Record<string, string>>;
};

/**
 * 服务端直连 nonebot 原子端点（不走代理中间件）：
 * 附加仅服务端可见的密码头，并按需解析 `{"result": ...}` 包装。
 */
async function fetchUpstream<T>(restPath: string, unwrap = true): Promise<T> {
  const url = `${getResolvedNonebotBaseUrl()}${config.webuiBasePath}${restPath}`;
  const res = await fetch(url, {
    headers: { "x-lingchu-webui-password": getCachedWebuiPassword() ?? "" },
    signal: AbortSignal.timeout(8000),
  });
  if (!res.ok) {
    // 仅 502 读取上游响应体：区分「OneBot 未连接」与一般上游错误（非 JSON/失败则走通用路径）。
    let detail: string | undefined;
    if (res.status === 502) {
      try {
        detail = ((await res.json()) as { detail?: string }).detail;
      } catch {
        // 忽略非 JSON 响应体
      }
    }
    if (detail === "onebot_disconnected") throw new Error("upstream_onebot_disconnected");
    throw new Error(`upstream_http_${res.status}`);
  }
  const payload = (await res.json()) as { result?: T };
  return unwrap ? (payload.result as T) : (payload as unknown as T);
}

/** 将单区块失败收敛为错误码：OneBot 未连接 → onebot_disconnected，其余 → unavailable。 */
function blockError(reason: unknown): string {
  return reason instanceof Error && reason.message === "upstream_onebot_disconnected"
    ? "onebot_disconnected"
    : "unavailable";
}

export const overviewHandler: Handler = async (c: Context) => {
  // 与代理中间件一致的 UBT 鉴权要求。
  const token = extractBearer(c.req.header("Authorization"));
  if (!token || !(await verifyToken(token))) {
    return c.json({ error: "unauthorized" }, 401);
  }

  // 孤儿会话检查：UBT 可校验但本进程尚无登录口令缓存
  // （dev / 生产进程重启后浏览器仍持有 12h 内签发的无状态 UBT）。
  // 此时无法携带密码访问 nonebot，判定会话已失效，引导前端重新登录。
  if (getCachedWebuiPassword() === null) {
    return c.json({ error: "session_expired" }, 401);
  }

  const data: OverviewPayload = { errors: {} };

  // 原子请求并发：互不阻塞，失败互不影响。
  const [login, status, version, groups, friends, lingchu] =
    await Promise.allSettled([
      fetchUpstream<LoginInfo>("/onebot/login-info"),
      fetchUpstream<OnebotStatus>("/onebot/status"),
      fetchUpstream<VersionInfo>("/onebot/version-info"),
      fetchUpstream<GroupInfo[]>("/onebot/groups"),
      fetchUpstream<FriendInfo[]>("/onebot/friends"),
      fetchUpstream<LingchuStatus>("/status", false),
    ]);

  if (login.status === "fulfilled") data.loginInfo = login.value;
  else data.errors.loginInfo = blockError(login.reason);

  if (status.status === "fulfilled") data.status = status.value;
  else data.errors.status = blockError(status.reason);

  if (version.status === "fulfilled") data.versionInfo = version.value;
  else data.errors.versionInfo = blockError(version.reason);

  if (groups.status === "fulfilled") data.groups = groups.value;
  else data.errors.groups = blockError(groups.reason);

  if (friends.status === "fulfilled") data.friends = friends.value;
  else data.errors.friends = blockError(friends.reason);

  if (lingchu.status === "fulfilled") data.lingchuVersion = lingchu.value.version;
  else data.errors.lingchuVersion = "unavailable";

  return c.json(data);
};
