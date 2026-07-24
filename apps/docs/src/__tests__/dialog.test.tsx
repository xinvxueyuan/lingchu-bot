import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

describe("Dialog", () => {
  it("renders open dialog content as a React island component", () => {
    render(
      <Dialog open>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Island dialog</DialogTitle>
            <DialogDescription>Rendered by React.</DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>,
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Island dialog")).toBeInTheDocument();
    expect(screen.getByText("Rendered by React.")).toBeInTheDocument();
  });
});
