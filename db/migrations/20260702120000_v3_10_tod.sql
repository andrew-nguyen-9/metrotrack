-- v3.10 — transit-oriented development: CBD anchors + per-hex TOD mart. [v3.10]
--
-- Two new spine tables, both multi-tenant (metro_id FK) + RLS public-read, writes
-- only via the service role. CBDs are data-driven + multi-district (N per metro).
-- Idempotent: create-if-not-exists + drop/recreate policies (matches db/schema.sql).

create table if not exists public.cbds (
  metro_id    text not null references public.metros(metro_id),
  cbd_id      text not null,
  name        text not null,
  geom        extensions.geometry(Point, 4326),
  as_of       date,
  primary key (metro_id, cbd_id)
);

create table if not exists public.hex_tod (
  metro_id        text   not null references public.metros(metro_id),
  h3              text   not null,
  jobs            integer,
  population      integer,
  jobs_prev       integer,
  pop_prev        integer,
  jobs_growth_pct double precision,
  pop_growth_pct  double precision,
  nearest_cbd_id  text   not null,
  dist_cbd_m      bigint not null,
  min_to_cbd      double precision not null,
  as_of           date,
  source_hash     text,
  primary key (metro_id, h3)
);

create index if not exists cbds_geom_gix
  on public.cbds using gist (geom extensions.gist_geometry_ops_2d);

alter table public.cbds    enable row level security;
alter table public.hex_tod enable row level security;

drop policy if exists "public read cbds"    on public.cbds;
drop policy if exists "public read hex_tod" on public.hex_tod;
create policy "public read cbds" on public.cbds
  for select to anon, authenticated using (true);
create policy "public read hex_tod" on public.hex_tod
  for select to anon, authenticated using (true);
