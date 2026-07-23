"use client";
import { flushSync } from "react-dom";
import Link, { type LinkProps } from "next/link";
import { useRouter, usePathname } from "next/navigation";
import type { ComponentProps, FC, MouseEventHandler } from "react";

const SCHEME_RE = /^[a-z][a-z0-9+.-]*:/i;

/**
 * Resolve a pathname's locale using the same convention as
 * `src/components/provider.tsx` (`pathname.startsWith("/zh") ? "zh" : "en"`).
 */
function getLocale(pathname: string): "zh" | "en" {
  return pathname.startsWith("/zh") ? "zh" : "en";
}

/**
 * Returns `true` when navigating from `currentPathname` to `href` changes the
 * site locale (`/zh` prefix vs default `en`). External URLs and invalid hrefs
 * return `false` defensively.
 */
export function detectLocaleSwitch(currentPathname: string, href: string): boolean {
  if (!href) return false;
  // External URLs (with a scheme like `https:`, `mailto:`) don't change this
  // site's locale.
  if (SCHEME_RE.test(href)) return false;
  let hrefPath: string;
  try {
    hrefPath = new URL(href, "http://d").pathname;
  } catch {
    return false;
  }
  return getLocale(currentPathname) !== getLocale(hrefPath);
}

interface ViewTransitionNavigateOptions {
  types?: string[];
}

interface ViewTransitionRouter {
  push: (url: string, opts?: ViewTransitionNavigateOptions) => void;
  replace: (url: string, opts?: ViewTransitionNavigateOptions) => void;
}

/**
 * Wraps `next/navigation`'s `useRouter` so `push`/`replace` run inside a
 * `document.startViewTransition`. When the View Transitions API is unavailable
 * (SSR or unsupported browsers), navigation falls back to the plain router
 * call without throwing.
 */
export function useViewTransitionRouter(): ViewTransitionRouter {
  const router = useRouter();

  const navigate = (
    url: string,
    method: "push" | "replace",
    opts?: ViewTransitionNavigateOptions,
  ): void => {
    const run = (): void => {
      if (method === "push") router.push(url);
      else router.replace(url);
    };

    if (typeof document === "undefined" || typeof document.startViewTransition !== "function") {
      run();
      return;
    }

    // Static-export pages are prefetched, so `flushSync` captures the new route
    // state synchronously inside the transition's update callback.
    const update = (): void => flushSync(run);
    const types = opts?.types;

    if (types && types.length > 0) {
      try {
        // View Transitions Level 2 options form. The TS DOM lib already
        // declares the `StartViewTransitionOptions` overload, so no cast is
        // required here.
        document.startViewTransition({ update, types });
        return;
      } catch {
        // Browser supports the callback form but not the options form: fall
        // back below to the callback form without `types`.
      }
    }

    document.startViewTransition(update);
  };

  return {
    push: (url, opts) => navigate(url, "push", opts),
    replace: (url, opts) => navigate(url, "replace", opts),
  };
}

type TransitionLinkProps = ComponentProps<"a"> & { prefetch?: boolean };

/**
 * Drop-in replacement for `next/link` that wraps same-origin left-click
 * navigations in a View Transition. Falls back to `next/link`'s native
 * behavior when the View Transitions API is unsupported or when the click is a
 * modified/new-tab/hash-only navigation. Satisfies Fumadocs' `Framework['Link']`
 * contract so it can be supplied via `RootProvider components={{ Link }}`.
 */
export const TransitionLink: FC<TransitionLinkProps> = ({ onClick, href, ...rest }) => {
  const pathname = usePathname();
  const { push } = useViewTransitionRouter();

  const handleClick: MouseEventHandler<HTMLAnchorElement> = (e) => {
    // Compose: consumer's onClick first, then our interception (only if it
    // didn't already preventDefault).
    if (onClick) onClick(e);
    if (e.defaultPrevented) return;
    if (typeof document === "undefined" || typeof document.startViewTransition !== "function") {
      return;
    }
    if (e.button !== 0) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    if (rest.target === "_blank") return;
    if (rest.download) return;
    if (typeof href !== "string") return;

    let url: URL;
    try {
      url = new URL(href, location.href);
    } catch {
      return;
    }
    if (url.origin !== location.origin) return;
    // Allow default behavior for in-page hash anchors on the same path.
    if (url.pathname === pathname && url.hash) return;

    e.preventDefault();
    const resolvedPathname = url.pathname + url.search;
    const isLocaleSwitch = detectLocaleSwitch(pathname, resolvedPathname);
    push(resolvedPathname, isLocaleSwitch ? { types: ["locale-switch"] } : undefined);
  };

  // Fumadocs framework always supplies `href` as a string at runtime; the
  // typeof check is purely defensive. Render a plain `<a>` in the
  // (impossible-in-practice) undefined case so `next/link`'s required-href
  // prop type is satisfied without an `as` cast.
  if (typeof href !== "string") {
    return (
      <a
        href={href}
        onClick={handleClick}
        {...rest}
      />
    );
  }

  // `next/link`'s `LinkProps` declares its event handlers (onMouseEnter,
  // onTouchStart, onClick) and `prefetch` without `| undefined`, which is
  // incompatible with React's `AnchorHTMLAttributes` under
  // `exactOptionalPropertyTypes`. Cast the forwarded anchor props to
  // next/link's expected shape — runtime is unchanged because React treats
  // undefined props as omitted.
  return (
    <Link
      href={href}
      onClick={handleClick}
      {...(rest as Omit<LinkProps, "href">)}
    />
  );
};
