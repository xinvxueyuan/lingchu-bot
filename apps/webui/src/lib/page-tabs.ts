/**
 * 内容区子标签页菜单栏配置。
 *
 * 菜单栏是通用组件：由布局在内容区顶部渲染、对所有内容页默认生效；
 * 可通过全局 `enabled` 一键关闭，也可对单个栏目设置 `disabled` 独立关闭。
 * 标签集合与左侧栏目绑定（path 精确匹配），非全站导航。
 */
export type PageTab = {
  /** 标签唯一标识，作为 ?tab= 查询参数值 */
  id: string;
  /** i18n 文案 key */
  labelKey: string;
};

export type PageTabGroup = {
  /** 绑定的左侧栏目路由路径（精确匹配当前 pathname） */
  path: string;
  /** 该栏目下的子标签页（横向排列的纯文本菜单项） */
  tabs: PageTab[];
  /** 默认标签 id：无 ?tab= 参数或参数未命中时激活该标签 */
  defaultTab?: string;
  /** 独立控制：本栏目是否禁用菜单栏，默认 false */
  disabled?: boolean;
};

export type PageTabsConfig = {
  /** 全局开关：false 时所有内容页均不渲染菜单栏 */
  enabled: boolean;
  groups: PageTabGroup[];
};

export const pageTabsConfig: PageTabsConfig = {
  enabled: true,
  groups: [
    {
      path: "/",
      tabs: [
        { id: "overview", labelKey: "tabs.home.overview" },
        { id: "account-detail", labelKey: "tabs.home.accountDetail" },
      ],
      defaultTab: "overview",
    },
    {
      path: "/debug/http",
      tabs: [
        { id: "request", labelKey: "tabs.http.request" },
        { id: "response", labelKey: "tabs.http.response" },
        { id: "history", labelKey: "tabs.http.history" },
      ],
    },
    {
      path: "/debug/ws",
      tabs: [
        { id: "connection", labelKey: "tabs.ws.connection" },
        { id: "messages", labelKey: "tabs.ws.messages" },
      ],
    },
  ],
};

/** 命中当前路径的栏目配置；全局关闭或该栏目独立禁用时返回 null。 */
export function findPageTabGroup(pathname: string): PageTabGroup | null {
  if (!pageTabsConfig.enabled) return null;
  const group = pageTabsConfig.groups.find((g) => g.path === pathname);
  if (!group || group.disabled) return null;
  return group;
}
