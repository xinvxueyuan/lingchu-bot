import { source } from '@/lib/source';
import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import { baseOptions } from '@/lib/layout.shared';

export default async function Layout({ children }: LayoutProps<'/en/docs'>) {
  return (
    <DocsLayout tree={source.getPageTree('en')} {...(await baseOptions('en'))}>
      {children}
    </DocsLayout>
  );
}
