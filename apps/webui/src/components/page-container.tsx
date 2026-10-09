import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/** 内容区页面容器：统一页边距的 <main> 包装。 */
export function PageContainer({ className, children }: { className?: string; children: ReactNode }) {
  return <main className={cn("p-6", className)}>{children}</main>;
}
