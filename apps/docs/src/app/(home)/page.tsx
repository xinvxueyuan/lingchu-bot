import Link from 'next/link';
import { gitConfig } from '@/lib/shared';
import { getHomeMetadata } from '@/lib/site-metadata';

export const metadata = getHomeMetadata('en');

const githubUrl = `https://github.com/${gitConfig.user}/${gitConfig.repo}`;

const features = [
  ['Permission-aware commands', 'Menus and handlers use the same command keys, so operators only see actions they can run.'],
  ['OneBot V11 first', 'QQ group operations document the active OneBot V11 path without hiding adapter boundaries.'],
  ['Runtime controls', 'Silent mode and the handle gate let maintainers pause noisy replies without losing recovery commands.'],
] as const;

const docLinks = [
  ['Start', 'Configure the active QQ adapter and platform identity model.', '/docs/platforms/qq'],
  ['Operate', 'Use documented group commands for daily moderation.', '/docs/user-guide/commands'],
  ['Extend', 'Follow the developer guide for tests, i18n, and delivery checks.', '/docs/developer-guide/architecture/introduction'],
] as const;

export default function HomePage() {
  return (
    <main className="flex max-w-[100vw] flex-1 flex-col overflow-x-hidden bg-fd-background text-fd-foreground">
      <section className="mx-auto grid w-full max-w-72 gap-10 py-14 md:max-w-6xl md:grid-cols-[1fr_420px] md:px-8 md:py-20">
        <div className="min-w-0">
          <p className="mb-4 text-sm font-medium uppercase text-fd-muted-foreground">
            NoneBot2 group management bot
          </p>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-normal md:text-6xl">
            Lingchu Bot
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-8 text-fd-muted-foreground md:text-lg">
            A code-driven operations bot for QQ groups: moderation commands, permission-aware
            menus, runtime switches, and docs that describe what actually exists.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/docs"
              className="rounded-md bg-fd-primary px-5 py-3 text-center text-sm font-medium text-fd-primary-foreground"
            >
              Open docs
            </Link>
            <Link
              href="/zh"
              className="rounded-md border px-5 py-3 text-center text-sm font-medium"
            >
              简体中文
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
              <h2 className="text-base font-semibold">Operator snapshot</h2>
              <p className="text-sm text-fd-muted-foreground">QQ / OneBot V11 / permission gate</p>
            </div>
            <span className="rounded-md bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-600 dark:text-emerald-300">
              active
            </span>
          </div>
          <div className="grid gap-3">
            {features.map(([title, description]) => (
              <article key={title} className="min-w-0 rounded-md border bg-fd-background p-4">
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
            <Link key={title} href={href} className="rounded-md border bg-fd-card p-5 hover:bg-fd-muted/40">
              <h2 className="text-base font-semibold">{title}</h2>
              <p className="mt-2 text-sm leading-6 text-fd-muted-foreground">{description}</p>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
