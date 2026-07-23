import Link from "next/link";
import { HeroSketchLoader } from "@/components/p5/hero-sketch-loader";
import { gitConfig } from "@/lib/shared";
import { getHomeMetadata } from "@/lib/site-metadata";

export const metadata = getHomeMetadata("zh");

const githubUrl = `https://github.com/${gitConfig.user}/${gitConfig.repo}`;

const features = [
  ["权限感知命令", "菜单与处理器使用同一套 command key，只展示操作者能执行的动作。"],
  ["OneBot V11 优先", "QQ 群操作围绕当前启用的 OneBot V11 路径展开，不隐藏适配器边界。"],
  ["运行期控制", "静默模式和开关机门控可以暂停高噪声回复，同时保留恢复命令。"],
] as const;

const docLinks = [
  ["接入", "配置当前 QQ 适配器与平台身份模型。", "/zh/docs/platforms/qq"],
  ["运营", "使用文档化群命令完成日常群管。", "/zh/docs/user-guide/commands"],
  [
    "扩展",
    "按开发者指南补齐测试、国际化与交付检查。",
    "/zh/docs/developer-guide/architecture/introduction",
  ],
] as const;

export default function ChineseHomePage() {
  return (
    <main className="flex max-w-[100vw] flex-1 flex-col overflow-x-hidden bg-fd-background text-fd-foreground">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 overflow-hidden opacity-60"
      >
        <HeroSketchLoader className="h-full w-full" />
      </div>
      <section className="mx-auto grid w-full max-w-72 gap-10 py-14 md:max-w-6xl md:grid-cols-[1fr_420px] md:px-8 md:py-20">
        <div className="min-w-0">
          <p className="mb-4 text-sm font-medium uppercase text-fd-muted-foreground">
            NoneBot2 群管理机器人
          </p>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-normal md:text-6xl">
            Lingchu Bot 文档
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-8 text-fd-muted-foreground md:text-lg">
            面向 QQ
            群运营的代码驱动机器人：群管命令、权限感知菜单、运行期开关，以及只描述当前事实的文档。
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/zh/docs"
              className="rounded-md bg-fd-primary px-5 py-3 text-center text-sm font-medium text-fd-primary-foreground"
            >
              打开文档
            </Link>
            <Link
              href="/"
              className="rounded-md border px-5 py-3 text-center text-sm font-medium"
            >
              English
            </Link>
            <Link
              href={githubUrl}
              className="rounded-md border px-5 py-3 text-center text-sm font-medium"
            >
              GitHub
            </Link>
          </div>
        </div>

        <div className="min-w-0 rounded-md border bg-fd-card p-5 shadow-xl shadow-fd-foreground/5">
          <div className="mb-5 flex items-center justify-between gap-4 border-b pb-4">
            <div>
              <h2 className="text-base font-semibold">运营概览</h2>
              <p className="text-sm text-fd-muted-foreground">QQ / OneBot V11 / 权限门控</p>
            </div>
            <span className="rounded-md bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-600 dark:text-emerald-300">
              active
            </span>
          </div>
          <div className="grid gap-3">
            {features.map(([title, description]) => (
              <article
                key={title}
                className="min-w-0 rounded-md border bg-fd-background p-4"
              >
                <h3 className="text-sm font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-fd-muted-foreground">{description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t bg-fd-muted/20">
        <div className="mx-auto grid w-full max-w-72 gap-4 py-10 md:max-w-6xl md:grid-cols-3 md:px-8">
          {docLinks.map(([title, description, href]) => (
            <Link
              key={title}
              href={href}
              className="rounded-md border bg-fd-card p-5 hover:bg-fd-muted/40"
            >
              <h2 className="text-base font-semibold">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-fd-muted-foreground">{description}</p>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
