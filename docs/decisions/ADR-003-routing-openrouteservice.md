# ADR-003: openrouteservice for travel-time + isochrones

**Status:** Accepted
**Date:** 2026-06-27
**Deciders:** Andrew Nguyen

---

## Context

The job-access score (`../modeling/ACCESS_SCORE.md`) and the map's access
visualization need street/walk routing + isochrone polygons. Questionnaire G1 picked
openrouteservice over self-hosting Valhalla/OSRM or a GTFS-only graph.

## Decision

Use **openrouteservice (ORS) hosted free API** for walk/street routing + isochrones.
Transit legs come from GTFS. **Precompute** the ambient per-hex access layer in the
nightly pipeline (batch + cache); call ORS **live only** for on-demand point clicks,
cached by rounded coordinate + cutoff + departure.

## Consequences

**Positive:**
- Zero infra to run; free tier covers a hobby workload if we precompute.
- Good isochrone + matrix endpoints, exactly the shapes the access model needs.

**Negative:**
- Free-tier rate/quota limits — a naive per-hex live call would blow them instantly.
- ORS is street-network; **transit routing still needs a GTFS router** (r5py /
  OpenTripPlanner) — ORS alone doesn't do schedule-aware transit trips.

**Mitigations:**
- Batch-precompute hex access nightly; cache aggressively; coarsen H3 resolution if
  quota is tight.
- The GTFS transit-leg integration is the **v1.4 spike** — evaluate r5py vs OTP vs
  ORS public-transport mode before committing the routing topology.

## Alternatives considered

| Alternative | Why not (for v1) |
|---|---|
| Self-host Valhalla / OSRM | More control + no quota, but infra to run/maintain; against the free/zero-ops goal. Revisit if ORS quota bites. |
| GTFS-only graph (no street routing) | No walk access/egress realism; weaker access score. |

Revisit (→ self-host) if free-tier quota proves insufficient even with precompute.
