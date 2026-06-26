import { Provider } from '@/components/provider';
import { AnnouncementBanner } from '@/components/announcement-banner';
import type { Metadata } from 'next';
import { getSiteAlternatesTypes, getSiteMetadata } from '@/lib/site-metadata';
import './global.css';

const site = getSiteMetadata();

export const metadata: Metadata = {
  ...site,
  alternates: {
    ...site.alternates,
    types: getSiteAlternatesTypes(),
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
