import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col justify-center px-6 py-16">
      <p className="mb-3 text-sm font-medium text-fd-muted-foreground">NoneBot2 project docs</p>
      <h1 className="mb-5 text-4xl font-semibold tracking-normal text-fd-foreground">
        Lingchu Bot
      </h1>
      <p className="mb-8 max-w-2xl text-base leading-7 text-fd-muted-foreground">
        基于 NoneBot2 的应用侧管理机器人项目文档，覆盖当前用户指南、开发流程、国际化、
        测试与 GitNexus 工作流。
      </p>
      <div className="flex flex-wrap gap-3">
        <Link
          href="/docs"
          className="rounded-md bg-fd-primary px-4 py-2 text-sm font-medium text-fd-primary-foreground"
        >
          简体中文
        </Link>
        <Link
          href="/en/docs"
          className="rounded-md border px-4 py-2 text-sm font-medium text-fd-foreground"
        >
          English
        </Link>
      </div>
    </div>
  );
}
