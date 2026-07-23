"use client";
import dynamic from "next/dynamic";

const HeroSketch = dynamic(
  async () => (await import("@/components/p5/hero-sketch")).HeroSketch,
  { ssr: false, loading: () => null },
);

export function HeroSketchLoader({ className }: { className?: string }) {
  return <HeroSketch {...(className ? { className } : {})} />;
}
