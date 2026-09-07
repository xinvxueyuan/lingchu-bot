import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { OnebotStatus } from "@/lib/overview-api";

/** OneBot 在线状态徽标：online 且非 good=false 视为在线；悬浮显示状态文案。 */
export function OnlineStatusBadge({ status }: { status: OnebotStatus | undefined }) {
  const { t } = useTranslation();
  const online = status !== undefined && status.online === true && status.good !== false;
  const label = t(online ? "overview.online" : "overview.offline");
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge variant={online ? "default" : "secondary"}>{label}</Badge>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}
