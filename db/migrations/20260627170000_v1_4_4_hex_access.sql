-- Migration 20260627170000 — v1.4.4 hex access (job-access score).
--
-- One row per H3 cell: jobs reachable within a walk radius (straight-line walkshed,
-- the v1.4 no-ORS-key metric; ORS network isochrones refine it when configured).
-- Mirrors the spine conventions: RLS public-read, writes via the direct-Postgres role.
-- Snapshot in db/schema.sql.

create table if not exists public.hex_access (
  h3                  text primary key,              -- joins to public.hex_metrics
  jobs_reachable_walk bigint not null,
  walk_radius_m       integer not null
);

alter table public.hex_access enable row level security;

drop policy if exists "public read hex_access" on public.hex_access;
create policy "public read hex_access" on public.hex_access
  for select to anon, authenticated using (true);
