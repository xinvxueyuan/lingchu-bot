import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';
import { appName, gitConfig } from './shared';

const labels = {
  zh: {
    docs: '文档',
    github: 'GitHub',
  },
  en: {
    docs: 'Docs',
    github: 'GitHub',
  },
};

export function baseOptions(locale = 'zh'): BaseLayoutProps {
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
      {
        text: text.github,
        url: `https://github.com/${gitConfig.user}/${gitConfig.repo}`,
        external: true,
      },
    ],
    githubUrl: `https://github.com/${gitConfig.user}/${gitConfig.repo}`,
  };
}
