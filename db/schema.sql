-- MetroTrack — Project A spine (authoritative schema snapshot). [v1.0.2]
--
-- Foundation tables: authorities, routes, stops. PostGIS geometry in SRID 4326
-- (WGS84 lat/lng), GiST spatial indexes, RLS public-read on every table.
--
-- PostGIS lives in the `extensions` schema (Supabase convention — keeps `public`
-- clean for the security advisor's extension_in_public check). The geometry type
-- and the GiST operator class are therefore schema-qualified so DDL resolves
-- regardless of the connection's search_path.
--
-- Writes happen only via the service-role key, which bypasses RLS; anon and
-- authenticated roles get SELECT and nothing else. This file is the snapshot;
-- db/migrations/ holds the timestamped, immutable applied units.

create extension if not exists postgis with schema extensions;

-- ── authorities ───────────────────────────────────────────────────────
-- The transit agencies. Short stable code as PK so GTFS rows join cleanly.
create table if not exists public.authorities (
  id          text primary key,                       -- 'cta' | 'pace' | 'metra'
  name        text not null,
  mode        text not null,                          -- 'bus' | 'rail' | 'multi'
  url         text,
  created_at  timestamptz not null default now()
);

-- ── routes ────────────────────────────────────────────────────────────
-- GTFS routes. route_id is unique only within an authority, hence the composite.
create table if not exists public.routes (
  id            bigint generated always as identity primary key,
  authority_id  text not null references public.authorities(id) on delete cascade,
  route_id      text not null,                         -- GTFS route_id
  short_name    text,
  long_name     text,
  route_type    integer,                               -- GTFS route_type
  color         text,                                  -- hex, no leading '#'
  text_color    text,
  geom          extensions.geometry(MultiLineString, 4326),
  unique (authority_id, route_id)
);

-- ── stops ─────────────────────────────────────────────────────────────
create table if not exists public.stops (
  id            bigint generated always as identity primary key,
  authority_id  text not null references public.authorities(id) on delete cascade,
  stop_id       text not null,                         -- GTFS stop_id
  name          text,
  geom          extensions.geometry(Point, 4326),
  unique (authority_id, stop_id)
);

-- ── hex_metrics ───────────────────────────────────────────────────────
-- Jobs + population aggregated to H3 cells (mapping pillar, v1.1.4). One row per
-- cell; jobs_per_1k_pop is null where a cell has no residents. Polygon geometry.
create table if not exists public.hex_metrics (
  h3              text primary key,                  -- H3 index string; res in `resolution`
  resolution      integer not null,
  jobs            integer not null,
  population      integer not null,
  jobs_per_1k_pop double precision,
  geom            extensions.geometry(Polygon, 4326)
);

-- ── spatial indexes (qualified opclass → search_path-independent) ──────
create index if not exists routes_geom_gix
  on public.routes using gist (geom extensions.gist_geometry_ops_2d);
create index if not exists stops_geom_gix
  on public.stops  using gist (geom extensions.gist_geometry_ops_2d);
create index if not exists hex_metrics_geom_gix
  on public.hex_metrics using gist (geom extensions.gist_geometry_ops_2d);

-- ── RLS: public read; writes only via service role (bypasses RLS) ──────
alter table public.authorities enable row level security;
alter table public.routes      enable row level security;
alter table public.stops       enable row level security;
alter table public.hex_metrics enable row level security;

drop policy if exists "public read authorities" on public.authorities;
drop policy if exists "public read routes"      on public.routes;
drop policy if exists "public read stops"       on public.stops;
drop policy if exists "public read hex_metrics" on public.hex_metrics;

create policy "public read authorities" on public.authorities
  for select to anon, authenticated using (true);
create policy "public read routes" on public.routes
  for select to anon, authenticated using (true);
create policy "public read stops" on public.stops
  for select to anon, authenticated using (true);
create policy "public read hex_metrics" on public.hex_metrics
  for select to anon, authenticated using (true);

-- ── seed: the three Chicagoland GTFS authorities (stable reference data) ─
insert into public.authorities (id, name, mode, url) values
  ('cta',   'Chicago Transit Authority', 'multi', 'https://www.transitchicago.com'),
  ('pace',  'Pace Suburban Bus',         'bus',   'https://www.pacebus.com'),
  ('metra', 'Metra Commuter Rail',       'rail',  'https://metra.com')
on conflict (id) do nothing;

-- ── funding pillar: operating actual (NTD) vs RTA budget/plan [v1.2.4] ──
create table if not exists public.agency_finances (
  authority_id     text    not null,                 -- cta | metra | pace
  fiscal_year      integer not null,
  actual_audited   bigint,                            -- FTA NTD operating expense ($)
  fare_revenue     bigint,                            -- FTA NTD ($)
  unlinked_trips   bigint,                            -- FTA NTD
  rta_kind         text,                              -- actual | estimate | budget | plan
  rta_amount       bigint,                            -- RTA adopted operating budget ($)
  farebox_recovery double precision,                  -- fare_revenue / actual_audited
  primary key (authority_id, fiscal_year)
);

alter table public.agency_finances enable row level security;

drop policy if exists "public read agency_finances" on public.agency_finances;
create policy "public read agency_finances" on public.agency_finances
  for select to anon, authenticated using (true);

-- ── hiring pillar: weekly open-postings snapshots [v1.3.4] ─────────────
create table if not exists public.vacancy_postings (
  authority_id   text    not null,                   -- cta | metra | pace
  as_of          date    not null,
  open_postings  integer not null,
  source_url     text,
  method         text,                               -- taleo | cadient | oracle
  primary key (authority_id, as_of)
);

alter table public.vacancy_postings enable row level security;

drop policy if exists "public read vacancy_postings" on public.vacancy_postings;
create policy "public read vacancy_postings" on public.vacancy_postings
  for select to anon, authenticated using (true);

-- ── access pillar: walkshed job-access score per hex [v1.4.4] ───────────
create table if not exists public.hex_access (
  h3                  text primary key,              -- joins to public.hex_metrics
  jobs_reachable_walk bigint not null,
  walk_radius_m       integer not null
);

alter table public.hex_access enable row level security;

drop policy if exists "public read hex_access" on public.hex_access;
create policy "public read hex_access" on public.hex_access
  for select to anon, authenticated using (true);
