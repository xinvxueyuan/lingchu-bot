import { describe, expect, it } from "vitest";
import { appName, gitConfig, SITE_URL } from "@/lib/shared";

describe("shared constants", () => {
  it("should export appName", () => {
    expect(appName).toBe("Lingchu Bot");
  });

  it("should export SITE_URL", () => {
    expect(SITE_URL).toBe("https://lingchu.zone.id/");
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
