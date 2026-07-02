// Delay + crowding-proxy data shapes for the [metro]/delays page island and the
// table fallbacks. Served from frontend/src/data/<slug>/delays.json
// (pipeline/delays.py, rolled up from the e4a live-feed sample log).

export type SourceInfo = { label: string; url: string; note: string };

export type DelayByMode = {
  mode: string;
  observations: number;
  delayed: number;
  delayedShare: number; // 0..1
};

export type CountdownBucket = { bucket: string; count: number };

export type BunchRoute = {
  route: string;
  observations: number;
  bunched: number;
  bunchRate: number; // 0..1
};

export type DelaysData = {
  source: SourceInfo;
  meta: {
    samples: number;
    firstGenerated: string | null;
    lastGenerated: string | null;
    vehicleObservations: number;
    arrivalObservations: number;
  };
  delay: {
    byMode: DelayByMode[];
    observations: number;
    delayed: number;
    delayedShare: number;
  };
  countdown: CountdownBucket[];
  bunching: {
    observations: number;
    bunched: number;
    bunchRate: number;
    gapMin: number;
    topRoutes: BunchRoute[];
  };
};

// True once the sample log carries at least one snapshot with observations.
export const hasSamples = (d: DelaysData): boolean =>
  d.meta.samples > 0 && (d.meta.vehicleObservations > 0 || d.meta.arrivalObservations > 0);

export const fmtInt = (n: number): string => n.toLocaleString("en-US");

// 0.6667 → "66.7%". Kept at one decimal — these are proxy shares, not precise rates.
export const fmtPct = (share: number): string =>
  `${(share * 100).toLocaleString("en-US", { maximumFractionDigits: 1 })}%`;

// "2026-07-02T18:00:00Z" → "Jul 2, 6:00 PM UTC" for the as-of window label.
export const tsLabel = (iso: string | null): string => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
    timeZone: "UTC", timeZoneName: "short",
  });
};

export const modeLabel = (mode: string): string =>
  mode === "bus" ? "Bus" : mode === "rail" ? "Rail ('L')" : mode;
