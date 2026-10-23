#!/usr/bin/env node
// SPDX-FileCopyrightText: 2026 lingchu-bot contributors <support@xinvstar.xyz>
// SPDX-License-Identifier: LGPL-3.0-or-later
/**
 * Stage the WebUI static build into the Python package tree.
 *
 * Copies `apps/webui/dist/client` (the SPA static output) to
 * `src/plugins/nonebot_plugin_lingchu_bot/webui/dist/client` so the files ship
 * inside the wheel. `uv_build` uses `module-root = "src/plugins"`, so anything
 * under `src/` is packaged automatically — no build-backend change needed.
 *
 * The copy is also the only mechanical guard against the Vite `base` silently
 * drifting away from the Python-side mount prefix: the staged `index.html` is
 * asserted to reference its assets under
 * `LINGCHU_WEBUI_BASE_PATH ?? "/lc/webui/"`. If they disagree the build fails
 * here instead of producing a wheel whose page cannot load its own JS.
 *
 * Usage:
 *   node scripts/stage_webui.mjs
 *   LINGCHU_WEBUI_BASE_PATH=/lc/webui/ node scripts/stage_webui.mjs
 */

import {
  cpSync,
  existsSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

/** Repository root, derived from this script's location (`<root>/scripts/`). */
const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

/** Static client build output produced by the webui workspace. */
const SOURCE_DIR = join(REPO_ROOT, "apps", "webui", "dist", "client");

/** Destination inside the Python package (ships in the wheel). */
const TARGET_DIR = join(
  REPO_ROOT,
  "src",
  "plugins",
  "nonebot_plugin_lingchu_bot",
  "webui",
  "dist",
  "client",
);

/**
 * Expected mount prefix. The Python side derives the page root as `<base>/`,
 * so asset URLs always carry exactly one trailing slash. Mirrors
 * `DEFAULT_WEBUI_BASE_PATH` in `services/webui/paths.py`.
 */
const DEFAULT_BASE_PREFIX = "/lc/webui/";

/**
 * Print an error prefixed with the script name and exit with status 1.
 *
 * @param {string} message Human readable failure reason.
 * @returns {never} Never returns — always exits the process.
 */
function fail(message) {
  console.error(`\u2717 stage_webui: ${message}`);
  process.exit(1);
}

/**
 * Normalize a configured base path to the form used in built asset URLs.
 *
 * Collapses duplicate slashes, adds a leading slash and exactly one trailing
 * slash so `/lc/webui`, `lc/webui` and `/lc/webui/` all compare equal.
 *
 * @param {string} raw Base path from the environment or the default.
 * @returns {string} Normalized prefix with a single trailing slash.
 */
function normalizeBasePrefix(raw) {
  const trimmed = raw.trim().replace(/\/{2,}/gu, "/").replace(/^\/+|\/+$/gu, "");
  return trimmed ? `/${trimmed}/` : "/";
}

/**
 * Recursively collect the file count and total byte size under `dir`.
 *
 * @param {string} dir Directory to walk.
 * @returns {{ files: number, bytes: number }} File count and byte total.
 */
function measure(dir) {
  let files = 0;
  let bytes = 0;
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      const nested = measure(full);
      files += nested.files;
      bytes += nested.bytes;
    } else if (entry.isFile()) {
      files += 1;
      bytes += statSync(full).size;
    }
  }
  return { files, bytes };
}

const expectedPrefix = normalizeBasePrefix(
  process.env.LINGCHU_WEBUI_BASE_PATH ?? DEFAULT_BASE_PREFIX,
);

// ── 1. Validate the source build ──────────────────────────────────────────
if (!existsSync(SOURCE_DIR)) {
  fail(
    `source build not found: ${SOURCE_DIR}\n` +
      "  Run `pnpm webui:build` (or `task webui:build`) before staging.",
  );
}
const sourceIndex = join(SOURCE_DIR, "index.html");
const sourceAssets = join(SOURCE_DIR, "assets");
if (!existsSync(sourceIndex)) {
  fail(`source build is missing index.html: ${sourceIndex}`);
}
if (!existsSync(sourceAssets) || !statSync(sourceAssets).isDirectory()) {
  fail(`source build is missing the assets/ directory: ${sourceAssets}`);
}

// ── 2. Assert the build prefix matches the Python mount prefix ────────────
// Vite 的 `base` 与 react-router 的 `basename` 必须同时等于挂载前缀，产物里的
// 资源 URL（index.html 与 JS chunk 内部都硬编码）才会指向正确的地址。这里是
// 唯一的机械守卫：一旦两者漂移，构建在此失败，而不是产出一个打不开的包。
const sourceHtml = readFileSync(sourceIndex, "utf8");
const referenced = [...sourceHtml.matchAll(/(?:src|href)="(\/[^"]*)"/gu)]
  .map((match) => match[1])
  .filter((url) => !/^\/\//u.test(url));
const mismatched = referenced.filter((url) => !url.startsWith(expectedPrefix));
if (mismatched.length > 0) {
  fail(
    "asset prefix mismatch between the webui build and the Python mount prefix.\n" +
      `  expected prefix: ${expectedPrefix}\n` +
      `  actual references: ${mismatched.slice(0, 5).join(", ")}\n` +
      "  Align Vite `base` and react-router `basename` with " +
      "LINGCHU_WEBUI_BASE_PATH (see services/webui/paths.py).",
  );
}

// ── 3. Replace the destination and copy ──────────────────────────────────
rmSync(TARGET_DIR, { recursive: true, force: true });
cpSync(SOURCE_DIR, TARGET_DIR, { recursive: true });

// ── 4. Verify the staged output is complete ───────────────────────────────
if (!existsSync(join(TARGET_DIR, "index.html"))) {
  fail(`staged output is missing index.html: ${join(TARGET_DIR, "index.html")}`);
}
const stagedAssets = join(TARGET_DIR, "assets");
if (!existsSync(stagedAssets)) {
  fail(`staged output is missing the assets/ directory: ${stagedAssets}`);
}
const stagedScripts = readdirSync(stagedAssets).filter((name) => name.endsWith(".js"));
if (stagedScripts.length === 0) {
  fail(`staged output has no assets/*.js bundle under ${stagedAssets}`);
}

const { files, bytes } = measure(TARGET_DIR);
const kib = (bytes / 1024).toFixed(1);
const relativeTarget = TARGET_DIR.replace(`${REPO_ROOT}\\`, "").replaceAll("\\", "/");
console.log(
  `\u2713 stage_webui: copied ${files} file(s), ${bytes} bytes (${kib} KiB) ` +
    `to ${relativeTarget} (base: ${expectedPrefix}, js bundles: ${stagedScripts.length})`,
);
