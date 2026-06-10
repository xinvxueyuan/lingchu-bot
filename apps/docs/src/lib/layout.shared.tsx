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
  en: {
    docs: 'Docs',
  },
  zh: {
    docs: '文档',
  },
};

export async function baseOptions(locale = 'en'): Promise<BaseLayoutProps> {
  const text = locale === 'zh' ? labels.zh : labels.en;

  return {
    nav: {
      title: appName,
    },
    links: [
      {
        text: text.docs,
        url: locale === 'zh' ? '/zh/docs' : '/docs',
        active: 'nested-url',
      },
    ],
    githubUrl: `https://github.com/${gitConfig.user}/${gitConfig.repo}`,
  };
}
