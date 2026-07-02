-- Gold hex TOD: the transit-oriented-development serving mart (v3.10). One row per
-- hex carrying the three TOD signals:
--   • density  — current jobs + population (equal-area H3 → count reads as density);
--   • growth   — jobs & population change vs the prior vintage (silver_hex_prior),
--                as a signed percent (null where the prior cell had none);
--   • time-to-CBD — straight-line distance to the *nearest* configured CBD and a
--                best-case minute estimate at the nominal cbd_speed_kmh.
--
-- Nearest-CBD is computed against the full data-driven CBD set (silver_cbds), so a
-- metro with N districts (future NYC/SF Bay) works with zero code change — the
-- min-distance window just ranks over more anchors.
-- ponytail: O(hexes × CBDs) sphere-distance cross join — trivial at Chicago scale
-- (~1.9k hexes × 1 CBD). An H3/spatial prefilter is the lever if a metro declares
-- many CBDs over a much larger hex grid.
--
-- The minute estimate is a crow-flies FLOOR on real travel time (the routed path is
-- longer); ORS network isochrones refine it when ORS_API_KEY is set (pipeline/access.py).
-- No synthetic figure is published — distance is exact; the minute label says "best-case".
with hex as (
    select
        metro_id,
        h3,
        jobs,
        population,
        ST_Centroid(ST_GeomFromText(geom_wkt)) as c
    from {{ ref('gold_hex_metrics') }}
),
cbd as (
    select metro_id, cbd_id, ST_Point(lon, lat) as p
    from {{ ref('silver_cbds') }}
),
nearest as (
    select
        h.metro_id,
        h.h3,
        c.cbd_id as nearest_cbd_id,
        ST_Distance_Sphere(h.c, c.p) as dist_m,
        row_number() over (
            partition by h.metro_id, h.h3
            order by ST_Distance_Sphere(h.c, c.p)
        ) as rn
    from hex h
    join cbd c on c.metro_id = h.metro_id
)
select
    h.metro_id,
    h.h3,
    h.jobs,
    h.population,
    p.jobs_prev,
    p.pop_prev,
    case when p.jobs_prev > 0
         then round(100.0 * (h.jobs - p.jobs_prev) / p.jobs_prev, 1) end as jobs_growth_pct,
    case when p.pop_prev > 0
         then round(100.0 * (h.population - p.pop_prev) / p.pop_prev, 1) end as pop_growth_pct,
    n.nearest_cbd_id,
    cast(round(n.dist_m) as bigint) as dist_cbd_m,
    round(n.dist_m / 1000.0 / {{ var('cbd_speed_kmh') }} * 60.0, 1) as min_to_cbd
from hex h
join nearest n on n.metro_id = h.metro_id and n.h3 = h.h3 and n.rn = 1
left join {{ ref('silver_hex_prior') }} p on p.metro_id = h.metro_id and p.h3 = h.h3
