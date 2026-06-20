import { Provider } from '@/components/provider';
import { AnnouncementBanner } from '@/components/announcement-banner';
import type { Metadata } from 'next';
import { appName, gitConfig } from '@/lib/shared';
import './global.css';

const baseUrl = `https://${gitConfig.user}.github.io/${gitConfig.repo}`;

export const metadata: Metadata = {
  alternates: {
    types: {
      'application/rss+xml': [
        { title: `${appName} Docs`, url: `${baseUrl}/rss.xml` },
        { title: `${appName} 文档`, url: `${baseUrl}/zh/rss.xml` },
      ],
    },
  },
};

export default async function Layout({ children }: LayoutProps<'/'>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="flex flex-col min-h-screen" suppressHydrationWarning>
        <AnnouncementBanner />
        <Provider>{children}</Provider>
      </body>
    </html>
  );
}
