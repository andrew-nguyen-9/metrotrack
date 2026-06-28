-- Migration 20260627120000 — v1.0.2 foundation spine (authorities, routes, stops).
-- Immutable applied unit. Content mirrors db/schema.sql at v1.0.2.

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

-- ── spatial indexes (qualified opclass → search_path-independent) ──────
create index if not exists routes_geom_gix
  on public.routes using gist (geom extensions.gist_geometry_ops_2d);
create index if not exists stops_geom_gix
  on public.stops  using gist (geom extensions.gist_geometry_ops_2d);

-- ── RLS: public read; writes only via service role (bypasses RLS) ──────
alter table public.authorities enable row level security;
alter table public.routes      enable row level security;
alter table public.stops       enable row level security;

drop policy if exists "public read authorities" on public.authorities;
drop policy if exists "public read routes"      on public.routes;
drop policy if exists "public read stops"       on public.stops;

create policy "public read authorities" on public.authorities
  for select to anon, authenticated using (true);
create policy "public read routes" on public.routes
  for select to anon, authenticated using (true);
create policy "public read stops" on public.stops
  for select to anon, authenticated using (true);

-- ── seed: the three Chicagoland GTFS authorities (stable reference data) ─
insert into public.authorities (id, name, mode, url) values
  ('cta',   'Chicago Transit Authority', 'multi', 'https://www.transitchicago.com'),
  ('pace',  'Pace Suburban Bus',         'bus',   'https://www.pacebus.com'),
  ('metra', 'Metra Commuter Rail',       'rail',  'https://metra.com')
on conflict (id) do nothing;
