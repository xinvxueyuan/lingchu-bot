import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { ComponentProps, MouseEventHandler } from "react";
import { render, screen, renderHook, fireEvent } from "@testing-library/react";

// --- Mocks (vi.fn defined BEFORE vi.mock; SUT import AFTER vi.mock) ---

const pushMock = vi.fn<(url: string) => void>();
const replaceMock = vi.fn<(url: string) => void>();
const prefetchMock = vi.fn();
const pathnameMock = vi.fn<() => string>();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    replace: replaceMock,
    prefetch: prefetchMock,
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  }),
  usePathname: () => pathnameMock(),
}));

// Mock next/link with a plain <a> so the SUT's click handler is the only
// interceptor. The real next/link calls preventDefault itself on same-origin
// left-clicks, which would mask the SUT's fallthrough behavior.
vi.mock("next/link", () => ({
  default: function MockLink({
    href,
    onClick,
    children,
    ...rest
  }: ComponentProps<"a"> & { href: string }) {
    return (
      <a href={href} onClick={onClick} {...rest}>
        {children}
      </a>
    );
  },
}));

// Make flushSync invoke its callback synchronously so the wrapped
// router.push/replace actually executes inside the test. Only `flushSync` is
// needed from this entry — @testing-library/react uses `react-dom/client`.
vi.mock("react-dom", () => ({
  flushSync: (fn: () => void) => fn(),
}));

import {
  TransitionLink,
  detectLocaleSwitch,
  useViewTransitionRouter,
} from "@/components/view-transition";

// --- document.startViewTransition mock (jsdom lacks this API) ---

interface StartViewTransitionArg {
  update?: () => void;
  types?: string[];
}

const startViewTransitionMock = vi.fn(
  (arg?: (() => void) | StartViewTransitionArg) => {
    if (typeof arg === "function") {
      arg();
    } else if (arg?.update) {
      arg.update();
    }
    return { finished: Promise.resolve() };
  },
);

function injectStartViewTransition(): void {
  Object.defineProperty(document, "startViewTransition", {
    value: startViewTransitionMock,
    writable: true,
    configurable: true,
  });
}

function removeStartViewTransition(): void {
  Object.defineProperty(document, "startViewTransition", {
    value: undefined,
    writable: true,
    configurable: true,
  });
}

// --- Shared setup ---

beforeEach(() => {
  pushMock.mockReset();
  replaceMock.mockReset();
  prefetchMock.mockReset();
  startViewTransitionMock.mockReset();
  pathnameMock.mockReturnValue("/");
  injectStartViewTransition();
});

afterEach(() => {
  removeStartViewTransition();
});

// --- detectLocaleSwitch (pure function) ---

describe("detectLocaleSwitch", () => {
  it("returns true for / → /zh", () => {
    expect(detectLocaleSwitch("/", "/zh")).toBe(true);
  });

  it("returns true for /docs → /zh/docs", () => {
    expect(detectLocaleSwitch("/docs", "/zh/docs")).toBe(true);
  });

  it("returns true for /zh → /", () => {
    expect(detectLocaleSwitch("/zh", "/")).toBe(true);
  });

  it("returns false for /zh/docs/a → /zh/docs/b (same locale)", () => {
    expect(detectLocaleSwitch("/zh/docs/a", "/zh/docs/b")).toBe(false);
  });

  it("returns false for /docs/a → /docs/b (same locale)", () => {
    expect(detectLocaleSwitch("/docs/a", "/docs/b")).toBe(false);
  });

  it("returns false for external URL with scheme", () => {
    expect(detectLocaleSwitch("/", "https://github.com/foo/bar")).toBe(false);
  });

  it("returns false for mailto URL", () => {
    expect(detectLocaleSwitch("/", "mailto:foo@bar.com")).toBe(false);
  });

  it("returns false for empty href", () => {
    expect(detectLocaleSwitch("/", "")).toBe(false);
  });
});

// --- useViewTransitionRouter ---

