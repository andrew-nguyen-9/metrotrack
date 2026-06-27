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
};
