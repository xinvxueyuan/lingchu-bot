import { Bot } from "lucide-react";
import Link from "next/link";
import { buttonVariants } from "fumadocs-ui/components/ui/button";
import { cn } from "@/lib/cn";

export function LLMBadge({ locale }: { locale?: string }) {
  const label =
    locale === "zh"
      ? "可通过 llms.txt 获取 AI 友好文档"
      : "AI-friendly docs available via llms.txt";

  return (
    <Link
      href="/llms.txt"
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
      title={label}
      className={cn(
        buttonVariants({
          variant: "ghost",
          size: "icon-xs",
        }),
        "text-fd-muted-foreground hover:text-fd-foreground",
      )}
    >
      <Bot className="size-3.5" />
    </Link>
  );
}
