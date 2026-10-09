import { useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/**
 * 可展开/收起的区块：按钮头部（标题 + 可选计数徽章 + 箭头）+ children。
 * 内部维护开合状态，默认展开；`defaultOpen` 可指定初始状态。
 */
export function CollapsibleSection({
  title,
  count,
  defaultOpen = true,
  children,
}: {
  title: string;
  count?: number;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="grid gap-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 rounded-md px-2 py-1.5 text-left hover:bg-accent"
        aria-expanded={open}
      >
        <span className="flex min-w-0 items-center gap-2">
          <span className="text-sm font-medium">{title}</span>
          {count !== undefined ? (
            <Badge variant="secondary" className="font-mono">
              {count}
            </Badge>
          ) : null}
        </span>
        <ChevronDown
          className={cn(
            "size-4 shrink-0 text-muted-foreground transition-transform",
            !open && "-rotate-90",
          )}
        />
      </button>
      {open ? children : null}
    </div>
  );
}
