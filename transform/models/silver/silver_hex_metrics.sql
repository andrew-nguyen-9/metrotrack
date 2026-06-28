-- Silver hex metrics: jobs + population aggregated to H3 cells (res = var h3_res).
--
-- Population comes from the 2020 Centers of Population block-group file, which
-- carries the centroid lat/lng — so each block group maps directly to one H3
-- cell. Jobs (LODES) have no coordinates, so they are summed per block group and
-- ride that block group's centroid cell. H3 cells are equal-area, so a per-cell
-- count reads as density without distortion (docs/phases/v1/v1.1/PLAN.md).
with cenpop as (
    select
        bg_geoid,
        try_cast(population as integer) as population,
        try_cast(lat as double) as lat,
        try_cast(lon as double) as lon
    from read_parquet('{{ var("bronze_dir") }}/{{ var("metro") }}/census/cenpop_bg.parquet')
    where lat is not null and lon is not null
),
jobs as (
    select bg_geoid, sum(try_cast(jobs as integer)) as jobs
    from read_parquet('{{ var("bronze_dir") }}/{{ var("metro") }}/census/lodes_wac.parquet')
    group by bg_geoid
),
bg as (
    select
        h3_latlng_to_cell(c.lat, c.lon, {{ var("h3_res") }}) as h3,
        c.population,
        coalesce(j.jobs, 0) as jobs
    from cenpop c
    left join jobs j using (bg_geoid)
),
agg as (
    select h3, sum(jobs) as jobs, sum(population) as population
    from bg
    group by h3
)
select
    '{{ var("metro") }}' as metro_id,
    h3_h3_to_string(h3) as h3,
    {{ var("h3_res") }} as resolution,
    jobs,
    population
from agg
