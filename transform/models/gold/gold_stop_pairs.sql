-- Gold stop pairs (v3.7) — cross-agency service-coordination candidates.
--
-- The PostGIS/geography skill unit: every unordered pair of stops from two
-- *different* agencies whose points fall within a walkable transfer radius is a
-- candidate for a merge / timing alignment. dist_m is a great-circle distance in
-- metres (ST_Distance_Sphere) = the geography distance ST_DWithin(geography, R)
-- filters on in the DB serving layer; we filter on the sphere metre value here
-- (mirrors gold_hex_tod) so the threshold is honest metres, not planar degrees.
--
-- Timing gap: each agency carries a *representative published* headway (seed
-- service_headways, sourced per agency schedule page — NOT real-time / per-stop).
-- The expected uncoordinated transfer wait ≈ the slower leg's headway ÷ 2 (a rider
-- arriving at random waits, on average, half the headway of the service they
-- catch). score blends closeness + timing mismatch, each in [0,1], equal weight —
-- fully transparent, no black box.
--
-- ponytail: O(stops²) self-join, trivial at Chicago sample scale (~40 stops). An
-- H3/ST_DWithin prefilter is the lever only if a metro loads its full stop set.
{% set radius = var('pair_radius_m', 400) %}
with stops as (
    select authority_id, stop_id, name, mode, geom
    from {{ ref('silver_stops') }}
    where metro_id = '{{ var("metro") }}'
),
hw as (select authority_id, headway_min from {{ ref('service_headways') }}),
gap_span as (select max(headway_min) - min(headway_min) as span from hw),
pairs as (
    select
        a.authority_id as authority_a, a.stop_id as stop_a, a.name as name_a, a.mode as mode_a,
        b.authority_id as authority_b, b.stop_id as stop_b, b.name as name_b, b.mode as mode_b,
        ST_Distance_Sphere(a.geom, b.geom) as dist_m,
        ha.headway_min as headway_a,
        hb.headway_min as headway_b
    from stops a
    join stops b on a.authority_id < b.authority_id
    left join hw ha on ha.authority_id = a.authority_id
    left join hw hb on hb.authority_id = b.authority_id
    where ST_Distance_Sphere(a.geom, b.geom) <= {{ radius }}
)
select
    '{{ var("metro") }}' as metro_id,
    p.authority_a, p.stop_a, p.name_a, p.mode_a,
    p.authority_b, p.stop_b, p.name_b, p.mode_b,
    cast(round(p.dist_m) as bigint) as dist_m,
    p.headway_a,
    p.headway_b,
    abs(p.headway_a - p.headway_b) as headway_gap_min,
    round(greatest(p.headway_a, p.headway_b) / 2.0, 1) as wait_min,
    -- closeness: 1 at 0 m → 0 at the radius. mismatch: gap ÷ the widest possible
    -- agency-pair gap (so the worst real mismatch scores 1). equal weight.
    round(
        0.5 * (1 - p.dist_m / {{ radius }}.0)
      + 0.5 * (abs(p.headway_a - p.headway_b)::double / nullif(g.span, 0))
    , 3) as score
from pairs p
cross join gap_span g
order by score desc
