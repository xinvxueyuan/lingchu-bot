import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";

describe("Badge", () => {
  it("renders its children with the default variant", () => {
    render(<Badge>active</Badge>);
    const badge = screen.getByText("active");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute("data-slot", "badge");
  });

  it("applies the variant class for each variant", () => {
    const { rerender } = render(<Badge variant="accent">a</Badge>);
    let badge = screen.getByText("a");
    expect(badge.className).toContain("border-[color-mix");

    rerender(<Badge variant="destructive">a</Badge>);
    badge = screen.getByText("a");
    expect(badge.className).toContain("border-[color-mix");

    rerender(<Badge variant="outline">a</Badge>);
    badge = screen.getByText("a");
    expect(badge.className).toContain("bg-transparent");
  });
});

describe("Alert", () => {
  it("renders title and description inside a note region", () => {
    render(
      <Alert variant="accent">
        <AlertTitle>Adapter selected</AlertTitle>
        <AlertDescription>OneBot V11 is the default adapter.</AlertDescription>
      </Alert>,
    );

    const alert = screen.getByRole("note");
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveAttribute("data-slot", "alert");
    expect(screen.getByText("Adapter selected")).toBeInTheDocument();
    expect(screen.getByText("OneBot V11 is the default adapter.")).toBeInTheDocument();
  });

  it("renders a default icon when none is provided", () => {
    render(
      <Alert>
        <AlertTitle>Default</AlertTitle>
      </Alert>,
    );
    const alert = screen.getByRole("note");
    // The icon container is an aria-hidden span sibling of the content.
    expect(alert.querySelector(':scope > [aria-hidden="true"] svg')).toBeTruthy();
  });
});
