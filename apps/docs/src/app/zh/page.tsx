import Link from 'next/link';
import type { Metadata } from 'next';
import { appName } from '@/lib/shared';

export const metadata: Metadata = {
  title: `${appName} 文档`,
  description:
    '基于 NoneBot2 的应用侧管理机器人项目文档，覆盖用户指南、开发流程、国际化、测试与 GitNexus 工作流。',
};

export default function ChineseHomePage() {
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col justify-center px-6 py-16">
      <p className="mb-3 text-sm font-medium text-fd-muted-foreground">NoneBot2 项目文档</p>
      <h1 className="mb-5 text-4xl font-semibold tracking-normal text-fd-foreground">
        Lingchu Bot 文档
      </h1>
      <p className="mb-8 max-w-2xl text-base leading-7 text-fd-muted-foreground">
        基于 NoneBot2 的应用侧管理机器人项目文档，覆盖当前用户指南、开发流程、国际化、
        测试与 GitNexus 工作流。
      </p>
      <div className="flex flex-wrap gap-3">
        <Link
          href="/zh/docs"
          className="rounded-md bg-fd-primary px-4 py-2 text-sm font-medium text-fd-primary-foreground"
        >
          简体中文
        </Link>
        <Link
          href="/docs"
          className="rounded-md border px-4 py-2 text-sm font-medium text-fd-foreground"
        >
          English
        </Link>
      </div>
    </div>
  );
}
