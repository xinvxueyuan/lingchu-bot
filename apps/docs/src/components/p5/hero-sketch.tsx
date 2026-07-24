"use client";
import type p5 from "p5";
import { P5Sketch } from "@/components/p5/p5-sketch";

/**
 * Organic Turbulence — hero flow field for the Lingchu Bot docs.
 *
 * Algorithmic philosophy: see ORGANIC_TURBULENCE.md in this folder.
 * Conceptual seed: 灵枢 (Lingchu — "the spiritual pivot"). A fraction of
 * particles spawn along a few invisible sinusoidal meridian curves, so density
 * accumulates along them like vital channels. Those who know the etymology
 * feel it; everyone else sees organic turbulence.
 *
 * Everything is seeded for reproducibility. Theme colors are read from the
 * Starlight CSS variables and refreshed when the theme changes.
 */

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
}

// Seeded constants — reproducibility is non-negotiable.
const SEED = 20_240_617;
const PARTICLE_COUNT = 240;
const FADE_ALPHA = 16; // trail veil opacity (0–255); lower = longer trails
const NOISE_SCALE = 0.0026; // spatial field resolution
const NOISE_TIME_STEP = 0.0006; // temporal drift — meridians migrate slowly
const STEER_FORCE = 0.16;
const FRICTION = 0.93;
const SPEED_MAX = 2.4;
const OCTAVES = 3; // layered Perlin noise
const MERIDIAN_COUNT = 4; // invisible 灵枢 channels
const MERIDIAN_FRACTION = 0.34; // share of respawns born along meridians

/** Parse a CSS color string into an [r, g, b] tuple. Falls back to a sane default. */
function parseColor(raw: string, fallback: [number, number, number]): [number, number, number] {
  const m = raw.match(/rgba?\(([^)]+)\)/);
  if (!m) return fallback;
  const parts = m[1].split(",").map((s) => Number(s.trim()));
  if (parts.length < 3 || parts.some((n) => Number.isNaN(n))) return fallback;
  return [parts[0], parts[1], parts[2]];
}

/** Read a CSS variable from the document, resolved to its current computed value. */
function readVar(name: string, fallback: [number, number, number]): [number, number, number] {
  if (typeof globalThis === "undefined") return fallback;
  const raw = globalThis
    .getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return raw ? parseColor(raw, fallback) : fallback;
}

