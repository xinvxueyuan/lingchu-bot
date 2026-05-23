import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';
import { uiTranslations } from 'fumadocs-ui/i18n';
import { zhCN } from '@fumadocs/language/zh-cn';
import { i18n } from './i18n';
import { appName, gitConfig } from './shared';

export const translations = i18n
  .translations()
  .extend(uiTranslations())
  .preset('zh', zhCN());

const labels = {
  zh: {
    docs: '文档',
  },
  en: {
    docs: 'Docs',
  },
};

export async function baseOptions(locale = 'zh'): Promise<BaseLayoutProps> {
  const text = locale === 'en' ? labels.en : labels.zh;

  return {
    nav: {
      title: appName,
    },
    links: [
      {
        text: text.docs,
        url: locale === 'en' ? '/en/docs' : '/docs',
        active: 'nested-url',
      },
    ],
    githubUrl: `https://github.com/${gitConfig.user}/${gitConfig.repo}`,
  };
}
