import { useTranslation } from "react-i18next";
import { useLocation, useSearchParams } from "react-router";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { findPageTabGroup, type PageTab } from "@/lib/page-tabs";
import { cn } from "@/lib/utils";

/**
 * 读取当前路径命中的标签组与激活标签（?tab= 查询参数驱动）。
 * 供页面组件渲染当前标签对应内容使用；无命中或停用时返回 null。
 */
export function useActivePageTab() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const group = findPageTabGroup(location.pathname);
  const tabId = searchParams.get("tab");
  const activeTab =
    group?.tabs.find((tab) => tab.id === tabId) ??
    group?.tabs.find((tab) => tab.id === group?.defaultTab) ??
    group?.tabs[0];
  return { group, activeTab };
}

/**
 * 内容区子标签页菜单栏：横向排列的纯文本按钮，?tab= 查询参数切换。
 * 通用组件，由布局在内容区顶部渲染；与左侧栏目绑定，非全站导航。
 */
export function PageTabs() {
  const { t } = useTranslation();
  const { group, activeTab } = useActivePageTab();
  const [searchParams, setSearchParams] = useSearchParams();

  if (!group) return null;

  const selectTab = (tab: PageTab) => {
    const next = new URLSearchParams(searchParams);
    if (tab.id === group.defaultTab) {
      next.delete("tab");
    } else {
      next.set("tab", tab.id);
    }
    setSearchParams(next, { replace: true });
  };

  return (
    <div className="sticky top-0 z-10 flex items-center gap-1 border-b border-border bg-background/95 px-4 py-1.5 backdrop-blur">
      {group.tabs.map((tab) => (
        <Tooltip key={tab.id}>
          <TooltipTrigger asChild>
            <button
              type="button"
              onClick={() => selectTab(tab)}
              aria-current={activeTab?.id === tab.id ? "page" : undefined}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                activeTab?.id === tab.id
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              {t(tab.labelKey)}
            </button>
          </TooltipTrigger>
          <TooltipContent>{t(tab.labelKey)}</TooltipContent>
        </Tooltip>
      ))}
    </div>
  );
}
