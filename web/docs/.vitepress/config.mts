import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "灵初bot",
  description: "QQ社管bot",
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: '主页', link: '/' },
      { text: '文档',
        items: [
          { text: '项目说明', link: '/introduction' },
          { text: '快速上手', link: '/main' },
          { text: '功能介绍', link: '/features' }
        ]}
    ],

    sidebar: [
      {
        text: '基础',
        items: [
          { text: '项目说明', link: '/introduction' },
          { text: '快速上手', link: '/main' },
          { text: '功能介绍', link: '/features' }
        ]
      },
      {
        text: '使用说明',
        items: [
          { text: '配置说明', link: '/config' },
          { text: '插件说明', link: '/plugin' },
          { text: '指令说明', link: '/command' }
        ]
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/xinvxueyuan/lingchu-nonebot-bot' }
    ]
  }
})
