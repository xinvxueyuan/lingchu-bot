"use client";
import { HeroSketch } from "@/components/p5/hero-sketch";

export function HeroSketchLoader({ className }: { className?: string }) {
  return <HeroSketch {...(className ? { className } : {})} />;
}
