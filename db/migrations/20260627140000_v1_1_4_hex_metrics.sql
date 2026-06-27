-- Migration 20260627140000 — v1.1.4 hex metrics (population + jobs choropleth).
--
-- One row per H3 cell over Cook County: jobs, population, derived jobs_per_1k_pop,
-- and the hex polygon (SRID 4326). Mirrors the v1.0 spine conventions: geometry in
-- the extensions schema, qualified GiST opclass, RLS public-read; writes only via
-- the service role (bypasses RLS). Snapshot kept in db/schema.sql.

create table if not exists public.hex_metrics (
  h3              text primary key,                  -- H3 index string; res in `resolution`
  resolution      integer not null,
  jobs            integer not null,
  population      integer not null,
  jobs_per_1k_pop double precision,                  -- null where population = 0
  geom            extensions.geometry(Polygon, 4326)
);

create index if not exists hex_metrics_geom_gix
  on public.hex_metrics using gist (geom extensions.gist_geometry_ops_2d);

alter table public.hex_metrics enable row level security;

drop policy if exists "public read hex_metrics" on public.hex_metrics;
create policy "public read hex_metrics" on public.hex_metrics
  for select to anon, authenticated using (true);
