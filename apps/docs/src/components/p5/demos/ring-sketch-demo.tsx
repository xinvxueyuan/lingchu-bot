"use client";
import type p5 from "p5";
import { P5Sketch } from "@/components/p5/p5-sketch";

const ringSketch = (p: p5) => {
  let angle = 0;
  p.setup = () => {
    p.createCanvas(480, 240);
    p.noFill();
    p.strokeWeight(2);
  };
  p.draw = () => {
    p.clear();
    p.translate(p.width / 2, p.height / 2);
    for (let i = 0; i < 12; i++) {
      const a = angle + (i * p.TWO_PI) / 12;
      const r = 60 + 20 * p.sin(angle * 2 + i);
      p.stroke(`hsl(${(i * 30) % 360}, 70%, 60%)`);
      p.ellipse(p.cos(a) * r, p.sin(a) * r, 18, 18);
    }
    angle += 0.02;
  };
};

export function RingSketchDemo() {
  return <P5Sketch sketch={ringSketch} />;
}
