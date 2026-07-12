import { describe, it, expect, vi } from "vitest";

vi.mock("@/lib/source", () => ({
  source: {
    getPages: vi.fn(() => [
      {
        url: "/docs/a",
        slugs: ["a"],
        data: {
          title: "Page A",
          description: "Desc A",
          extractedReferences: [{ href: "/docs/b" }],
        },
      },
      {
        url: "/docs/b",
        slugs: ["b"],
        data: {
          title: "Page B",
          description: "Desc B",
          extractedReferences: [],
        },
      },
      {
        url: "/docs/c",
        slugs: ["c"],
        data: {
          title: "Page C",
          description: "Desc C",
          extractedReferences: [{ href: "/docs/missing" }],
        },
      },
    ]),
    getPageByHref: vi.fn((href: string) => {
      if (href === "/docs/b") return { page: { url: "/docs/b" } };
      return;
    }),
  },
}));

import { buildGraph } from "@/lib/build-graph";

describe("buildGraph", () => {
  it("should return a graph with nodes and links", async () => {
    const graph = await buildGraph();
    expect(graph).toHaveProperty("nodes");
    expect(graph).toHaveProperty("links");
    expect(Array.isArray(graph.nodes)).toBe(true);
    expect(Array.isArray(graph.links)).toBe(true);
  });

  it("should create a node for each page", async () => {
    const graph = await buildGraph();
    expect(graph.nodes).toHaveLength(3);
    const urls = graph.nodes.map((n) => n.id);
    expect(urls).toContain("/docs/a");
    expect(urls).toContain("/docs/b");
    expect(urls).toContain("/docs/c");
  });

  it("should include title and description in nodes", async () => {
    const graph = await buildGraph();
    const nodeA = graph.nodes.find((n) => n.id === "/docs/a");
    expect(nodeA).toBeDefined();
    expect(nodeA?.text).toBe("Page A");
    expect(nodeA?.description).toBe("Desc A");
  });

  it("should create links for valid extracted references", async () => {
    const graph = await buildGraph();
    const link = graph.links.find((l) => l.source === "/docs/a" && l.target === "/docs/b");
    expect(link).toBeDefined();
  });

  it("should skip links for unresolved references", async () => {
    const graph = await buildGraph();
    const brokenLink = graph.links.find(
      (l) => l.source === "/docs/c" && l.target === "/docs/missing",
    );
    expect(brokenLink).toBeUndefined();
  });

  it("should not create links for pages without extracted references", async () => {
    const graph = await buildGraph();
    const linksFromB = graph.links.filter((l) => l.source === "/docs/b");
    expect(linksFromB).toHaveLength(0);
  });
});
