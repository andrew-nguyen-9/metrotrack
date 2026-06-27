# ADR-001: Supabase + PostGIS as the data/geo backbone

**Status:** Accepted
**Date:** 2026-06-26
**Deciders:** Andrew Nguyen

---

## Context

The tracker needs (a) a relational store for funding + hiring time series and
(b) live spatial queries for the map (residents/jobs within walking distance of a
stop, service-area coverage). It must run on free/hobby tiers and broaden skills
beyond the existing GCP/BigQuery, Supabase, Neon, Vercel base.

## Decision

Use **Supabase Postgres with the PostGIS extension** as the serving database.
DuckDB handles heavy offline analytics (Census LODES parquet) in `transform/`;
gold tables and geometry are loaded into Supabase for live queries. Large/static
geometry is additionally baked to **PMTiles** for the map.

## Consequences

**Positive:**
- Smallest leap from existing Supabase experience; PostGIS is the new skill.
- Real spatial joins (`ST_DWithin`, `ST_Contains`, `ST_Intersects`) the map needs.
- Row-Level Security gives clean public-read with a protected service role.
- Auto-generated REST/Realtime APIs reduce frontend plumbing.

**Negative:**
- Free-tier row/storage + connection limits — keep gold tables lean; static
  geometry goes to PMTiles, not row storage.
- Spatial query performance needs deliberate GiST indexing.

**Mitigations:**
- Heavy crunching stays in DuckDB; Supabase holds only serving-shaped gold.
- PMTiles offloads big geometry from the DB and from the tile-server cost entirely.
- GiST indexes + H3 hex pre-aggregation keep live queries cheap.

## Alternatives considered

| Alternative | Why not (for v1) |
|---|---|
| Neon + PostGIS | Equivalent spatial skill, but more plumbing (own auth/API layer) and less incremental from current Supabase experience. |
| DuckDB + PMTiles only (no live DB) | Cheapest for read-only, but no live spatial queries and defers the PostGIS skill that's a core goal. Revisit if Supabase limits bite. |
| BigQuery GIS | Already in the skill set; not the broadening this project is for, and weaker fit for a small public app. |
