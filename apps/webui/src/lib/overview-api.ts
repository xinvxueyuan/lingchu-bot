/**
 * 概览数据源：单次 `overview` 过程调用。
 *
 * 聚合在 Python 侧完成（同进程直连 OneBot），前端不接触上游细节；
 * 类型由契约推导，此处不再重复声明本地类型。
 */

import type { Overview } from "@/orpc/contract";
import { client } from "@/orpc/client";

/** 概览数据（契约推导类型）。 */
export type OverviewData = Overview;

/** 契约类型透出，供字段级类型推导（如 `Overview["status"]`）使用。 */
export type { Overview };

/** 拉取聚合概览；401 由客户端拦截器统一跳登录页。 */
export async function fetchOverview(): Promise<OverviewData> {
  return client.overview();
}

/**
 * OneBot 未连接判定：任一 OneBot 依赖区块被标记为 onebot_disconnected
 * （五块共用上游 `get_bot()`，未连接时同进同退，故可代表整体状态）。
 */
export function isOnebotDisconnected(data: OverviewData | null): boolean {
  if (!data) return false;
  const { errors } = data;
  return (
    errors["loginInfo"] === "onebot_disconnected" ||
    errors["status"] === "onebot_disconnected" ||
    errors["versionInfo"] === "onebot_disconnected" ||
    errors["groups"] === "onebot_disconnected" ||
    errors["friends"] === "onebot_disconnected"
  );
}
