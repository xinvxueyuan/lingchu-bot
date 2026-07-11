"use client";

import { use, useId, useMemo, useSyncExternalStore } from "react";
import { useTheme } from "next-themes";
import {
  getMermaidConfig,
  sanitizeMermaidSvg,
  renderMermaidSvg,
} from "./mermaid-utils";

const emptySubscribe = () => () => {};

function useMounted() {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
}

export function Mermaid({ chart }: { chart: string }) {
  const mounted = useMounted();

  if (!mounted) return;
  return <MermaidContent chart={chart} />;
}

const cache = new Map<string, Promise<unknown>>();

function cachePromise<T>(
  key: string,
  setPromise: () => Promise<T>,
): Promise<T> {
  const cached = cache.get(key);
  if (cached) return cached as Promise<T>;

  const promise = setPromise();
  cache.set(key, promise);
  return promise;
}

function MermaidContent({ chart }: { chart: string }) {
  const id = useId();
  const { resolvedTheme } = useTheme();
  const { default: mermaid } = use(
    cachePromise("mermaid", () => import("mermaid")),
  );

  const renderPromise = useMemo(() => {
    mermaid.initialize(getMermaidConfig(resolvedTheme));
    return mermaid.render(id, chart.replaceAll("\\n", "\n"));
  }, [chart, id, mermaid, resolvedTheme]);
  const { svg, bindFunctions } = use(renderPromise);
  const sanitizedSvg = sanitizeMermaidSvg(svg);

  return (
    <div
      ref={(container) => {
        if (!container) return;

        renderMermaidSvg(container, sanitizedSvg, bindFunctions);
      }}
    />
  );
}
