import { source } from "@/lib/source";
import { DocsLayout } from "fumadocs-ui/layouts/docs";
import { baseOptions } from "@/lib/layout.shared";

export default async function Layout({ children }: LayoutProps<"/zh/docs">) {
  return (
    <DocsLayout tree={source.getPageTree("zh")} {...await baseOptions("zh")}>
      {children}
    </DocsLayout>
  );
}
