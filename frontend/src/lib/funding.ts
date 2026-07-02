// Funding data shapes + formatters for the chart island and the table fallback.
// Authority labels are reused from transit.ts (one source of truth, no dup).
import { authorityLabel } from "./transit";

export { authorityLabel };

export type FundingRow = {
  authority_id: string;
  fiscal_year: number;
  actual_audited: number | null;
  fare_revenue: number | null;
  unlinked_trips: number | null;
  rta_kind: string | null;
  rta_amount: number | null;
  farebox_recovery: number | null;
  subsidy: number | null;
  subsidy_per_rider: number | null;
  cost_per_rider: number | null;
};

export type FundingSource = { label: string; asOf: string; url: string };
export type FundingData = {
  sources: { actual: FundingSource; rta: FundingSource };
  rows: FundingRow[];
};

// The RTA presents one column per year; the kind says what that column truly is,
// so a forward "plan" is never mislabeled as an adopted budget (honest by construction).
export const RTA_KIND_LABELS: Record<string, string> = {
  actual: "actual",
  estimate: "estimate",
  budget: "adopted budget",
  plan: "plan",
};

export const SERIES_LABELS = {
  actual: "Actual operating expense (audited)",
  rta: "RTA budget / plan",
} as const;

// Compact USD for axis ticks + tooltips. Two sig-figs at billions, whole millions.
export const fmtUSD = (n: number): string => {
  const abs = Math.abs(n);
  if (abs >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `$${Math.round(n / 1e6).toLocaleString()}M`;
  return `$${Math.round(n).toLocaleString()}`;
};

export const fmtPct = (x: number): string => `${(x * 100).toFixed(1)}%`;

// Per-rider dollars land in the single/low-double digits, so cents matter.
export const fmtUSD2 = (n: number): string => `$${n.toFixed(2)}`;

// The efficiency-trend chart plots one NTD-internal ratio at a time across years,
// one line per service board. Each metric names its accessor + formatter + axis so
// the island stays generic (no per-metric branching in the component).
export type TrendMetricKey = "farebox_recovery" | "subsidy_per_rider" | "cost_per_rider";

export const TREND_METRICS: Record<TrendMetricKey, {
  label: string;
  axis: string;
  fmt: (n: number) => string;
  isPct?: boolean;
}> = {
  farebox_recovery: {
    label: "Farebox recovery",
    axis: "Fare revenue ÷ operating expense",
    fmt: fmtPct,
    isPct: true,
  },
  subsidy_per_rider: {
    label: "Subsidy per rider",
    axis: "Public subsidy ÷ trip ($)",
    fmt: fmtUSD2,
  },
  cost_per_rider: {
    label: "Cost per rider",
    axis: "Operating expense ÷ trip ($)",
    fmt: fmtUSD2,
  },
};

// Years for which NTD audited actuals exist (a metric value is present).
export const trendYears = (rows: FundingRow[]): number[] =>
  [...new Set(rows.filter((r) => r.actual_audited != null).map((r) => r.fiscal_year))]
    .sort((a, b) => a - b);

export const authorities = (rows: FundingRow[]): string[] =>
  [...new Set(rows.map((r) => r.authority_id))].sort();

export const rowsFor = (rows: FundingRow[], authority: string): FundingRow[] =>
  rows.filter((r) => r.authority_id === authority).sort((a, b) => a.fiscal_year - b.fiscal_year);