describe("useViewTransitionRouter", () => {
  it("degrades to plain router.push when startViewTransition is unavailable", () => {
    removeStartViewTransition();
    const { result } = renderHook(() => useViewTransitionRouter());
    result.current.push("/x");
    expect(pushMock).toHaveBeenCalledWith("/x");
    expect(startViewTransitionMock).not.toHaveBeenCalled();
  });

  it("wraps push in startViewTransition callback form when no types given", () => {
    const { result } = renderHook(() => useViewTransitionRouter());
    result.current.push("/x");
    expect(startViewTransitionMock).toHaveBeenCalledTimes(1);
    // Callback form: the argument is a function (not an options object).
    expect(startViewTransitionMock).toHaveBeenCalledWith(expect.any(Function));
    // flushSync ran the update callback → router.push was called.
    expect(pushMock).toHaveBeenCalledWith("/x");
  });

  it("passes types via options object form when types is non-empty", () => {
    const { result } = renderHook(() => useViewTransitionRouter());
    result.current.push("/zh", { types: ["locale-switch"] });
    expect(startViewTransitionMock).toHaveBeenCalledTimes(1);
    // Options object form (not callback): argument has `types`.
    expect(startViewTransitionMock).toHaveBeenCalledWith(
      expect.objectContaining({ types: ["locale-switch"] }),
    );
    // update callback was invoked → router.push called inside flushSync.
    expect(pushMock).toHaveBeenCalledWith("/zh");
  });

  it("routes replace through replaceMock (not pushMock)", () => {
    const { result } = renderHook(() => useViewTransitionRouter());
    result.current.replace("/y");
    expect(replaceMock).toHaveBeenCalledWith("/y");
    expect(pushMock).not.toHaveBeenCalled();
  });
});

// --- TransitionLink ---

describe("TransitionLink", () => {
  it("renders an anchor with passthrough href, className, and children", () => {
    render(
      <TransitionLink href="/docs" className="cls">
        label
      </TransitionLink>,
    );
    const anchor = screen.getByText("label").closest("a");
    expect(anchor).not.toBeNull();
    expect(anchor?.getAttribute("href")).toBe("/docs");
    expect(anchor?.className).toBe("cls");
  });

  it("intercepts same-origin left-click and kicks a view transition", () => {
    const onClick = vi.fn<MouseEventHandler<HTMLAnchorElement>>();
    render(
      <TransitionLink href="/docs" onClick={onClick}>
        link
      </TransitionLink>,
    );
    fireEvent.click(screen.getByText("link"));
    expect(startViewTransitionMock).toHaveBeenCalledTimes(1);
    // Consumer onClick composed before interception; SUT calls preventDefault
    // after, so the captured event reflects defaultPrevented === true once
    // the full handler returns.
    expect(onClick).toHaveBeenCalledTimes(1);
    const capturedCall = onClick.mock.calls[0];
    const event = capturedCall?.[0];
    expect(event?.defaultPrevented).toBe(true);
  });

  it("tags locale-switch transition type when target locale differs", () => {
    pathnameMock.mockReturnValue("/");
    render(<TransitionLink href="/zh">switch</TransitionLink>);
    fireEvent.click(screen.getByText("switch"));
    expect(startViewTransitionMock).toHaveBeenCalledWith(
      expect.objectContaining({ types: ["locale-switch"] }),
    );
  });

  it("falls through for modified click (metaKey)", () => {
    render(<TransitionLink href="/docs">mod</TransitionLink>);
    fireEvent.click(screen.getByText("mod"), { metaKey: true });
    expect(startViewTransitionMock).not.toHaveBeenCalled();
  });

  it("falls through for external URL (different origin)", () => {
    render(<TransitionLink href="https://github.com/foo">ext</TransitionLink>);
    fireEvent.click(screen.getByText("ext"));
    expect(startViewTransitionMock).not.toHaveBeenCalled();
  });

  it("falls through when startViewTransition is unsupported (native behavior preserved)", () => {
    removeStartViewTransition();
    const onClick = vi.fn<MouseEventHandler<HTMLAnchorElement>>();
    render(
      <TransitionLink href="/docs" onClick={onClick}>
        no-vt
      </TransitionLink>,
    );
    fireEvent.click(screen.getByText("no-vt"));
    // SUT returns early (typeof startViewTransition !== "function") without
    // calling preventDefault or push — the mock was never invoked.
    expect(startViewTransitionMock).not.toHaveBeenCalled();
  });
});

// --- TransitionLink sharedName (shared-element transitions) ---

