import { source } from '@/lib/source';
import type { Graph } from '@/components/graph-view';
import type { ExtractedReference } from 'fumadocs-mdx';

interface PageDataWithReferences {
  extractedReferences?: ExtractedReference[];
  [key: string]: unknown;
}

export async function buildGraph(): Promise<Graph> {
  const pages = source.getPages();
  const graph: Graph = { links: [], nodes: [] };

  for (const page of pages) {
    graph.nodes.push({
      id: page.url,
      url: page.url,
      text: page.data.title,
      description: page.data.description,
    });

    const data = page.data as unknown as PageDataWithReferences;
    const { extractedReferences = [] } = data;
    for (const ref of extractedReferences) {
      const refPage = source.getPageByHref(ref.href);
      if (!refPage) continue;

      graph.links.push({
        source: page.url,
        target: refPage.page.url,
      });
    }
  }

  return graph;
}
