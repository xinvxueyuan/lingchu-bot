import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { fetchOverview, isOnebotDisconnected, type OverviewData } from "@/lib/overview-api";

type OverviewContextValue = {
  /** 概览聚合数据，未就绪为 null。 */
  data: OverviewData | null;
  /** 首次未就绪或刷新中。 */
  pending: boolean;
  /** 后端已运行但未连接 OneBot11（判定结果供全局 Alert 与卡片空态共享）。 */
  onebotDisconnected: boolean;
  /** 手动重新拉取概览（守卫 Alert「刷新」按钮）。 */
  reload: () => void;
};

const OverviewContext = createContext<OverviewContextValue | null>(null);

/**
 * 概览数据全局提供者：布局层挂载一次，所有登录页面共享同一份数据与刷新入口，
 * 避免各页面重复请求 /api/overview；OneBot 未连接状态也由此统一驱动全局 Alert。
 */
export function OverviewProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    // fetchOverview 单请求后端聚合端点；失败由错误态承载（卡片显示「加载失败」）。
    void fetchOverview().then(
      (result) => {
        if (cancelled) return;
        setData(result);
        setLoading(false);
      },
      () => {
        if (cancelled) return;
        setData({ errors: { global: "request_failed" } });
        setLoading(false);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  const value = useMemo<OverviewContextValue>(
    () => ({
      data,
      pending: data === null || loading,
      onebotDisconnected: isOnebotDisconnected(data),
      reload,
    }),
    [data, loading, reload],
  );

  return <OverviewContext.Provider value={value}>{children}</OverviewContext.Provider>;
}

/** 消费概览数据；必须在 OverviewProvider 内使用。 */
export function useOverview(): OverviewContextValue {
  const ctx = useContext(OverviewContext);
  if (!ctx) throw new Error("useOverview must be used within <OverviewProvider>");
  return ctx;
}
