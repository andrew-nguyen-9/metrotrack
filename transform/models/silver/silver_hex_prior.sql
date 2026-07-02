-- Silver prior-vintage hex metrics: jobs + population aggregated to H3 cells from
-- the TOD growth baselines (LODES prior year + 2010 Centers of Population). Mirrors
-- silver_hex_metrics exactly, but reads the *_prior.parquet bronze, so growth is a
-- like-for-like hex comparison of two real vintages — never a synthetic figure
-- (pipeline/census.py, docs/architecture/DATA_SOURCES.md). [v3.10]
--
-- Each vintage is binned to hex by its own block-group centroids, so no decennial
-- block-group boundary change has to be reconciled: the hex geography is fixed and
-- the same on both sides of the diff.
with cenpop as (
    select
        bg_geoid,
        try_cast(population as integer) as population,
        try_cast(lat as double) as lat,
        try_cast(lon as double) as lon
    from read_parquet('{{ var("bronze_dir") }}/{{ var("metro") }}/census/cenpop_bg_prior.parquet')
    where lat is not null and lon is not null
),
jobs as (
    select bg_geoid, sum(try_cast(jobs as integer)) as jobs
    from read_parquet('{{ var("bronze_dir") }}/{{ var("metro") }}/census/lodes_wac_prior.parquet')
    group by bg_geoid
),
bg as (
    select
        h3_latlng_to_cell(c.lat, c.lon, {{ var("h3_res") }}) as h3,
        c.population,
        coalesce(j.jobs, 0) as jobs
    from cenpop c
    left join jobs j using (bg_geoid)
)
select
    '{{ var("metro") }}' as metro_id,
    h3_h3_to_string(h3) as h3,
    sum(jobs) as jobs_prev,
    sum(population) as pop_prev
from bg
group by h3
