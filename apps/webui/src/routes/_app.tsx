import { useEffect, useState, type ComponentType } from "react";
import { Navigate, NavLink, Outlet, useLocation } from "react-router";
import { useTranslation } from "react-i18next";
import {
  Cable,
  ChevronDown,
  ChevronRight,
  FileCog,
  FlaskConical,
  Home,
  Moon,
  PanelLeft,
  PanelLeftClose,
  Settings,
  SlidersHorizontal,
  Sun,
  Wrench,
} from "lucide-react";

import { OnebotDisconnectedBanner } from "@/components/onebot-disconnected-banner";
import { OverviewProvider, useOverview } from "@/components/overview-provider";
import { PageTabs } from "@/components/page-tabs";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { getStoredToken } from "@/lib/api";
import { cn } from "@/lib/utils";

type NavItem = {
  to: string;
  labelKey: string;
  icon: ComponentType<{ className?: string }>;
};

type NavGroup = {
  labelKey: string;
  icon: ComponentType<{ className?: string }>;
  children: NavItem[];
};

type NavEntry = NavItem | NavGroup;

/**
 * 计算导航链接的 className（纯字符串，SSR 安全）。
 *
 * 不能给 NavLink 传函数式 className：该函数经 Radix TooltipTrigger asChild
 * （内部为 Slot，做 props merge）传递后，SSR 阶段会被序列化为函数源码字符串
 * 而非最终类名，导致样式丢失并触发 hydration mismatch。
 * 故改为基于当前 pathname 自行计算 active 态。
 */
function navLinkClass(
  to: string,
  pathname: string,
  collapsed: boolean,
  nested = false,
): string {
  const active =
    to === "/" ? pathname === "/" : pathname === to || pathname.startsWith(`${to}/`);
  return cn(
    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
    collapsed ? "justify-center" : nested ? "pl-8" : "",
    active
      ? "bg-accent text-accent-foreground"
      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
  );
}

// 导航项由该数组派生；新增页面只需在此追加一项。
// `icon` 采用 lucide 图标（Simple Icons 仅含品牌标识，无通用 UI 图标），
// lucide-react 已在依赖中，未引入新 UI 库。
const navEntries: NavEntry[] = [
  { to: "/", labelKey: "nav.home", icon: Home },
  {
    labelKey: "nav.config",
    icon: Settings,
    children: [
      { to: "/config/basic", labelKey: "nav.configBasic", icon: SlidersHorizontal },
      { to: "/config/advanced", labelKey: "nav.configAdvanced", icon: FileCog },
    ],
  },
  {
    labelKey: "nav.devTools",
    icon: Wrench,
    children: [
      { to: "/debug/http", labelKey: "nav.debugHttp", icon: FlaskConical },
      { to: "/debug/ws", labelKey: "nav.debugWs", icon: Cable },
    ],
  },
];

/**
 * 全局 OneBot 未连接 Alert：挂在布局层（Provider 内），任意路由下可见。
 * 数据来自全局 OverviewProvider，与各页面卡片共享同一份判定与刷新入口。
 */
function GlobalOnebotAlert() {
  const { onebotDisconnected, pending, reload } = useOverview();
  if (!onebotDisconnected || pending) return null;
  return (
    <div className="p-4 pb-0">
      <OnebotDisconnectedBanner onRefresh={reload} />
    </div>
  );
}

