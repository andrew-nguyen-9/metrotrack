-- Silver stops: one validated point per (authority, stop_id).
-- Reads the content-hashed bronze parquet; authority is derived from the path
-- (data/bronze/<authority>/stops.parquet). Coords are SRID 4326 (GTFS is WGS84).
with src as (
    select
        regexp_extract(filename, 'bronze/([^/]+)/', 1) as authority_id,
        stop_id,
        nullif(stop_name, '') as name,
        try_cast(stop_lon as double) as lon,
        try_cast(stop_lat as double) as lat
    from read_parquet(
        '{{ var("bronze_dir") }}/*/stops.parquet',
        filename = true,
        union_by_name = true
    )
)

select
    authority_id,
    stop_id,
    name,
    lon,
    lat,
    st_point(lon, lat) as geom
from src
where lon is not null and lat is not null
qualify row_number() over (partition by authority_id, stop_id order by stop_id) = 1
