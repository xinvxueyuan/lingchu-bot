import Link from 'next/link';

export default function EnglishHomePage() {
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col justify-center px-6 py-16">
      <p className="mb-3 text-sm font-medium text-fd-muted-foreground">NoneBot2 project docs</p>
      <h1 className="mb-5 text-4xl font-semibold tracking-normal text-fd-foreground">
        Lingchu Bot Documentation
      </h1>
      <p className="mb-8 max-w-2xl text-base leading-7 text-fd-muted-foreground">
        Documentation for the Lingchu Bot application-side management bot, including user guides,
        development workflow, internationalization, testing, and GitNexus practices.
      </p>
      <div className="flex flex-wrap gap-3">
        <Link
          href="/en/docs"
          className="rounded-md bg-fd-primary px-4 py-2 text-sm font-medium text-fd-primary-foreground"
        >
          Open docs
        </Link>
        <Link
          href="/docs"
          className="rounded-md border px-4 py-2 text-sm font-medium text-fd-foreground"
        >
          简体中文
        </Link>
      </div>
    </div>
  );
}
