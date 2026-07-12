import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LLMBadge } from "@/components/llm-badge";

describe("LLMBadge", () => {
  it("should render with zh locale by default", () => {
    render(<LLMBadge />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/llms.txt");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("should render zh aria-label when locale is zh", () => {
    render(<LLMBadge locale="zh" />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("aria-label", "可通过 llms.txt 获取 AI 友好文档");
  });

  it("should render en aria-label when locale is en", () => {
    render(<LLMBadge locale="en" />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("aria-label", "AI-friendly docs available via llms.txt");
  });
});
