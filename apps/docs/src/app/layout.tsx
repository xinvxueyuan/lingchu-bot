import { Provider } from '@/components/provider';
import { Banner } from 'fumadocs-ui/components/banner';
import './global.css';

export default function Layout({ children }: LayoutProps<'/'>) {
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
