-- MetroTrack — Project A spine (authoritative schema snapshot). [v2.0.2]
--
-- Multi-tenant: every spine table carries a NOT NULL metro_id FK → public.metros
-- (= slug), with collision-prone natural keys scoped to the tenant. PostGIS
-- geometry in SRID 4326 (WGS84 lat/lng), GiST spatial indexes, RLS public-read.
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

-- ── metros ────────────────────────────────────────────────────────────
-- Multi-tenant registry [v2.0.1]. metros/<slug>.toml is the authored truth;
-- sync_metros() (pipeline/load.py) mirrors this serving subset. metro_id = slug =
-- the tenant key v2.0.2 adds to every spine table below.
create table if not exists public.metros (
  metro_id    text primary key,                        -- = slug; tenant key everywhere
  name        text not null,
  slug        text not null unique,
  tz          text not null,                            -- IANA tz; store UTC, render here
  status      text not null default 'soon'
              check (status in ('live', 'soon')),
  bbox        extensions.geometry(Polygon, 4326),       -- metro extent envelope (WGS84)
  as_of       date,
  created_at  timestamptz not null default now()
);

create index if not exists metros_bbox_gix
  on public.metros using gist (bbox extensions.gist_geometry_ops_2d);

alter table public.metros enable row level security;
drop policy if exists "public read metros" on public.metros;
create policy "public read metros" on public.metros
  for select to anon, authenticated using (true);

-- ── authorities ───────────────────────────────────────────────────────
-- The transit agencies. Short stable code as PK so GTFS rows join cleanly. Agency
-- codes are globally unique, so the PK stays single-column; metro_id is a NOT NULL
-- FK tag for per-metro filtering (no composite PK → no composite FK cascade). [B18a]
create table if not exists public.authorities (
  id          text primary key,                       -- 'cta' | 'pace' | 'metra'
  metro_id    text not null references public.metros(metro_id),
  name        text not null,
  mode        text not null,                          -- 'bus' | 'rail' | 'multi'
  url         text,
  created_at  timestamptz not null default now()
);

-- ── routes ────────────────────────────────────────────────────────────
-- GTFS routes. route_id collides across metros, so the unique is tenant-scoped.
create table if not exists public.routes (
  id            bigint generated always as identity primary key,
  metro_id      text not null references public.metros(metro_id),
  authority_id  text not null references public.authorities(id) on delete cascade,
  route_id      text not null,                         -- GTFS route_id
  short_name    text,
  long_name     text,
  route_type    integer,                               -- GTFS route_type
  color         text,                                  -- hex, no leading '#'
  text_color    text,
  geom          extensions.geometry(MultiLineString, 4326),
  as_of         date,                                  -- load date; v2.0.4 refines to source as_of
  source_hash   text,                                  -- gold provenance; populated v2.0.4 [H15a]
  unique (metro_id, authority_id, route_id)
);

-- ── stops ─────────────────────────────────────────────────────────────
create table if not exists public.stops (
  id            bigint generated always as identity primary key,
  metro_id      text not null references public.metros(metro_id),
  authority_id  text not null references public.authorities(id) on delete cascade,
  stop_id       text not null,                         -- GTFS stop_id
  name          text,
  geom          extensions.geometry(Point, 4326),
  as_of         date,
  source_hash   text,
  unique (metro_id, authority_id, stop_id)
);

-- ── hex_metrics ───────────────────────────────────────────────────────
-- Jobs + population aggregated to H3 cells (mapping pillar, v1.1.4). One row per
-- cell; jobs_per_1k_pop is null where a cell has no residents. Polygon geometry.
create table if not exists public.hex_metrics (
  metro_id        text not null references public.metros(metro_id),
  h3              text not null,                     -- H3 index string; res in `resolution`
  resolution      integer not null,
  jobs            integer not null,
  population      integer not null,
  jobs_per_1k_pop double precision,
  geom            extensions.geometry(Polygon, 4326),
  as_of           date,
  source_hash     text,
  primary key (metro_id, h3)                         -- h3 globally unique; metro_id leads for prefix reads
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
insert into public.authorities (id, metro_id, name, mode, url) values
  ('cta',   'chicago', 'Chicago Transit Authority', 'multi', 'https://www.transitchicago.com'),
  ('pace',  'chicago', 'Pace Suburban Bus',         'bus',   'https://www.pacebus.com'),
  ('metra', 'chicago', 'Metra Commuter Rail',       'rail',  'https://metra.com')
on conflict (id) do nothing;

-- ── funding pillar: operating actual (NTD) vs RTA budget/plan [v1.2.4] ──
create table if not exists public.agency_finances (
  metro_id         text    not null references public.metros(metro_id),
  authority_id     text    not null,                 -- cta | metra | pace
  fiscal_year      integer not null,
  actual_audited   bigint,                            -- FTA NTD operating expense ($)
  fare_revenue     bigint,                            -- FTA NTD ($)
  unlinked_trips   bigint,                            -- FTA NTD
  rta_kind         text,                              -- actual | estimate | budget | plan
  rta_amount       bigint,                            -- RTA adopted operating budget ($)
  farebox_recovery double precision,                  -- fare_revenue / actual_audited
  as_of            date,
  source_hash      text,
  primary key (metro_id, authority_id, fiscal_year)
);

alter table public.agency_finances enable row level security;

drop policy if exists "public read agency_finances" on public.agency_finances;
create policy "public read agency_finances" on public.agency_finances
  for select to anon, authenticated using (true);

-- ── hiring pillar: weekly open-postings snapshots [v1.3.4] ─────────────
create table if not exists public.vacancy_postings (
  metro_id       text    not null references public.metros(metro_id),
  authority_id   text    not null,                   -- cta | metra | pace
  as_of          date    not null,
  open_postings  integer not null,
  source_url     text,
  method         text,                               -- taleo | cadient | oracle
  source_hash    text,
  primary key (metro_id, authority_id, as_of)
);

alter table public.vacancy_postings enable row level security;

drop policy if exists "public read vacancy_postings" on public.vacancy_postings;
create policy "public read vacancy_postings" on public.vacancy_postings
  for select to anon, authenticated using (true);

-- ── access pillar: walkshed job-access score per hex [v1.4.4] ───────────
create table if not exists public.hex_access (
  metro_id            text not null references public.metros(metro_id),
  h3                  text not null,                 -- joins to public.hex_metrics (metro_id, h3)
  jobs_reachable_walk bigint not null,
  walk_radius_m       integer not null,
  as_of               date,
  source_hash         text,
  primary key (metro_id, h3)
);

alter table public.hex_access enable row level security;

drop policy if exists "public read hex_access" on public.hex_access;
create policy "public read hex_access" on public.hex_access
  for select to anon, authenticated using (true);
