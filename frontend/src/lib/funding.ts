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

export const authorities = (rows: FundingRow[]): string[] =>
  [...new Set(rows.map((r) => r.authority_id))].sort();

export const rowsFor = (rows: FundingRow[], authority: string): FundingRow[] =>
  rows.filter((r) => r.authority_id === authority).sort((a, b) => a.fiscal_year - b.fiscal_year);
