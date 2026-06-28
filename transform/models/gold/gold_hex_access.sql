-- Gold hex access: straight-line walkshed job-access score per hex (the v1.4 signature
-- metric, no-key path). For each hex, sum the jobs in every hex whose centroid is
-- within walk_radius_m (great-circle) of this hex's centroid — an honest approximation
-- of ½-mi walk access (docs/modeling/ACCESS_SCORE.md G5). ORS network isochrones refine
-- this when ORS_API_KEY is set (pipeline/access.py); no synthetic figure is published.
--
-- Each hex's own centroid is within radius of itself, so jobs_reachable_walk always
-- includes the hex's own jobs.
-- ponytail: O(n²) centroid self-join — fine at sample scale (~1.9k hexes). Add a
-- spatial index / H3 k-ring prefilter if this scales to the full region.
with h as (
    select
        metro_id,
        h3,
        jobs,
        ST_Centroid(ST_GeomFromText(geom_wkt)) as c
    from {{ ref('gold_hex_metrics') }}
)
select
    a.metro_id,
    a.h3,
    cast(sum(b.jobs) as bigint) as jobs_reachable_walk,
    {{ var('walk_radius_m') }} as walk_radius_m
from h as a
join h as b on a.metro_id = b.metro_id
    and ST_Distance_Sphere(a.c, b.c) <= {{ var('walk_radius_m') }}
group by a.metro_id, a.h3
