// Ridership data shapes + helpers for the trend/by-line chart islands and the
// table fallbacks. Served from frontend/src/data/<slug>/ridership.json
// (pipeline/ridership_export.py).

export type SourceInfo = { label: string; url: string; note: string };
export type TrendPoint = { month: string; bus: number; rail: number };
export type LineRow = { route: string; route_name: string; rides: number };
export type StopRow = { station_id: string; station_name: string; rides: number };

export type RidershipData = {
  sources: { line: SourceInfo; stop: SourceInfo };
  latestMonth: { line: string | null; stop: string | null };
  trend: TrendPoint[];
  byLine: LineRow[];
  byStop: StopRow[];
};

// "2026-04-01" → "Apr 2026". Parsed as UTC so the day-1 date never rolls back a
// month in a negative-offset timezone.
export const monthLabel = (iso: string | null): string => {
  if (!iso) return "—";
  const d = new Date(`${iso}T00:00:00Z`);
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
};

export const fmtInt = (n: number): string => n.toLocaleString("en-US");
