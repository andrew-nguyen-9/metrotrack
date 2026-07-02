// Service-coordination candidates (v3.7) — shapes for stop_pairs.json, produced by
// pipeline/stop_pairs_export.py from the gold_stop_pairs PostGIS/geography mart.
// Distance is a great-circle metre value; headways are representative published
// figures per agency (NOT real-time) — see docs/architecture/DATA_SOURCES.md.

export type Headway = {
  authority_id: string;
  headwayMin: number;
  service: string;
  sourceUrl: string;
};

// One ranked cross-agency pair. authority_a < authority_b (stable ordering).
export type StopPair = {
  authority_a: string;
  stop_a: string;
  name_a: string;
  mode_a: string;
  authority_b: string;
  stop_b: string;
  name_b: string;
  mode_b: string;
  dist_m: number;
  headway_a: number;
  headway_b: number;
  headway_gap_min: number;
  wait_min: number;
  score: number;
  rationale: string;
};

export type CoordinationData = {
  asOf: string;
  radiusM: number;
  candidateCount: number;
  shown: number;
  headways: Headway[];
  pairs: StopPair[];
};
