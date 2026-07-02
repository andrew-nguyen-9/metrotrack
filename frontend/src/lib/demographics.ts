// Demographic-change data shapes + formatters for the ACS change page (v3.9).
// The island (bucket bar) and the no-JS table fallback both read this.

export type County = {
  year_prior: number;
  year_latest: number;
  pop_prior: number;
  pop_latest: number;
  pop_change: number;
  pop_change_pct: number;
  income_prior: number | null;
  income_latest: number | null;
  income_change: number | null;
};

export type Bucket = { label: string; count: number };
export type Mover = {
  geoid: string;
  pop_prior: number;
  pop_latest: number;
  pop_change: number;
  pop_change_pct: number;
};

export type DemographicsData = {
  vintages: { prior: number; latest: number };
  source: { label: string; note: string; url: string };
  county: County;
  tractTotal: number;
  buckets: Bucket[];
  movers: Mover[];
};

export const fmtInt = (n: number): string => Math.round(n).toLocaleString();
export const fmtSigned = (n: number): string => `${n > 0 ? "+" : ""}${fmtInt(n)}`;
export const fmtPct = (x: number): string => `${x > 0 ? "+" : ""}${x.toFixed(1)}%`;
export const fmtUSD = (n: number | null): string =>
  n == null ? "—" : `$${Math.round(n).toLocaleString()}`;

// Change tone: a demographic shift isn't inherently good/bad, so tone stays muted
// (honest by construction — see hiring.astro). dir is for the redundant arrow only.
export const dir = (n: number): "up" | "down" => (n >= 0 ? "up" : "down");
