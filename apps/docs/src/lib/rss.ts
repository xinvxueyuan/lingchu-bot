import { Feed } from 'feed';
import { source } from '@/lib/source';
import { appName, gitConfig } from '@/lib/shared';

const baseUrl = `https://${gitConfig.user}.github.io/${gitConfig.repo}`;

export function getRSS(locale: string = 'zh') {
    const isZh = locale === 'zh';
    const feed = new Feed({
        title: isZh ? `${appName} 文档` : `${appName} Docs`,
        id: `${baseUrl}${isZh ? '/docs' : '/en/docs'}`,
        link: `${baseUrl}${isZh ? '/docs' : '/en/docs'}`,
        language: locale,
        favicon: `${baseUrl}/icon.png`,
        copyright: `All rights reserved ${new Date().getFullYear()}, ${appName}`,
    });

    for (const page of source.getPages(locale)) {
        feed.addItem({
            id: page.url,
            title: page.data.title,
            description: page.data.description,
            link: `${baseUrl}${page.url}`,
            date: page.data.lastModified ? new Date(page.data.lastModified) : new Date(),
        });
    }

    return feed.rss2();
}
