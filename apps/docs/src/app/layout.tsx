import { Provider } from '@/components/provider';
import { Banner } from 'fumadocs-ui/components/banner';
import type { Metadata } from 'next';
import { appName, gitConfig } from '@/lib/shared';
import './global.css';

const baseUrl = `https://${gitConfig.user}.github.io/${gitConfig.repo}`;

export const metadata: Metadata = {
  alternates: {
    types: {
      'application/rss+xml': [
        { title: `${appName} 文档`, url: `${baseUrl}/rss.xml` },
        { title: `${appName} Docs`, url: `${baseUrl}/en/rss.xml` },
      ],
    },
  },
};

export default async function Layout({ children }: LayoutProps<'/'>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className="flex flex-col min-h-screen" suppressHydrationWarning>
        <Banner variant="rainbow">
          🎉 Lingchu Bot 文档已上线，欢迎查阅！
        </Banner>
        <Provider>{children}</Provider>
      </body>
    </html>
  );
}