describe("TransitionLink sharedName", () => {
  it("sets inline view-transition-name and uses shared-transition type when sharedName is provided", () => {
    pathnameMock.mockReturnValue("/");
    render(
      <TransitionLink href="/docs/platforms/qq" sharedName="hero-doc-card">
        Start
      </TransitionLink>,
    );
    const anchor = screen.getByText("Start").closest<HTMLAnchorElement>("a");
    expect(anchor).not.toBeNull();
    // Spy on the clicked anchor's style.setProperty so the inline-name assertion
    // is deterministic and unaffected by the queueMicrotask cleanup timing.
    if (!anchor) throw new Error("anchor not found");
    const setPropertySpy = vi.spyOn(anchor.style, "setProperty");

    fireEvent.click(screen.getByText("Start"));

    // Inline view-transition-name was set on e.currentTarget before the
    // transition started.
    expect(setPropertySpy).toHaveBeenCalledWith(
      "view-transition-name",
      "hero-doc-card",
    );
    // The shared-transition type was passed via the options object form,
    // bypassing the locale-switch detection branch.
    expect(startViewTransitionMock).toHaveBeenCalledWith(
      expect.objectContaining({ types: ["shared-transition"] }),
    );
    // Underlying next/navigation router.push received the resolved pathname.
    expect(pushMock).toHaveBeenCalledWith("/docs/platforms/qq");
    setPropertySpy.mockRestore();
  });

  it("does not set inline name or shared-transition type when sharedName is omitted", () => {
    pathnameMock.mockReturnValue("/");
    render(<TransitionLink href="/docs/platforms/qq">Start</TransitionLink>);
    const anchor = screen.getByText("Start").closest<HTMLAnchorElement>("a");
    expect(anchor).not.toBeNull();

    fireEvent.click(screen.getByText("Start"));

    // No inline view-transition-name was ever set.
    expect(anchor?.style.getPropertyValue("view-transition-name")).toBe("");
    // / → /docs/platforms/qq is NOT a locale switch, so push is called without
    // types → callback form (function arg), not the options object form.
    expect(startViewTransitionMock).toHaveBeenCalledWith(expect.any(Function));
    expect(startViewTransitionMock).not.toHaveBeenCalledWith(
      expect.objectContaining({ types: ["shared-transition"] }),
    );
    expect(pushMock).toHaveBeenCalledWith("/docs/platforms/qq");
  });

  it("degrades without setting inline name when startViewTransition is unavailable", () => {
    removeStartViewTransition();
    pathnameMock.mockReturnValue("/");
    render(
      <TransitionLink href="/docs/platforms/qq" sharedName="hero-doc-card">
        Start
      </TransitionLink>,
    );
    const anchor = screen.getByText("Start").closest<HTMLAnchorElement>("a");
    expect(anchor).not.toBeNull();

    fireEvent.click(screen.getByText("Start"));

    // The sharedName branch is never reached because the unsupported-API early
    // return in handleClick runs first, so no inline name is set.
    expect(anchor?.style.getPropertyValue("view-transition-name")).toBe("");
    // handleClick early-returns before push, so neither startViewTransition
    // nor the underlying router.push is invoked — native navigation falls
    // through (mirrors the existing unsupported-API degradation test).
    expect(startViewTransitionMock).not.toHaveBeenCalled();
    expect(pushMock).not.toHaveBeenCalled();
  });
});

// --- Provider onLocaleChange coverage (SubTask 5.4) ---
//
// `Provider`'s `onLocaleChange` (src/components/provider.tsx) is a thin wrapper:
//
//   const { push } = useViewTransitionRouter();
//   const onLocaleChange = useCallback(
//     (newLocale: string) => {
//       push(switchLocale(pathname, locale, newLocale), { types: ["locale-switch"] });
//     },
//     [pathname, locale, push],
//   );
//
// The "passes types via options object form when types is non-empty" test above
// exercises exactly this call shape — `push(url, { types: ["locale-switch"] })`
// — and asserts that `startViewTransition` receives the options object with
// `types: ["locale-switch"]` and that `router.push` is invoked with the target
// URL. This transitively covers `onLocaleChange`'s contract.
//
// Rendering the full `Provider` is deliberately avoided: it pulls in Fumadocs
// `RootProvider` (which mounts `SearchDialog`, i18n context, and framework
// internals), requiring heavy mocking of `fumadocs-ui/provider/next`,
// `fumadocs-ui/i18n`, `@/components/search`, and `@/lib/layout.shared` for
// negligible additional coverage beyond what the hook test already proves.
