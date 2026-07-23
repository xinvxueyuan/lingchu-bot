"use client";
import { useEffect, useRef } from "react";
import type p5 from "p5";
import { ClientOnly } from "@/components/p5/client-only";

export interface P5SketchProps {
  sketch: (p: p5) => void;
  className?: string;
}

function P5SketchImpl({ sketch, className }: P5SketchProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<p5 | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let disposed = false;
    void import("p5").then(({ default: P5 }) => {
      if (disposed || !containerRef.current) return;
      instanceRef.current = new P5(sketch, containerRef.current);
    });

    return () => {
      disposed = true;
      instanceRef.current?.remove();
      instanceRef.current = null;
    };
  }, [sketch]);

  return <div ref={containerRef} className={className} />;
}

export function P5Sketch(props: P5SketchProps) {
  return (
    <ClientOnly>
      <P5SketchImpl {...props} />
    </ClientOnly>
  );
}
