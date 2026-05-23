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
  tocNoHeadings: '本页无标题',
  tocInline: '目录',
  chooseLanguage: '选择语言',
  editOnGithub: '在 GitHub 编辑',
  lastUpdate: '最后更新',
  nextPage: '下一页',
  previousPage: '上一页',
  chooseTheme: '选择主题',
  themeToggle: '切换主题',
  themeLight: '浅色',
  themeDark: '深色',
  themeSystem: '跟随系统',
  codeBlockCopy: '复制代码',
  codeBlockCopied: '已复制',
  accordionCopyAnchor: '复制锚点链接',
  headingCopyAnchor: '复制锚点链接',
  bannerClose: '关闭',
  menuToggle: '切换菜单',
  pageActionsCopyMarkdown: '复制 Markdown',
  pageActionsOpen: '打开方式',
  pageActionsOpenGitHub: '在 GitHub 查看',
  pageActionsViewMarkdown: '查看 Markdown',
  pageActionsOpenScira: '在 Scira AI 中打开',
  pageActionsOpenChatGPT: '在 ChatGPT 中打开',
  pageActionsOpenClaude: '在 Claude 中打开',
  pageActionsOpenCursor: '在 Cursor 中打开',
  pageActionsOpenInLLMPrompt: '在 {url} 中打开',
  sidebarOpen: '打开侧边栏',
  sidebarCollapse: '收起侧边栏',
  notFoundTitle: '页面未找到',
  notFoundDescription: '你访问的页面不存在',
  notFoundLink: '返回首页',
  typeTableProp: '属性',
  typeTableType: '类型',
  typeTableDefault: '默认值',
  typeTableParameters: '参数',
  typeTableReturns: '返回值',
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