export default function AppLayout() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  // 折叠态：SSR 端恒为展开（false），挂载后再读本地偏好（"lingchu-sidebar-collapsed"；
  // "1" 折叠 / "0" 展开），避免服务端/客户端首帧不一致触发 hydration mismatch。
  const [collapsed, setCollapsed] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("light");
  // 分组展开态：以分组 labelKey 为键，仅内存态。默认展开“系统配置”、收起“开发调试”。
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({
    "nav.config": true,
    "nav.devTools": false,
  });

  // 登录守卫：未持有 UBT（WebUI Bearer Token）时跳转登录页。
  // 构建期预渲染时 window 不存在，直接放行，由客户端首帧接管。
  if (typeof window !== "undefined" && !getStoredToken()) {
    return <Navigate to="/login" replace />;
  }

  useEffect(() => {
    // 挂载后读取折叠偏好（SSR/客户端首帧保持一致后再应用）。
    if (localStorage.getItem("lingchu-sidebar-collapsed") === "1") {
      setCollapsed(true);
    }
    const mql = window.matchMedia("(max-width: 767px)");
    const sync = () => {
      // 窄屏（<768px）自动折叠；宽屏不强制，保留手动控制。
      if (mql.matches) setCollapsed(true);
    };
    sync();
    mql.addEventListener("change", sync);
    return () => mql.removeEventListener("change", sync);
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem("lingchu-theme");
    const initial: "light" | "dark" = stored === "dark" ? "dark" : "light";
    setTheme(initial);
    document.documentElement.classList.toggle("dark", initial === "dark");
  }, []);

  const toggleTheme = () => {
    setTheme((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      document.documentElement.classList.toggle("dark", next === "dark");
      localStorage.setItem("lingchu-theme", next);
      return next;
    });
  };

  return (
    <OverviewProvider>
      <div className="flex min-h-screen bg-background text-foreground">
        <aside
        className={cn(
          "flex shrink-0 flex-col border-r border-border bg-background transition-[width] duration-200",
          collapsed ? "w-16" : "w-60"
        )}
      >
        <div className="flex h-14 items-center border-b border-border px-3">
          {collapsed ? null : (
            <span className="truncate text-sm font-semibold">{t("app.title")}</span>
          )}
        </div>

        <nav className="flex-1 space-y-1 p-2">
          {navEntries.map((entry) => {
            if ("to" in entry) {
              const Icon = entry.icon;
              return (
                <div key={entry.to}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <NavLink
                        to={entry.to}
                        end
                        aria-label={t(entry.labelKey)}
                        className={navLinkClass(entry.to, pathname, collapsed)}
                      >
                        <Icon className="size-5 shrink-0" />
                        {collapsed ? null : <span>{t(entry.labelKey)}</span>}
                      </NavLink>
                    </TooltipTrigger>
                    <TooltipContent>{t(entry.labelKey)}</TooltipContent>
                  </Tooltip>
                </div>
              );
            }
            const Icon = entry.icon;
            return (
              <div key={entry.labelKey}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={() =>
                        setOpenGroups((prev) => ({
                          ...prev,
                          [entry.labelKey]: !prev[entry.labelKey],
                        }))
                      }
                      aria-label={t(entry.labelKey)}
                      className={cn(
                        "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                        collapsed ? "justify-center" : "",
                        "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                      )}
                    >
                      <Icon className="size-5 shrink-0" />
                      {collapsed ? null : (
                        <>
                          <span className="flex-1 text-left">{t(entry.labelKey)}</span>
                          {openGroups[entry.labelKey] ? (
                            <ChevronDown className="size-4 shrink-0" />
                          ) : (
                            <ChevronRight className="size-4 shrink-0" />
                          )}
                        </>
                      )}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>{t(entry.labelKey)}</TooltipContent>
                </Tooltip>
                {openGroups[entry.labelKey]
                  ? entry.children.map((child) => {
                      const ChildIcon = child.icon;
                      return (
                        <div key={child.to}>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <NavLink
                                to={child.to}
                                aria-label={t(child.labelKey)}
                                className={navLinkClass(child.to, pathname, collapsed, true)}
                              >
                                <ChildIcon className="size-5 shrink-0" />
                                {collapsed ? null : <span>{t(child.labelKey)}</span>}
                              </NavLink>
                            </TooltipTrigger>
                            <TooltipContent>{t(child.labelKey)}</TooltipContent>
                          </Tooltip>
                        </div>
                      );
                    })
                  : null}
              </div>
            );
          })}
        </nav>

        <div className="space-y-1 border-t border-border p-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={toggleTheme}
                aria-label={t("nav.theme")}
                className={cn("w-full", collapsed ? "justify-center px-0" : "justify-start")}
              >
                {theme === "dark" ? <Sun className="size-5" /> : <Moon className="size-5" />}
                {collapsed ? null : <span>{t("nav.theme")}</span>}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{t("nav.theme")}</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() =>
                  setCollapsed((v) => {
                    const next = !v;
                    localStorage.setItem("lingchu-sidebar-collapsed", next ? "1" : "0");
                    return next;
                  })
                }
                aria-label={t(collapsed ? "nav.expand" : "nav.collapse")}
                className={cn("w-full", collapsed ? "justify-center px-0" : "justify-start")}
              >
                {collapsed ? (
                  <PanelLeft className="size-5" />
                ) : (
                  <PanelLeftClose className="size-5" />
                )}
                {collapsed ? null : <span>{t(collapsed ? "nav.expand" : "nav.collapse")}</span>}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{t(collapsed ? "nav.expand" : "nav.collapse")}</TooltipContent>
          </Tooltip>
        </div>
      </aside>

      <div className="flex-1 overflow-y-auto">
        <PageTabs />
        <GlobalOnebotAlert />
        <Outlet />
      </div>
      </div>
    </OverviewProvider>
  );
}
