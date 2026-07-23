import { describe, it, expect } from "vitest";
import { cn } from "@/lib/cn";

describe("cn", () => {
  it("should merge class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("should handle conditional classes", () => {
    expect(cn("foo", false, "baz")).toBe("foo baz");
  });

  it("should merge conflicting tailwind classes", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });

  it("should handle undefined and null", () => {
    expect(cn("foo", undefined, null, "bar")).toBe("foo bar");
  });

  it("should return empty string for no arguments", () => {
    expect(cn()).toBe("");
  });

  it("should handle object form (clsx conditional object)", () => {
    expect(cn("foo", { bar: true, baz: false })).toBe("foo bar");
  });

  it("should handle array form (clsx array of strings)", () => {
    expect(cn("foo", ["bar", "baz"])).toBe("foo bar baz");
  });

  it("should handle nested arrays mixed with objects", () => {
    expect(cn("foo", [["bar"], { baz: true }])).toBe("foo bar baz");
  });

  it("should merge conflicting tailwind classes inside nested arrays", () => {
    expect(cn("px-2", [{ "px-8": true }, ["py-1"]])).toBe("px-8 py-1");
  });
});
