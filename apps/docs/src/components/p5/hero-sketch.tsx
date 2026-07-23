"use client";
import type p5 from "p5";
import { P5Sketch } from "@/components/p5/p5-sketch";

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

const PARTICLE_COUNT = 36;
const LINK_DISTANCE = 120;

const heroSketch = (p: p5) => {
  let particles: Particle[] = [];
  let canvasRenderer: p5.Renderer | null = null;

  const getParentEl = (): HTMLElement | null => {
    const raw: unknown = canvasRenderer?.elt;
    if (raw instanceof HTMLElement) {
      return raw.parentElement;
    }
    return null;
  };

  const rebuild = () => {
    particles = Array.from({ length: PARTICLE_COUNT }, () => ({
      x: p.random(p.width),
      y: p.random(p.height),
      vx: p.random(-0.4, 0.4),
      vy: p.random(-0.4, 0.4),
    }));
  };

  const drawLinks = (a: Particle, startIndex: number) => {
    for (let j = startIndex; j < particles.length; j++) {
      const b = particles[j];
      if (!b) continue;
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      const dist = Math.hypot(dx, dy);
      if (dist < LINK_DISTANCE) {
        const alpha = p.map(dist, 0, LINK_DISTANCE, 80, 0);
        p.stroke(255, 255, 255, alpha);
        p.line(a.x, a.y, b.x, b.y);
      }
    }
  };

  p.setup = () => {
    canvasRenderer = p.createCanvas(800, 400);
    const parent = getParentEl();
    if (parent) {
      p.resizeCanvas(parent.clientWidth, parent.clientHeight);
    }
    rebuild();
  };

  p.draw = () => {
    p.clear();
    for (const a of particles) {
      a.x += a.vx;
      a.y += a.vy;
      if (a.x < 0 || a.x > p.width) a.vx *= -1;
      if (a.y < 0 || a.y > p.height) a.vy *= -1;
    }
    p.strokeWeight(1);
    for (const [i, a] of particles.entries()) {
      drawLinks(a, i + 1);
    }
  };

  p.windowResized = () => {
    const parent = getParentEl();
    if (parent) p.resizeCanvas(parent.clientWidth, parent.clientHeight);
  };
};

export function HeroSketch({ className }: { className?: string }) {
  return <P5Sketch sketch={heroSketch} {...(className ? { className } : {})} />;
}
