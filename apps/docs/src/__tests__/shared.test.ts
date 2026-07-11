import { describe, it, expect } from "vitest";
import {
  appName,
  docsRoute,
  docsImageRoute,
  docsContentRoute,
  gitConfig,
} from "@/lib/shared";

describe("shared constants", () => {
  it("should export appName", () => {
    expect(appName).toBe("Lingchu Bot");
  });

  it("should export docs routes", () => {
    expect(docsRoute).toBe("/docs");
    expect(docsImageRoute).toBe("/og/docs");
    expect(docsContentRoute).toBe("/llms.mdx/docs");
  });

  it("should export gitConfig with required fields", () => {
    expect(gitConfig).toHaveProperty("user");
    expect(gitConfig).toHaveProperty("repo");
    expect(gitConfig).toHaveProperty("branch");
    expect(typeof gitConfig.user).toBe("string");
    expect(typeof gitConfig.repo).toBe("string");
    expect(typeof gitConfig.branch).toBe("string");
  });
});
