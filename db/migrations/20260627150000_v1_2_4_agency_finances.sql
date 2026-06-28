-- Migration 20260627150000 — v1.2.4 agency finances (funding pillar).
--
-- One row per service board × fiscal year: audited operating expense + fare revenue
-- + trips (FTA NTD), the RTA adopted budget/plan figure tagged by kind, and derived
-- farebox recovery. Mirrors the v1.0/v1.1 spine conventions: RLS public-read, writes
-- only via the direct-Postgres role (bypasses RLS). Snapshot kept in db/schema.sql.

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
