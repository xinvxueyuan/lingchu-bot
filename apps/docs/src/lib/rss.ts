import { Feed } from "feed";
import { getPageImage, source } from "@/lib/source";
import { appName } from "@/lib/shared";
import { getSiteUrlString } from "@/lib/site-metadata";

export async function getRSS(locale: string = "en"): Promise<string> {
  const isEn = locale === "en";
  const baseUrl = getSiteUrlString();
  const author = {
    name: `${appName} Docs`,
    link: baseUrl,
  };
  const feed = new Feed({
    title: isEn ? `${appName} Docs` : `${appName} 文档`,
    id: `${baseUrl}${isEn ? "/docs" : "/zh/docs"}`,
    link: `${baseUrl}${isEn ? "/docs" : "/zh/docs"}`,
    language: locale,
    favicon: `${baseUrl}/favicon.ico`,
    copyright: `All rights reserved ${new Date().getFullYear()}, ${appName}`,
    feedLinks: {
      rss: `${baseUrl}${isEn ? "/rss.xml" : "/zh/rss.xml"}`,
    },
    author,
  });

  for (const page of source.getPages(locale)) {
    const pageDate = page.data.lastModified
      ? new Date(page.data.lastModified)
      : new Date();
    const item: Parameters<typeof feed.addItem>[0] = {
      id: `${baseUrl}${page.url}`,
      title: page.data.title,
      description: page.data.description ?? "",
      link: `${baseUrl}${page.url}`,
      date: pageDate,
      published: pageDate,
      author: [author],
    };
    // Include the generated page OG image so feed readers show a
    // thumbnail for each item. Reuse the canonical path builder from
    // `@/lib/source` so RSS and the page `<head>` stay in sync.
    if (isEn) {
      item.image = `${baseUrl}${getPageImage(page).url}`;
    }
    feed.addItem(item);
  }

  return feed.rss2();
}
