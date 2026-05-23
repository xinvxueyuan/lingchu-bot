'use client';
import SearchDialog from '@/components/search';
import { RootProvider } from 'fumadocs-ui/provider/next';
import { usePathname } from 'next/navigation';
import { type ReactNode } from 'react';

const zhTranslations = {
  search: '搜索',
  searchNoResult: '没有找到结果',
  searchOpen: '打开搜索',
  searchClose: '关闭搜索',
  toc: '本页目录',
  chooseLanguage: '选择语言',
  editOnGithub: '在 GitHub 编辑',
};

export function Provider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const locale = pathname.startsWith('/en') ? 'en' : 'zh';

  return (
    <RootProvider
      i18n={{
        locale,
        locales: [
          { name: '简体中文', locale: 'zh' },
          { name: 'English', locale: 'en' },
        ],
        onLocaleChange: (value) => {
          window.location.href = value === 'en' ? '/en/docs' : '/docs';
        },
        translations: locale === 'zh' ? zhTranslations : undefined,
      }}
      search={{ SearchDialog }}
    >
      {children}
    </RootProvider>
  );
}
