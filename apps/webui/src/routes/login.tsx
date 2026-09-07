import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authLogin, getStoredToken, setStoredToken, LoginError } from "@/lib/api";
import { appPageMeta } from "@/lib/meta";
import type { Route } from "./+types/login";

export function meta({}: Route.MetaArgs) {
  return appPageMeta();
}

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 单用户系统：用户名固定为 root，页面仅展示密码输入框。
  // 已登录用户访问 /login 直接回首页（未登录跳 /login 的守卫在 _app 布局）。
  if (typeof window !== "undefined" && getStoredToken()) {
    return <Navigate to="/" replace />;
  }

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const token = await authLogin(password);
      setStoredToken(token);
      navigate("/", { replace: true });
    } catch (err) {
      setError(
        err instanceof LoginError && err.status === 401
          ? t("auth.error.invalidPassword")
          : t("auth.error.network"),
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-background p-4 text-foreground">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>{t("auth.title")}</CardTitle>
          <CardDescription>{t("app.tagline")}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="flex flex-col gap-4">
            <div className="grid gap-2">
              <Label htmlFor="password">{t("auth.password")}</Label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                autoFocus
                placeholder={t("auth.passwordPlaceholder")}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error ? (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            ) : null}
            <Button type="submit" disabled={submitting}>
              {submitting ? t("auth.submitting") : t("auth.login")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
