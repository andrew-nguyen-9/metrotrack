// Transit-oriented-development data (v3.10): density + growth + time-to-CBD.
// Shape mirrors pipeline/tod_export.py → data/<slug>/tod.json. CBDs are a list
// (data-driven, N per metro) so the page never hardcodes a single district.

export type Cbd = { id: string; name: string; lat: number; lon: number };

export type TodRing = { label: string; hexes: number; jobs: number; population: number };

export type TodData = {
  asOf: string;
  cbds: Cbd[];
  speedKmh: number;
  density: { hexCount: number; jobs: number; population: number };
  growth: {
    jobs: number; jobsPrev: number; jobsGrowthPct: number | null;
    population: number; popPrev: number; popGrowthPct: number | null;
    jobsYear: number; jobsPriorYear: number | null;
    popYear: number; popPriorYear: number;
  };
  rings: TodRing[];
};

// A signed-percent → Stat delta descriptor. Growth is neutral (up isn't "good"):
// the arrow + sign carry direction, tone stays muted so we assert no judgement.
export const growthDelta = (pct: number | null) =>
  pct == null
    ? undefined
    : {
        value: `${pct > 0 ? "+" : ""}${pct.toFixed(1)}%`,
        dir: (pct >= 0 ? "up" : "down") as "up" | "down",
        tone: "muted" as const,
      };
