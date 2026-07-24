"use client";
import { usePathname } from "next/navigation";
import { Banner } from "fumadocs-ui/components/banner";

const messages = {
  en: "Lingchu Bot documentation is now live — check it out!",
  zh: "Lingchu Bot 文档现已上线 — 快来看看吧！",
};

export function AnnouncementBanner() {
  const pathname = usePathname();
  const locale = pathname.startsWith("/zh") ? "zh" : "en";

  return (
    <Banner
      variant="rainbow"
      className="vt-banner"
    >
      {messages[locale]}
    </Banner>
  );
}
