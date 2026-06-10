import { Feed } from 'feed';
import { source } from '@/lib/source';
import { appName, gitConfig } from '@/lib/shared';

const baseUrl = `https://${gitConfig.user}.github.io/${gitConfig.repo}`;

export async function getRSS(locale: string = 'en'): Promise<string> {
    const isEn = locale === 'en';
    const feed = new Feed({
        title: isEn ? `${appName} Docs` : `${appName} 文档`,
        id: `${baseUrl}${isEn ? '/docs' : '/zh/docs'}`,
        link: `${baseUrl}${isEn ? '/docs' : '/zh/docs'}`,
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
