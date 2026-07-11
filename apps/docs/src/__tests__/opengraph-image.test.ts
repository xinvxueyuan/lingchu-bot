import { describe, it, expect, vi } from "vitest";

// `next/og`'s `ImageResponse` is only fully wired into the Next.js runtime,
// so we stub it to a constructor-like function that records the args.
vi.mock("next/og", () => ({
  ImageResponse: class FakeImageResponse {
    readonly element: unknown;
    readonly options: unknown;
    constructor(element: unknown, options: unknown) {
      this.element = element;
      this.options = options;
    }
  },
}));

// `fumadocs-ui/og` ships ESX runtime components that are expensive to render
// in unit tests; replacing `generate` with a function-component-shaped stub
// keeps the route importable while we assert the static configuration.
vi.mock("fumadocs-ui/og", () => ({
  generate: () => null,
}));

import Image, { alt, contentType, runtime, size } from "@/app/opengraph-image";
import ZhImage, {
  alt as zhAlt,
  contentType as zhContentType,
  runtime as zhRuntime,
  size as zhSize,
} from "@/app/zh/opengraph-image";

describe("app/opengraph-image", () => {
  it("declares the nodejs runtime so `ImageResponse` can run during static export", () => {
    expect(runtime).toBe("nodejs");
  });

  it("emits a 1200x630 PNG with descriptive alt text", () => {
    expect(size).toEqual({ width: 1200, height: 630 });
    expect(contentType).toBe("image/png");
    expect(alt).toMatch(/documentation/i);
  });

  it("returns an ImageResponse when invoked", () => {
    // The default export must be a callable function. We just need to make
    // sure it does not throw and that the shape conforms to `ImageResponse`.
    const result = Image();
    expect(result).toBeDefined();
    return expect(result).resolves.toHaveProperty("options");
  });
});

describe("app/zh/opengraph-image", () => {
  it("declares the nodejs runtime so the Chinese variant mirrors the en one", () => {
    expect(zhRuntime).toBe("nodejs");
  });

  it("emits a 1200x630 PNG with Chinese alt text", () => {
    expect(zhSize).toEqual({ width: 1200, height: 630 });
    expect(zhContentType).toBe("image/png");
    // The alt must include the Chinese 文档 marker so the zh build is
    // distinguishable from the en build in social card metadata.
    expect(zhAlt).toContain("文档");
  });

  it("returns an ImageResponse when invoked", () => {
    const result = ZhImage();
    expect(result).toBeDefined();
    return expect(result).resolves.toHaveProperty("options");
  });
});
