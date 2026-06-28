-- v2.0.1 — metros registry table. [B2c, B6a, B9a]
--
-- The metros/<slug>.toml files are the authored source of truth; this table
-- mirrors the serving subset (sync_metros() in pipeline/load.py upserts it) for
-- SQL joins + Astro getStaticPaths. metro_id = slug = the tenant key that v2.0.2
-- adds to every spine table. RLS public-read like the rest of the spine; writes
-- only via the service role (bypasses RLS). PostGIS lives in `extensions`.

create table if not exists public.metros (
  metro_id    text primary key,                        -- = slug; tenant key everywhere
  name        text not null,
  slug        text not null unique,
  tz          text not null,                            -- IANA tz; store UTC, render here [B15a]
  status      text not null default 'soon'
              check (status in ('live', 'soon')),       -- soon = greyed "coming soon" [C12a]
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
