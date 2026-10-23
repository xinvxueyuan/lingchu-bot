import { useState } from "react";
import { useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { client } from "@/orpc/client";

/**
 * 退出登录：触发按钮 + 确认 Modal。
 * 点击按钮仅打开确认框，「确认」后才调用 auth.logout 清除会话 Cookie 并跳转登录页，防止误触。
 */
export function LogoutButton() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const onConfirm = async () => {
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      await client.auth.logout();
    } catch {
      // 登出失败不阻断退出：会话 Cookie 可能已失效，界面仍应回到登录页。
    } finally {
      setOpen(false);
      setLoggingOut(false);
      navigate("/login", { replace: true });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="destructive"
            onClick={() => setOpen(true)}
            aria-label={t("auth.logout")}
          >
            <LogOut />
            {t("auth.logout")}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{t("auth.logout")}</TooltipContent>
      </Tooltip>
      <DialogContent showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>{t("auth.logoutConfirm.title")}</DialogTitle>
          <DialogDescription>{t("auth.logoutConfirm.desc")}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={loggingOut}
          >
            {t("auth.cancel")}
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={() => void onConfirm()}
            disabled={loggingOut}
          >
            <LogOut />
            {loggingOut ? t("auth.submitting") : t("auth.logout")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
