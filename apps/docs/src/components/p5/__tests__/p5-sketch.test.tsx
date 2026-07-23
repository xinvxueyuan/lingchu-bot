import { describe, it, expect, vi, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import type { ReactNode } from "react";

// Mock ClientOnly to bypass useSyncExternalStore mount detection. In jsdom the
// server snapshot of useSyncExternalStore is used for the initial render, which
// would hide the children — short-circuiting it keeps tests focused on the
// p5 lifecycle (the boundary itself is covered separately by the spec).
vi.mock("@/components/p5/client-only", () => ({
  ClientOnly: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

const mockRemove = vi.fn();
const mockP5Instance = { remove: mockRemove };

// P5SketchImpl uses `import("p5").then(({ default: P5 }) => new P5(...))`.
// The mock must therefore expose a `default` export that is constructable.
// Vitest 4 requires the implementation to use `function`/`class` syntax so it
// can be invoked with `new`; an arrow fn would throw "not a constructor".
// Returning an object from a constructor overrides `this`, so the returned
// instance is the shared `mockP5Instance` whose `remove` we can assert on.
const MockP5Constructor = vi.fn(function MockP5() {
  return mockP5Instance;
});

vi.mock("p5", () => ({
  default: MockP5Constructor,
}));

describe("P5Sketch", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("mounts a p5 instance with the sketch callback and container", async () => {
    const { P5Sketch } = await import("@/components/p5/p5-sketch");
    const sketch = vi.fn();
    const { container } = render(<P5Sketch sketch={sketch} />);

    // The dynamic `import("p5")` resolves on the next microtask; wait for the
    // constructor to be invoked with the sketch fn and the rendered container.
    await vi.waitFor(() => {
      expect(MockP5Constructor).toHaveBeenCalledTimes(1);
    });

    expect(MockP5Constructor).toHaveBeenCalledWith(sketch, expect.any(HTMLElement));
    // The constructor receives the rendered container div, not the test root.
    expect(container.firstChild).toBeInstanceOf(HTMLElement);
  });

  it("calls p.remove() on unmount", async () => {
    const { P5Sketch } = await import("@/components/p5/p5-sketch");
    const sketch = vi.fn();
    const { unmount } = render(<P5Sketch sketch={sketch} />);

    await vi.waitFor(() => {
      expect(MockP5Constructor).toHaveBeenCalledTimes(1);
    });

    unmount();

    expect(mockRemove).toHaveBeenCalledTimes(1);
  });
});
