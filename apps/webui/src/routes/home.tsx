import { useTranslation } from "react-i18next";
import type { Route } from "./+types/home";

import { AsyncCard } from "@/components/async-card";
import { Avatar } from "@/components/avatar";
import { CollapsibleSection } from "@/components/collapsible-section";
import { InfoRow } from "@/components/info-row";
import { OnlineStatusBadge } from "@/components/online-status-badge";
import { useOverview } from "@/components/overview-provider";
import { PageContainer } from "@/components/page-container";
import { useActivePageTab } from "@/components/page-tabs";
import { PlaceholderCard } from "@/components/placeholder-card";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { appPageMeta } from "@/lib/meta";
import webuiPkg from "../../package.json";

export function meta({}: Route.MetaArgs) {
  return appPageMeta();
}

/** OneBot 未连接时卡片级专属空态（替代笼统「加载失败」）。 */
function DisconnectedCardError() {
  const { t } = useTranslation();
  return (
    <p role="alert" className="text-sm text-destructive">
      {t("overview.onebotDisconnected.cardText")}
    </p>
  );
}

export default function Home() {
  const { t } = useTranslation();
  // 读取当前激活的子标签页（?tab= 查询参数），无命中时退回栏目名。
  const { activeTab } = useActivePageTab();
  // 概览聚合数据、加载态与 OneBot 未连接判定由布局层 OverviewProvider 全局提供，
  // 与全局 Alert 共享同一份数据与刷新入口。
  const { data, pending } = useOverview();

  // 「账号详情」标签页：账号聚合卡（群/好友数量与列表）迁移至此展示。
  if (activeTab?.id === "account-detail") {
    const detailCode = data?.errors.global || data?.errors.groups || data?.errors.friends;
    return (
      <PageContainer>
        <AsyncCard
          title={t("overview.summaryTitle")}
          pending={pending}
          error={detailCode === "onebot_disconnected" ? <DisconnectedCardError /> : Boolean(detailCode)}
        >
          {/* 标签页式分栏：群列表与好友列表上下分栏（非并列，防止排版异常），各自可展开/收起 */}
          <div className="grid gap-4">
            {/* 群列表区块 */}
            <CollapsibleSection title={t("overview.groupList")} count={data?.groups?.length ?? 0}>
              {data?.groups?.length ? (
                <ul className="grid gap-1.5 px-2">
                  {data.groups.map((group) => {
                    const groupName = group.group_name ?? String(group.group_id);
                    return (
                      <li key={group.group_id} className="flex items-center gap-3">
                        <Avatar
                          src={`http://p.qlogo.cn/gh/${group.group_id}/${group.group_id}/100/`}
                          alt={groupName}
                        />
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="min-w-0 flex-1 truncate text-sm">
                              {group.group_name || group.group_id}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>{groupName}</TooltipContent>
                        </Tooltip>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Badge variant="secondary" className="font-mono">
                              {group.group_id}
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent>{groupName}</TooltipContent>
                        </Tooltip>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="px-2 text-sm text-muted-foreground">{t("overview.noGroups")}</p>
              )}
            </CollapsibleSection>

            {/* 好友列表区块 */}
            <CollapsibleSection title={t("overview.friendList")} count={data?.friends?.length ?? 0}>
              {data?.friends?.length ? (
                <ul className="grid gap-1.5 px-2">
                  {data.friends.map((friend) => {
                    const friendName = friend.nickname ?? String(friend.user_id);
                    return (
                      <li key={friend.user_id} className="flex items-center gap-3">
                        <Avatar
                          src={`https://q1.qlogo.cn/g?b=qq&nk=${friend.user_id}&s=100`}
                          alt={friendName}
                        />
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="min-w-0 flex-1 truncate text-sm">
                              {friend.nickname || friend.user_id}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>{friendName}</TooltipContent>
                        </Tooltip>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Badge variant="secondary" className="font-mono">
                              {friend.user_id}
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent>{friendName}</TooltipContent>
                        </Tooltip>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="px-2 text-sm text-muted-foreground">{t("overview.noFriends")}</p>
              )}
            </CollapsibleSection>
          </div>
        </AsyncCard>
      </PageContainer>
    );
  }

  // 未命中概览相关标签页时保持原占位 Card。
  if (activeTab?.id !== "overview") {
    return (
      <PageContainer>
        <PlaceholderCard title={t(activeTab?.labelKey ?? "nav.home")} />
      </PageContainer>
    );
  }

  const accountCode = data?.errors.loginInfo || data?.errors.status;
  const versionCode = data?.errors.lingchuVersion;
  return (
    <PageContainer className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <AsyncCard
        title={t("overview.accountTitle")}
        pending={pending}
        error={accountCode === "onebot_disconnected" ? <DisconnectedCardError /> : Boolean(accountCode)}
      >
        {data?.loginInfo ? (
          <div className="flex items-center gap-4">
            <Avatar
              src={`https://q1.qlogo.cn/g?b=qq&nk=${data.loginInfo.user_id}&s=640`}
              alt={data.loginInfo.nickname}
              size="size-16"
            />
            <div className="grid flex-1 gap-2">
              <InfoRow label={t("overview.nickname")}>{data.loginInfo.nickname}</InfoRow>
              <InfoRow label={t("overview.qq")}>{data.loginInfo.user_id}</InfoRow>
              <InfoRow label={t("overview.onlineStatus")}>
                <OnlineStatusBadge status={data.status} />
              </InfoRow>
            </div>
          </div>
        ) : null}
      </AsyncCard>

      <AsyncCard
        title={t("overview.versionTitle")}
        pending={pending}
        error={Boolean(versionCode)}
      >
        <div className="grid gap-2">
          <InfoRow label={t("overview.onebotApp")}>
            {data?.versionInfo
              ? [data.versionInfo.app_name, data.versionInfo.app_version].filter(Boolean).join(" ") || "-"
              : "-"}
          </InfoRow>
          <InfoRow label={t("overview.lingchuVersion")}>{data?.lingchuVersion ?? "-"}</InfoRow>
          <InfoRow label={t("overview.webuiVersion")}>{webuiPkg.version}</InfoRow>
        </div>
      </AsyncCard>
    </PageContainer>
  );
}
