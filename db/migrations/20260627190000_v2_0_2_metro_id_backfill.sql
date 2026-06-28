-- v2.0.2 — metro_id backfill onto the v1 spine. [B17a, B18a, H15a]
--
-- Turns the single-metro (Chicago-implicit) spine into a multi-tenant one. Every
-- spine table gains a NOT NULL `metro_id` FK → public.metros, backfilled to
-- 'chicago' (the only metro that exists). Natural keys that collide across metros
-- (GTFS route_id/stop_id, the (authority,period) finance/vacancy keys, h3 cells)
-- become composite, tenant-scoped. Provenance columns (as_of, source_hash) land
-- here so v2.0.4's gold reload has somewhere to write "data as of" + integrity.
--
-- Additive + ordered: ADD nullable → UPDATE backfill → SET NOT NULL, so the
-- constraint never rejects an existing row mid-migration. No v1 column is dropped.
--
-- Deviation [B18a]: authorities keeps its single-column PK (id). Agency codes are
-- globally unique by construction and routes/stops already FK to authorities(id);
-- a composite PK here would force composite FKs everywhere for no collision-safety
-- gain. metro_id still lands as a NOT NULL FK tag for direct per-metro filtering.

-- ── authorities ───────────────────────────────────────────────────────
alter table public.authorities add column if not exists metro_id text;
update public.authorities set metro_id = 'chicago' where metro_id is null;
alter table public.authorities alter column metro_id set not null;
alter table public.authorities
  add constraint authorities_metro_id_fkey
  foreign key (metro_id) references public.metros(metro_id);

-- ── routes ────────────────────────────────────────────────────────────
alter table public.routes add column if not exists metro_id    text;
alter table public.routes add column if not exists as_of       date;  -- load date; v2.0.4 refines to source as_of
alter table public.routes add column if not exists source_hash text;  -- gold provenance; populated v2.0.4 [H15a]
update public.routes set metro_id = 'chicago' where metro_id is null;
alter table public.routes alter column metro_id set not null;
alter table public.routes
  add constraint routes_metro_id_fkey
  foreign key (metro_id) references public.metros(metro_id);
-- GTFS route_id collides across metros → scope the unique to the tenant. [B18a]
alter table public.routes drop constraint routes_authority_id_route_id_key;
alter table public.routes
  add constraint routes_metro_authority_route_key
  unique (metro_id, authority_id, route_id);

-- ── stops ─────────────────────────────────────────────────────────────
alter table public.stops add column if not exists metro_id    text;
alter table public.stops add column if not exists as_of       date;
alter table public.stops add column if not exists source_hash text;
update public.stops set metro_id = 'chicago' where metro_id is null;
alter table public.stops alter column metro_id set not null;
alter table public.stops
  add constraint stops_metro_id_fkey
  foreign key (metro_id) references public.metros(metro_id);
alter table public.stops drop constraint stops_authority_id_stop_id_key;
alter table public.stops
  add constraint stops_metro_authority_stop_key
  unique (metro_id, authority_id, stop_id);

-- ── hex_metrics ───────────────────────────────────────────────────────
alter table public.hex_metrics add column if not exists metro_id    text;
alter table public.hex_metrics add column if not exists as_of       date;
alter table public.hex_metrics add column if not exists source_hash text;
update public.hex_metrics set metro_id = 'chicago' where metro_id is null;
alter table public.hex_metrics alter column metro_id set not null;
alter table public.hex_metrics
  add constraint hex_metrics_metro_id_fkey
  foreign key (metro_id) references public.metros(metro_id);
-- h3 is globally unique, but lead the PK with metro_id so per-metro reads hit the index prefix.
alter table public.hex_metrics drop constraint hex_metrics_pkey;
alter table public.hex_metrics add primary key (metro_id, h3);

-- ── hex_access ────────────────────────────────────────────────────────
alter table public.hex_access add column if not exists metro_id    text;
alter table public.hex_access add column if not exists as_of       date;
alter table public.hex_access add column if not exists source_hash text;
update public.hex_access set metro_id = 'chicago' where metro_id is null;
alter table public.hex_access alter column metro_id set not null;
alter table public.hex_access
  add constraint hex_access_metro_id_fkey
  foreign key (metro_id) references public.metros(metro_id);
alter table public.hex_access drop constraint hex_access_pkey;
alter table public.hex_access add primary key (metro_id, h3);

-- ── agency_finances ───────────────────────────────────────────────────
alter table public.agency_finances add column if not exists metro_id    text;
alter table public.agency_finances add column if not exists as_of       date;
alter table public.agency_finances add column if not exists source_hash text;
update public.agency_finances set metro_id = 'chicago' where metro_id is null;
alter table public.agency_finances alter column metro_id set not null;
alter table public.agency_finances
  add constraint agency_finances_metro_id_fkey
  foreign key (metro_id) references public.metros(metro_id);
alter table public.agency_finances drop constraint agency_finances_pkey;
alter table public.agency_finances add primary key (metro_id, authority_id, fiscal_year);

-- ── vacancy_postings ──────────────────────────────────────────────────
-- as_of already exists (it's the snapshot date); only source_hash is missing.
alter table public.vacancy_postings add column if not exists metro_id    text;
alter table public.vacancy_postings add column if not exists source_hash text;
update public.vacancy_postings set metro_id = 'chicago' where metro_id is null;
alter table public.vacancy_postings alter column metro_id set not null;
alter table public.vacancy_postings
  add constraint vacancy_postings_metro_id_fkey
  foreign key (metro_id) references public.metros(metro_id);
alter table public.vacancy_postings drop constraint vacancy_postings_pkey;
alter table public.vacancy_postings add primary key (metro_id, authority_id, as_of);

-- RLS is unchanged: every table already had public-read enabled in v1; adding
-- columns/keys doesn't alter policies. No new table → no new policy needed.
