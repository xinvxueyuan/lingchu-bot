import {
  DocsBody,
  DocsDescription,
  DocsPage,
  DocsTitle,
  MarkdownCopyButton,
  ViewOptionsPopover,
  PageLastUpdate,
} from "fumadocs-ui/layouts/docs/page";
import { notFound } from "next/navigation";
import { createRelativeLink } from "fumadocs-ui/mdx";
import { getMDXComponents } from "@/components/mdx";
import { getPageImage, getPageMarkdownUrl, source } from "@/lib/source";
import { gitConfig } from "@/lib/shared";
import { LLMBadge } from "@/components/llm-badge";
import { getDocsPageMetadata } from "@/lib/site-metadata";

export default async function Page(props: PageProps<"/docs/[[...slug]]">) {
  const params = await props.params;
  const page = source.getPage(params.slug, "en");
  if (!page) notFound();

  const MDX = page.data.body;
  const markdownUrl = getPageMarkdownUrl(page).url;

  return (
    <DocsPage
      toc={page.data.toc}
      full={page.data.full}
    >
      <DocsTitle>{page.data.title}</DocsTitle>
      <DocsDescription className="mb-0">{page.data.description}</DocsDescription>
      <div className="flex flex-row gap-2 items-center border-b pb-6">
        <LLMBadge locale="en" />
        <MarkdownCopyButton markdownUrl={markdownUrl} />
        <ViewOptionsPopover
          markdownUrl={markdownUrl}
          githubUrl={`https://github.com/${gitConfig.user}/${gitConfig.repo}/blob/${gitConfig.branch}/apps/docs/content/docs/${page.path}`}
        />
      </div>
      <DocsBody>
        <MDX
          components={getMDXComponents({
            a: createRelativeLink(source, page),
          })}
        />
      </DocsBody>
      {page.data.lastModified && <PageLastUpdate date={page.data.lastModified} />}
    </DocsPage>
  );
}

export async function generateStaticParams() {
  return source.getPages("en").map((page) => ({
    slug: page.slugs,
  }));
}

export async function generateMetadata(props: PageProps<"/docs/[[...slug]]">) {
  const params = await props.params;
  const page = source.getPage(params.slug, "en");
  if (!page) notFound();

  // Look up the zh equivalent for cross-locale `alternates.languages`.
  const zhPage = source.getPage(params.slug, "zh");
  const alternateUrl = zhPage ? zhPage.url : undefined;

  return getDocsPageMetadata(page, getPageImage(page).url, alternateUrl);
}
