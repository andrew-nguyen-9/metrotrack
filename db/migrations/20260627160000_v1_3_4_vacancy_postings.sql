-- Migration 20260627160000 — v1.3.4 vacancy postings (hiring pillar).
--
-- Append-only weekly snapshot of open job postings per service board. One row per
-- authority × date; the weekly cron upserts new dates. Mirrors the spine conventions:
-- RLS public-read, writes only via the direct-Postgres role. Snapshot in db/schema.sql.

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
