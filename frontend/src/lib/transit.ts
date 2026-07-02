// Shared transit metadata for the map island + the page table fallback.
// Agency *brand* colors are deliberately NOT defined here — the design system
// (docs/design-system/TOKENS.md) sources their exact OKLCH values in v1.1 and
// CLAUDE.md forbids guessing them. Routes on the map use each route's own
// GTFS-published color (data, not a guess); authority is encoded by name (table)
// and the legend distinguishes geometry by shape, not color.

export const AUTHORITY_LABELS: Record<string, string> = {
  cta: "CTA",
  pace: "Pace",
  metra: "Metra",
};

export const authorityLabel = (id: string): string => AUTHORITY_LABELS[id] ?? id;

export type TransitData = {
  bbox: [number, number, number, number];
  routes: {
    authority_id: string;
    route_id: string;
    short_name: string | null;
    long_name: string | null;
    route_type: number | null;
    color: string | null;
  }[];
  stopCounts: Record<string, number>;
  stopTotal: number;
  hex: HexData;
};

// Hex choropleth (v1.1). `breaks` are the 4 quintile thresholds per metric,
// precomputed at tile-build time (pipeline/tiles.py) so the client ships no
// break math and the legend ranges are exact.
export type HexCell = { h3: string; jobs: number; population: number; access?: number };
export type HexMetric = "jobs" | "population" | "access";
export type HexData = {
  count: number;
  // `cbd_time` (minutes to nearest CBD) is a v3.10 TOD overlay break, present when
  // the tiles carry the TOD mart — optional so the map page stays metric-agnostic.
  breaks: Record<HexMetric, number[]> & { cbd_time?: number[] };
  topJobs: HexCell[];
  topPopulation: HexCell[];
  topAccess: HexCell[];
};

// 5-step sequential ramps (low → high), distinct hue per metric so the two
// overlays never read alike. Color is never the only signal: only one overlay
// shows at a time, the legend prints numeric ranges, and a click reveals exact
// values (docs/DEFINITION_OF_DONE.md — map layers need a non-color encoding).
export const HEX_RAMPS: Record<HexMetric, [string, string, string, string, string]> = {
  jobs: ["#3a2a12", "#7c4d18", "#b6711f", "#e09a36", "#ffd479"],
  population: ["#15324a", "#1f6091", "#2a86c0", "#52b0db", "#9fdcf0"],
  access: ["#13332a", "#1f6b4a", "#2a9d6a", "#52c98f", "#9ff0c4"],
};

export const HEX_LABELS: Record<HexMetric, string> = {
  jobs: "Jobs (workplace)",
  population: "Population",
  access: "Jobs reachable (½-mi walk)",
};

// Legend range labels from the 4 break thresholds + the step semantics:
// v < b0 | b0–b1 | b1–b2 | b2–b3 | ≥ b3.
export const hexBinLabels = (breaks: number[]): string[] => {
  const f = (n: number) => n.toLocaleString();
  return [
    `< ${f(breaks[0])}`,
    `${f(breaks[0])}–${f(breaks[1])}`,
    `${f(breaks[1])}–${f(breaks[2])}`,
    `${f(breaks[2])}–${f(breaks[3])}`,
    `≥ ${f(breaks[3])}`,
  ];
};
