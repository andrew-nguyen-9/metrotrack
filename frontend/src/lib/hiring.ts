// Hiring data shapes + helpers for the vacancy-trend island and table fallback.
// Authority labels reuse transit.ts (one source of truth).
import { authorityLabel } from "./transit";

export { authorityLabel };

export type VacancyRow = { authority_id: string; as_of: string; open_postings: number };
export type HiringData = {
  asOf: string | null;
  source: { label: string; note: string };
  rows: VacancyRow[];
};

export const authorities = (rows: VacancyRow[]): string[] =>
  [...new Set(rows.map((r) => r.authority_id))].sort();

// Sorted unique snapshot dates — the chart's category axis.
export const snapshotDates = (rows: VacancyRow[]): string[] =>
  [...new Set(rows.map((r) => r.as_of))].sort();

export const rowsFor = (rows: VacancyRow[], authority: string): VacancyRow[] =>
  rows.filter((r) => r.authority_id === authority).sort((a, b) => a.as_of.localeCompare(b.as_of));
