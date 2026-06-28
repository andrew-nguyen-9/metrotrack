// gen-metros.mjs — generate src/data/metros.json from the authored metros/*.toml.
// The toml files (../metros/*.toml) are the authoring surface (see metros/_schema.md);
// this script mirrors the serving subset the frontend needs (slug, name, region, tz,
// status, bbox) into a build artifact so `getStaticPaths` and the `/` redirect read
// from config, never a hardcoded list. Runs as `prebuild`; the committed copy keeps
// `astro check` green between builds. Edit the toml, not metros.json.
import { readdirSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parse as parseToml } from "smol-toml";

const here = dirname(fileURLToPath(import.meta.url));
const metrosDir = resolve(here, "../../metros");
const outFile = resolve(here, "../src/data/metros.json");

const SLUG_RE = /^[a-z][a-z0-9-]*$/;

function loadMetro(file) {
  const raw = parseToml(readFileSync(join(metrosDir, file), "utf8"));
  const { slug, name, region, tz, status, bbox } = raw;
  if (!SLUG_RE.test(slug ?? "")) throw new Error(`${file}: invalid slug '${slug}'`);
  if (!Array.isArray(bbox) || bbox.length !== 4) throw new Error(`${file}: bbox must be [minLon,minLat,maxLon,maxLat]`);
  if (status !== "live" && status !== "soon") throw new Error(`${file}: status must be live|soon`);
  return { slug, name, region: region ?? name, tz, status, bbox: bbox.map(Number) };
}

const metros = readdirSync(metrosDir)
  .filter((f) => f.endsWith(".toml"))
  .map(loadMetro)
  .sort((a, b) => a.slug.localeCompare(b.slug));

if (!metros.length) throw new Error(`no metros found under ${metrosDir}`);

mkdirSync(dirname(outFile), { recursive: true });
writeFileSync(outFile, JSON.stringify(metros, null, 2) + "\n");
console.log(`[gen-metros] wrote ${metros.length} metro(s) → ${outFile}: ${metros.map((m) => `${m.slug}(${m.status})`).join(", ")}`);
