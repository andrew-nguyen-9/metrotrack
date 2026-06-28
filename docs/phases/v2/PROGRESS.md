# v2 — Progress Ledger

The autonomous loop's single source of truth for **what's done and what's next**
`[K10a, K11a]`. A fresh session reads this top-to-bottom, picks the **first metro
whose status is `pending` and whose prerequisites are `done`**, works it via
[`LOOP_PROMPT.md`](LOOP_PROMPT.md), then updates the row. No shared chat memory —
this file *is* the handoff `[K16a]`.

**Editing rule:** update only the row you worked + the activity log. Keep it a diff,
not a rewrite. Statuses: `pending` · `in-progress` · `blocked` · `review` (PR open,
awaiting human) · `done`.

---

## Phase segments (build the machine first)

| Segment | What | Status | PR | Notes |
|---|---|---|---|---|
| v2.0 | Multi-tenant foundation | in-progress | — | v2.0.5 done (`[metro]` routing, Chicago migrated, `/`→`/chicago`); resume v2.0.6 → nightly orchestration + golden-test GATE (closes v2.0). **BLOCKER for v2.0.6:** Vercel SSO Deployment Protection 302s anon/headless requests, so the Lighthouse-on-preview gate can't run — needs a preview-protection bypass or disable |
| v2.1 | Site shell, pages & SEO | pending | — | needs v2.0 |
| v2.2 | RSS / regional feeds | pending | — | needs v2.0 |
| v2.3 | Metro onboarding: **SF** | pending | — | first add-a-metro; needs v2.1 |
| v2.4 | Metro onboarding: **NYC** | pending | — | validate walkshed/tile budget first; needs v2.3 |
| v2.5 | Modeling depth (Chicago-first) | pending | — | parallel-safe after v2.0 |
| v2.6 | Autonomous loop + rollout | pending | — | grinds metros below; needs v2.3 |

## Metro rollout (the loop's queue)

Order is the locked wave `[C1a]`. A metro is **`done`** only at full parity — map +
funding + hiring + job-access `[A4a]`, degrading gracefully where a source is missing
`[A7a]`. v2 closes with **Chicago + SF + NYC live** `[A2a]`; the rest grind via the
loop and show greyed "coming soon" until parity `[C12a]`.

| Wave | Metro | slug | Status | PR | Prereq | Parity notes |
|---|---|---|---|---|---|---|
| 0 | Chicago | `chicago` | pending→(v2.0 golden) | — | v2.0 | reference impl; must stay green |
| 1 | San Francisco / Bay Area | `sf` | pending | — | v2.3 | multi-agency: BART, Muni, Caltrain, AC Transit, ferries, + regional rail `[C2,C5a]` |
| 1 | New York | `nyc` | pending | — | v2.4 | MTA-scale; validate O(n²) walkshed + tile cap **first** `[C4a,H10a]` |
| 2 | Washington DC | `dc` | pending | — | loop | WMATA + commuter rail |
| 2 | Boston | `boston` | pending | — | loop | MBTA |
| 3 | Los Angeles | `la` | pending | — | loop | LA Metro |
| 3 | Philadelphia | `philly` | pending | — | loop | SEPTA |
| 4 | Seattle | `seattle` | pending | — | loop | Sound Transit + King County Metro |
| 4 | Atlanta | `atlanta` | pending | — | loop | MARTA |

> Cities beyond the 9 are chosen later from demand signals (search/feed/analytics)
> `[C13a]`. International is out of scope, noted for v3 `[C14a]`.

## Per-metro parity checklist (the loop's definition of `done`)

A metro flips to `done` only when **all** pass and evidence is attached to its PR
`[K21a]`:

- [ ] `metros/<slug>.toml` authored + `sync_metros()` upserts the row.
- [ ] `python -m pipeline.<x> --metro=<slug> --dry-run` clean (feeds + geo) `[H20a]`.
- [ ] Full pipeline run: bronze receipts under `data/bronze/<slug>/`, gold upserted.
- [ ] `dbt build --vars '{metro: <slug>}'` green incl. tests.
- [ ] `tiles/<slug>.pmtiles` within size cap `[I4]`.
- [ ] `/<slug>/*` pages render at a Vercel preview; nav + switcher + theme work.
- [ ] `pipeline/checks.verify_metro('<slug>')` passes — every figure → a source row,
      freshness floor met `[K6a]`.
- [ ] Lighthouse ≥90 mobile (perf + a11y), verified at 360/768/1280/1920 `[E12a]`.
- [ ] First feed items emitted ("now tracking <metro>") `[F9a]`.
- [ ] `DATA_SOURCES.md` rows added for the metro's feeds `[H16a]`.
- [ ] PR opened with screenshots + Lighthouse + integrity log; **not** merged to main.

---

## Activity log

Append one line per unit. Newest at top. Format:
`YYYY-MM-DD · <slug or segment> · <status> · <one line> · <PR/branch>`

- 2026-06-28 · v2.0.5 · done · Astro `[metro]/{index,map,funding,hiring,job-access}` via getStaticPaths from generated metros.json; islands take metro prop; data→`src/data/chicago/`; `/`→`/chicago` 301. npm build 5 routes, astro check 0 errors, emitted-HTML parity (funding/hiring/map figures match v1), job-access degrades gracefully. Live-preview Lighthouse blocked by Vercel SSO (verified on byte-identical local artifact) · v2
- 2026-06-28 · v2.0.4 · done · dbt silver+gold carry metro_id via var('metro'); bronze path+authority regex re-anchored on the metro segment; composite-unique + non-null-metro_id tests. dbt build PASS=65, gold counts identical to a main baseline (24/881/1934/1934/18/3); load.py reads gold.metro_id w/ disagreement guard · v2
- 2026-06-28 · v2.0.3 · done · pipeline `--metro` + `--dry-run` across 8 modules (cli.py helper), per-metro bronze `data/bronze/chicago/` (git mv, bytes preserved), feeds/FIPS/NTD/ATS from toml not hardcoded; selftest 30/30, chicago dry-run feeds 200 + geo valid, bogus slug exits 1. Interim: dbt build fails until v2.0.4 rewires bronze path+regex · v2
- 2026-06-28 · v2.0.2 · done · metro_id NOT NULL FK on 7 spine tables, composite tenant keys, as_of/source_hash provenance; applied to Project A, advisors clean, counts unchanged (auth 3/3 chicago, rest 0); load.py --metro; selftest 24/24 · v2
- 2026-06-27 · v2.0.1 · done · metros registry table + chicago.toml authored truth; selftest 24/24, security advisors clean · v2
- 2026-06-27 · v2 · seeded · phase folder + LOOP_PROMPT + ledger created · main