const heroSketch = (p: p5) => {
  let particles: Particle[] = [];
  let canvasRenderer: p5.Renderer | null = null;
  let timeT = 0;
  let reducedMotion = false;
  let accentRgb: [number, number, number] = [14, 165, 233];
  let bgRgb: [number, number, number] = [2, 8, 23];
  let themeObserver: MutationObserver | null = null;

  const getParentEl = (): HTMLElement | null => {
    const raw: unknown = canvasRenderer?.elt;
    if (raw instanceof HTMLElement) {
      return raw.parentElement;
    }
    return null;
  };

  const refreshThemeColors = () => {
    // --sl-color-accent is the Starlight accent; --sl-color-bg-nav is the
    // elevated surface used by .p5-sketch. Both adapt to light/dark mode.
    accentRgb = readVar("--sl-color-accent", [14, 165, 233]);
    bgRgb = readVar("--sl-color-bg-nav", [2, 8, 23]);
  };

  /** Layered Perlin noise: sum of octaves at decreasing amplitude. */
  const fieldAngle = (x: number, y: number, t: number): number => {
    let sum = 0;
    let amp = 1;
    let freq = 1;
    let norm = 0;
    for (let o = 0; o < OCTAVES; o++) {
      sum += amp * p.noise(x * freq * NOISE_SCALE, y * freq * NOISE_SCALE, t);
      norm += amp;
      amp *= 0.5;
      freq *= 2;
    }
    return (sum / norm) * p.TWO_PI * 2;
  };

  /** Invisible 灵枢 meridian: a sinusoidal vertical channel at column k. */
  const meridianX = (k: number, y: number): number => {
    const col = (k + 1) / (MERIDIAN_COUNT + 1);
    const baseX = col * p.width;
    const sway = Math.sin(y * 0.0042 + k * 1.7) * (p.width * 0.06);
    return baseX + sway;
  };

  const spawn = (initial = false): Particle => {
    const maxLife = p.random(140, 320);
    let x: number;
    let y: number;
    if (!initial && p.random() < MERIDIAN_FRACTION) {
      // Spawn along an invisible meridian — density accumulates into channels.
      const k = Math.floor(p.random(MERIDIAN_COUNT));
      y = p.random(p.height);
      x = meridianX(k, y) + p.randomGaussian(0, 8);
    } else {
      x = p.random(p.width);
      y = p.random(p.height);
    }
    return {
      x,
      y,
      vx: 0,
      vy: 0,
      life: initial ? p.random(maxLife) : maxLife,
      maxLife,
    };
  };

  const rebuild = () => {
    particles = Array.from({ length: PARTICLE_COUNT }, () => spawn(true));
  };

  /** Slow palette: lerp from shadow tone to accent by speed. */
  const strokeForSpeed = (speed: number) => {
    const t = Math.min(1, speed / SPEED_MAX);
    // Brighter at high speed, dimmer at low speed — velocity-mapped color.
    const r = bgRgb[0] + (accentRgb[0] - bgRgb[0]) * t;
    const g = bgRgb[1] + (accentRgb[1] - bgRgb[1]) * t;
    const b = bgRgb[2] + (accentRgb[2] - bgRgb[2]) * t;
    const alpha = 60 + 150 * t;
    p.stroke(r, g, b, alpha);
  };

  const step = () => {
    // Translucent veil — history weights the present; trails accumulate.
    p.noStroke();
    p.fill(bgRgb[0], bgRgb[1], bgRgb[2], FADE_ALPHA);
    p.rect(0, 0, p.width, p.height);

    p.strokeWeight(1.1);

    for (const a of particles) {
      const angle = fieldAngle(a.x, a.y, timeT);
      // Steer toward the field vector, damped by friction — edge of instability.
      a.vx = a.vx * FRICTION + Math.cos(angle) * STEER_FORCE;
      a.vy = a.vy * FRICTION + Math.sin(angle) * STEER_FORCE;

      // Cap speed; read color from velocity.
      const speed = Math.hypot(a.vx, a.vy);
      if (speed > SPEED_MAX) {
        a.vx = (a.vx / speed) * SPEED_MAX;
        a.vy = (a.vy / speed) * SPEED_MAX;
      }

      const px = a.x;
      const py = a.y;
      a.x += a.vx;
      a.y += a.vy;
      a.life -= 1;

      // Draw the trail segment for this tick.
      strokeForSpeed(speed);
      p.line(px, py, a.x, a.y);

      // Lifecycle: respawn at a fresh origin when exhausted or out of bounds.
      const outOfBounds = a.x < -20 || a.x > p.width + 20 || a.y < -20 || a.y > p.height + 20;
      if (a.life <= 0 || outOfBounds) {
        Object.assign(a, spawn(false));
      }
    }

    timeT += NOISE_TIME_STEP;
  };

  p.setup = () => {
    canvasRenderer = p.createCanvas(800, 360);
    p.noiseSeed(SEED);
    p.randomSeed(SEED);
    refreshThemeColors();
    reducedMotion =
      typeof globalThis !== "undefined" &&
      globalThis.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const parent = getParentEl();
    if (parent) {
      p.resizeCanvas(parent.clientWidth, parent.clientHeight);
    }
    rebuild();

    // Paint a single base frame so the canvas is never blank before first draw.
    p.background(bgRgb[0], bgRgb[1], bgRgb[2]);

    // Refresh colors when Starlight toggles light/dark theme.
    if (typeof globalThis !== "undefined") {
      themeObserver = new MutationObserver(() => {
        refreshThemeColors();
        p.background(bgRgb[0], bgRgb[1], bgRgb[2]);
      });
      themeObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-theme", "class"],
      });
    }
  };

  p.draw = () => {
    if (reducedMotion) {
      // Respect reduced-motion: render a single calm frame, then stop.
      step();
      p.noLoop();
      return;
    }
    step();
  };

  p.windowResized = () => {
    const parent = getParentEl();
    if (parent) p.resizeCanvas(parent.clientWidth, parent.clientHeight);
    p.background(bgRgb[0], bgRgb[1], bgRgb[2]);
  };

  // Best-effort cleanup if p5 is torn down externally.
  const originalRemove = p.remove.bind(p);
  p.remove = () => {
    themeObserver?.disconnect();
    themeObserver = null;
    originalRemove();
  };
};

export function HeroSketch({ className }: { className?: string }) {
  return (
    <P5Sketch
      sketch={heroSketch}
      {...(className ? { className } : {})}
    />
  );
}
