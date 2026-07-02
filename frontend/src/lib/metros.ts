// Metro registry + per-metro data loading for the `[metro]/*` routes.
// `metros.json` is generated from the authored `metros/*.toml` (scripts/gen-metros.mjs)
// so `getStaticPaths` and the data lookups read from config, never a hardcoded list.
// Islands stay generic: the only per-metro input is the data + bbox loaded here.
import metrosJson from "../data/metros.json";
import type { TransitData } from "./transit";
import type { FundingData } from "./funding";
import type { HiringData } from "./hiring";
import type { RidershipData } from "./ridership";

export type MetroStatus = "live" | "soon";

export type Metro = {
  slug: string;
  name: string;
  region: string;
  tz: string;
  status: MetroStatus;
  bbox: [number, number, number, number];
};

// Normalize the generated JSON (bbox is number[] there) into the typed tuple.
export const METROS: Metro[] = (metrosJson as Metro[]).map((m) => ({
  ...m,
  bbox: [m.bbox[0], m.bbox[1], m.bbox[2], m.bbox[3]],
}));

// Live metros get real routes today; `getStaticPaths` builds exactly these (just
// `chicago` now). "soon" metros are listed but not yet routed.
export const liveMetros = (): Metro[] => METROS.filter((m) => m.status === "live");

// Placeholder regions on the national directory — greyed "coming soon" cards only.
// Scope is LOCKED (E2): Chicago is the sole live metro; these 9 are directory
// placeholders with NO TOML, NO pipeline, NO route (we never fake a data page).
export const comingRegions: readonly string[] = [
  "New York", "SF Bay Area", "Boston", "Washington, DC", "Los Angeles",
  "Atlanta", "Seattle", "Philadelphia", "Dallas–Fort Worth",
];

export const getMetro = (slug: string): Metro => {
  const m = METROS.find((x) => x.slug === slug);
  if (!m) throw new Error(`unknown metro '${slug}' — not in metros.json`);
  return m;
};

// The default metro the bare `/` redirect targets (first live, alphabetical).
export const defaultMetro = (): Metro => liveMetros()[0] ?? METROS[0];

// Shared `getStaticPaths` for every `[metro]/*` route — one entry per live metro
// (just `chicago` today). Pages do `export const getStaticPaths = metroPaths;`.
export const metroPaths = () =>
  liveMetros().map((m) => ({ params: { metro: m.slug }, props: { metro: m } }));

// Per-metro PMTiles live under public/<slug>/transit.pmtiles (mirrors the data dir);
// v2.0.6 will emit these from pipeline/tiles.py as tiles/<slug>.pmtiles.
export const pmtilesUrl = (slug: string): string => `/${slug}/transit.pmtiles`;

// Eagerly load every metro's data JSON; index by slug. Keys are file paths relative
// to this module, e.g. "../data/chicago/transit.json".
const transitFiles = import.meta.glob<TransitData>("../data/*/transit.json", { eager: true, import: "default" });
const fundingFiles = import.meta.glob<FundingData>("../data/*/funding.json", { eager: true, import: "default" });
const hiringFiles = import.meta.glob<HiringData>("../data/*/hiring.json", { eager: true, import: "default" });
const ridershipFiles = import.meta.glob<RidershipData>("../data/*/ridership.json", { eager: true, import: "default" });

const pick = <T>(files: Record<string, T>, slug: string, kind: string): T => {
  const hit = Object.entries(files).find(([path]) => path.includes(`/data/${slug}/`));
  if (!hit) throw new Error(`no ${kind} data for metro '${slug}'`);
  return hit[1];
};

export const transitData = (slug: string): TransitData => pick(transitFiles, slug, "transit");
export const fundingData = (slug: string): FundingData => pick(fundingFiles, slug, "funding");
export const hiringData = (slug: string): HiringData => pick(hiringFiles, slug, "hiring");
export const ridershipData = (slug: string): RidershipData => pick(ridershipFiles, slug, "ridership");

// Job access reads the hex slice of transit.json (the gold_hex_access score, exported
// by pipeline/tiles.py) — see [metro]/job-access.astro. No separate loader needed.
