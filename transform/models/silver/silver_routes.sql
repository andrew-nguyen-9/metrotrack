-- Silver routes: GTFS routes with geometry stitched from shapes.
-- shapes → per-shape LINESTRING (points ordered by sequence) → per-route
-- MULTILINESTRING via the trips route_id↔shape_id link. SRID 4326 (GTFS is WGS84).
with shape_pts as (
    select
        regexp_extract(filename, '/{{ var("metro") }}/([^/]+)/', 1) as authority_id,
        shape_id,
        st_point(try_cast(shape_pt_lon as double), try_cast(shape_pt_lat as double)) as pt,
        try_cast(shape_pt_sequence as integer) as seq
    from read_parquet(
        '{{ var("bronze_dir") }}/{{ var("metro") }}/*/shapes.parquet',
        filename = true,
        union_by_name = true
    )
    where try_cast(shape_pt_lon as double) is not null
      and try_cast(shape_pt_lat as double) is not null
),

shape_lines as (
    select
        authority_id,
        shape_id,
        st_makeline(list(pt order by seq)) as geom
    from shape_pts
    group by authority_id, shape_id
    having count(*) >= 2  -- ST_MakeLine needs at least two points
),

route_shapes as (
    select distinct
        regexp_extract(filename, '/{{ var("metro") }}/([^/]+)/', 1) as authority_id,
        route_id,
        shape_id
    from read_parquet(
        '{{ var("bronze_dir") }}/{{ var("metro") }}/*/trips.parquet',
        filename = true,
        union_by_name = true
    )
    where nullif(shape_id, '') is not null
),

routes_base as (
    select
        regexp_extract(filename, '/{{ var("metro") }}/([^/]+)/', 1) as authority_id,
        route_id,
        nullif(route_short_name, '') as short_name,
        nullif(route_long_name, '') as long_name,
        try_cast(route_type as integer) as route_type,
        nullif(route_color, '') as color,
        nullif(route_text_color, '') as text_color
    from read_parquet(
        '{{ var("bronze_dir") }}/{{ var("metro") }}/*/routes.parquet',
        filename = true,
        union_by_name = true
    )
)

select
    '{{ var("metro") }}' as metro_id,
    rb.authority_id,
    rb.route_id,
    rb.short_name,
    rb.long_name,
    rb.route_type,
    {{ route_mode('rb.route_type') }} as mode,
    rb.color,
    rb.text_color,
    st_collect(list(sl.geom) filter (where sl.geom is not null)) as geom
from routes_base as rb
left join route_shapes as rs
    on rb.authority_id = rs.authority_id and rb.route_id = rs.route_id
left join shape_lines as sl
    on rs.authority_id = sl.authority_id and rs.shape_id = sl.shape_id
group by all
