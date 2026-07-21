import { describe, it, expect, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { GraphView, type Graph } from "@/components/graph-view";

vi.mock("fumadocs-core/framework", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("react-force-graph-2d", () => ({
  default: () => <div data-testid="force-graph" />,
}));

const mockGraph: Graph = {
  nodes: [
    {
      id: "/docs/a",
      url: "/docs/a",
      text: "Page A",
      description: "Description A",
    },
    {
      id: "/docs/b",
      url: "/docs/b",
      text: "Page B",
      description: "Description B",
    },
  ],
  links: [{ source: "/docs/a", target: "/docs/b" }],
};

describe("GraphView", () => {
  it("should render a container with correct height", async () => {
    let container: HTMLElement = document.createElement("div");
    await act(async () => {
      const result = render(<GraphView graph={mockGraph} />);
      container = result.container;
      await Promise.resolve();
    });
    const wrapper = container.querySelector(String.raw`.h-\[600px\]`);
    expect(wrapper).toBeInTheDocument();
  });

  it("should render with empty graph", async () => {
    const emptyGraph: Graph = { nodes: [], links: [] };
    let container: HTMLElement = document.createElement("div");
    await act(async () => {
      const result = render(<GraphView graph={emptyGraph} />);
      container = result.container;
      await Promise.resolve();
    });
    expect(container.querySelector(String.raw`.h-\[600px\]`)).toBeInTheDocument();
  });

  it("should render ForceGraph when mounted on client", async () => {
    await act(async () => {
      render(<GraphView graph={mockGraph} />);
      await Promise.resolve();
    });
    expect(screen.getByTestId("force-graph")).toBeInTheDocument();
  });
});
