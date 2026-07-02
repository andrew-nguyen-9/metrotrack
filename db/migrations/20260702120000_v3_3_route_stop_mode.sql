-- Migration 20260702120000 — v3.3 route/stop mode dimension (transit coverage).
--
-- Adds a normalized `mode` column to public.routes + public.stops so the map and
-- E3b can filter by mode (bus / rail / commuter-rail) alongside authority_id.
-- Derived in dbt from GTFS route_type (macro route_mode); stops inherit their
-- agency's route modes ('multi' for a multi-mode operator like CTA). Idempotent:
-- add-if-not-exists, no data rewrite. RLS is unchanged — these are existing
-- public-read tables; a new column inherits the table's row policy.

alter table public.routes add column if not exists mode text;  -- bus|rail|commuter-rail|other
alter table public.stops  add column if not exists mode text;  -- +multi (multi-mode agency)
