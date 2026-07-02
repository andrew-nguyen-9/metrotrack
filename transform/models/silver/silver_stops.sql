-- Silver stops: one validated point per (authority, stop_id).
-- Reads the content-hashed bronze parquet; authority is derived from the path
-- (data/bronze/<metro>/<authority>/stops.parquet). Coords are SRID 4326 (GTFS is WGS84).
with src as (
    select
        regexp_extract(filename, '/{{ var("metro") }}/([^/]+)/', 1) as authority_id,
        stop_id,
        nullif(stop_name, '') as name,
        try_cast(stop_lon as double) as lon,
        try_cast(stop_lat as double) as lat
    from read_parquet(
        '{{ var("bronze_dir") }}/{{ var("metro") }}/*/stops.parquet',
        filename = true,
        union_by_name = true
    )
),

-- Stop mode is derived per agency from the modes of the routes it runs: a
-- single-mode operator's stops inherit that mode (Metra → commuter-rail, Pace →
-- bus); a multi-mode operator's stops are 'multi' (CTA runs bus + rail from one
-- feed, and splitting a CTA stop bus/rail would need stop_times, out of scope).
authority_modes as (
    select
        authority_id,
        case when count(distinct mode) > 1 then 'multi' else min(mode) end as mode
    from {{ ref('silver_routes') }}
    where metro_id = '{{ var("metro") }}'
    group by authority_id
)

select
    '{{ var("metro") }}' as metro_id,
    src.authority_id,
    src.stop_id,
    src.name,
    coalesce(am.mode, 'other') as mode,
    src.lon,
    src.lat,
    st_point(src.lon, src.lat) as geom
from src
left join authority_modes as am on src.authority_id = am.authority_id
where src.lon is not null and src.lat is not null
qualify row_number() over (partition by src.authority_id, src.stop_id order by src.stop_id) = 1
