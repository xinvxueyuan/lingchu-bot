import { useEffect, useState, type FormEvent } from "react";
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
import { client } from "@/orpc/client";

/** 登录失败分类：口令错误与网络/服务端错误给不同文案。 */
type LoginFailure = "invalid_password" | "network";

/** 从 oRPC 错误中判定是否为「口令错误」（401）。 */
function isInvalidPassword(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    (error as { status?: unknown }).status === 401
  );
}

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<LoginFailure | null>(null);
  // 已登录用户访问 /login 直接回首页：会话状态只能异步探测（HttpOnly Cookie）。
  const [alreadyAuthenticated, setAlreadyAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    void client.auth
      .me()
      .then(
        () => !cancelled && setAlreadyAuthenticated(true),
        () => !cancelled && setAlreadyAuthenticated(false),
      );
    return () => {
      cancelled = true;
    };
  }, []);

  if (alreadyAuthenticated === true) return <Navigate to="/" replace />;

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      // 服务端下发 HttpOnly Cookie，前端不持有任何 token。
      await client.auth.login({ password });
      navigate("/", { replace: true });
    } catch (err) {
      setError(isInvalidPassword(err) ? "invalid_password" : "network");
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
                {error === "invalid_password"
                  ? t("auth.error.invalidPassword")
                  : t("auth.error.network")}
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
