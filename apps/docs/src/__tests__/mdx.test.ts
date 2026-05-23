import { describe, it, expect, vi } from 'vitest';

vi.mock('fumadocs-ui/components/image-zoom', () => ({
  ImageZoom: () => null,
}));

vi.mock('fumadocs-ui/components/accordion', () => ({
  Accordion: () => null,
  Accordions: () => null,
}));

vi.mock('fumadocs-ui/components/type-table', () => ({
  TypeTable: () => null,
}));

vi.mock('fumadocs-ui/components/tabs', () => ({
  Tabs: () => null,
  Tab: () => null,
  TabsList: () => null,
  TabsTrigger: () => null,
  TabsContent: () => null,
}));

vi.mock('fumadocs-ui/components/steps', () => ({
  Step: () => null,
  Steps: () => null,
}));

vi.mock('fumadocs-ui/components/inline-toc', () => ({
  InlineTOC: () => null,
}));

vi.mock('fumadocs-ui/components/files', () => ({
  File: () => null,
  Folder: () => null,
  Files: () => null,
}));

vi.mock('fumadocs-typescript/ui', () => ({
  AutoTypeTable: () => null,
}));

vi.mock('fumadocs-typescript', () => ({
  createGenerator: () => ({}),
  createFileSystemGeneratorCache: () => ({}),
}));

import { getMDXComponents } from '@/components/mdx';

describe('getMDXComponents', () => {
  it('should return an object with all required components', () => {
    const components = getMDXComponents();
    expect(components).toHaveProperty('img');
    expect(components).toHaveProperty('Accordion');
    expect(components).toHaveProperty('Accordions');
    expect(components).toHaveProperty('AutoTypeTable');
    expect(components).toHaveProperty('TypeTable');
    expect(components).toHaveProperty('Tabs');
    expect(components).toHaveProperty('Tab');
    expect(components).toHaveProperty('Step');
    expect(components).toHaveProperty('Steps');
    expect(components).toHaveProperty('InlineTOC');
    expect(components).toHaveProperty('File');
    expect(components).toHaveProperty('Folder');
    expect(components).toHaveProperty('Files');
    expect(components).toHaveProperty('a');
  });

  it('should merge custom components', () => {
    const CustomComponent = () => null;
    const components = getMDXComponents({ Custom: CustomComponent });
    expect((components as Record<string, unknown>).Custom).toBe(CustomComponent);
  });

  it('should allow custom components to override defaults', () => {
    const CustomImg = () => null;
    const components = getMDXComponents({ img: CustomImg });
    expect(components.img).toBe(CustomImg);
  });

  it('should include default MDX components', () => {
    const components = getMDXComponents();
    expect(components).toHaveProperty('pre');
  });
});
