/**
 * 概览页数据源：单请求 WebUI 后端聚合端点 `/api/overview`。
 * 后端内部并发聚合 nonebot 原子 API（login-info / status / version-info / groups /
 * friends / 灵初 status），一次性返回。前端不再直连 nonebot，也不接触内部细节。
 */

import { expireSession, getApiBase, getStoredToken } from "@/lib/api";

/** OneBot get_login_info 返回值。 */
export type LoginInfo = {
  user_id: number;
  nickname: string;
};

/** OneBot get_status 返回值（仅取前端展示字段）。 */
export type OnebotStatus = {
  online?: boolean;
  good?: boolean;
};

/** OneBot get_version_info 返回值（仅取前端展示字段）。 */
export type VersionInfo = {
  app_name?: string;
  app_version?: string;
};

/** OneBot get_group_list 数组元素。 */
export type GroupInfo = {
  group_id: number;
  group_name?: string;
};

/** OneBot get_friend_list 数组元素。 */
export type FriendInfo = {
  user_id: number;
  nickname?: string;
};

/** 灵初自身状态（/status，非 result 包装）。 */
export type LingchuStatus = {
  status: string;
  plugin: string;
  version: string;
};

/** 概览聚合数据（对应用户端可展示的字段）。 */
export type OverviewData = {
  loginInfo?: LoginInfo;
  status?: OnebotStatus;
  versionInfo?: VersionInfo;
  groups?: GroupInfo[];
  friends?: FriendInfo[];
  lingchuVersion?: string;
  /** 失败区块集合：键存在（值为错误码）即表示该区块请求失败，供前端逐区块独立错误态。 */
  errors: Partial<Record<string, string>>;
};

/** 拉取聚合概览（单请求）。401 等非 2xx 直接抛错。 */
export async function fetchOverview(): Promise<OverviewData> {
  const token = getStoredToken();
  const res = await fetch(`${getApiBase()}/overview`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (res.status === 401) {
    // 会话已失效（如进程重启后遗留 UBT）：清除并跳转登录页，等待重新登录恢复数据。
    expireSession();
  }
  if (!res.ok) throw new Error(`request_failed: ${res.status}`);
  return (await res.json()) as OverviewData;
}

/**
 * OneBot 未连接判定：任一 OneBot 依赖区块被标记为 onebot_disconnected
 * （五块共用上游 get_bot()，未连接时同进同退，故可代表整体状态）。
 */
export function isOnebotDisconnected(data: OverviewData | null): boolean {
  if (!data) return false;
  return (
    data.errors.loginInfo === "onebot_disconnected" ||
    data.errors.status === "onebot_disconnected" ||
    data.errors.versionInfo === "onebot_disconnected" ||
    data.errors.groups === "onebot_disconnected" ||
    data.errors.friends === "onebot_disconnected"
  );
}
