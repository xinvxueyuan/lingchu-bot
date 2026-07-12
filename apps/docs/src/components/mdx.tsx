import defaultMdxComponents from "fumadocs-ui/mdx";
import type { MDXComponents } from "mdx/types";
import { ImageZoom } from "fumadocs-ui/components/image-zoom";
import { Accordion, Accordions } from "fumadocs-ui/components/accordion";
import { createGenerator, createFileSystemGeneratorCache } from "fumadocs-typescript";
import { AutoTypeTable, type AutoTypeTableProps } from "fumadocs-typescript/ui";
import { TypeTable } from "fumadocs-ui/components/type-table";
import * as TabsComponents from "fumadocs-ui/components/tabs";
import { Step, Steps } from "fumadocs-ui/components/steps";
import { InlineTOC } from "fumadocs-ui/components/inline-toc";
import { File, Folder, Files } from "fumadocs-ui/components/files";
import Link from "fumadocs-core/link";
import * as Twoslash from "fumadocs-twoslash/ui";
import { Mermaid } from "@/components/mdx/mermaid";

const generator = createGenerator({
  cache: createFileSystemGeneratorCache(".next/fumadocs-typescript"),
});

export function getMDXComponents(components?: MDXComponents): MDXComponents {
  return {
    ...defaultMdxComponents,
    ...Twoslash,
    img: (props: React.ComponentProps<"img">) => (
      <ImageZoom {...(props as Record<string, unknown>)} />
    ),
    Accordion,
    Accordions,
    AutoTypeTable: (props: Partial<AutoTypeTableProps>) => (
      <AutoTypeTable
        {...props}
        generator={generator}
      />
    ),
    TypeTable,
    ...TabsComponents,
    Step,
    Steps,
    InlineTOC,
    File,
    Folder,
    Files,
    a: Link,
    Mermaid,
    ...components,
  } satisfies MDXComponents;
}

// Required by fumadocs MDX provider pattern (providerImportSource)
// Even if not currently consumed, keep for future MDX auto-resolution
export const useMDXComponents = getMDXComponents;

declare global {
  type MDXProvidedComponents = ReturnType<typeof getMDXComponents>;
}
