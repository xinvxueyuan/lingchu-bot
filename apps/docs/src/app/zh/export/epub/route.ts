import { source } from "@/lib/source";
import { exportEpub } from "fumadocs-epub";
import { appName, gitConfig } from "@/lib/shared";

export const revalidate = false;

export async function GET(): Promise<Response> {
  const buffer = await exportEpub({
    source,
    title: `${appName} 文档`,
    author: gitConfig.user,
    description: `基于 NoneBot2 的应用侧管理机器人项目文档`,
    language: "zh",
    includePages: (page) => page.locale === "zh",
  });

  return new Response(new Uint8Array(buffer), {
    headers: {
      "Content-Type": "application/epub+zip",
      "Content-Disposition": `attachment; filename="${appName.toLowerCase()}-docs-zh.epub"`,
    },
  });
}
