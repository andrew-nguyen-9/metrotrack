-- Gold routes: serving shape for the Supabase spine (public.routes).
-- Geometry as WKT so the loader inserts via ST_GeomFromText(.., 4326).
select
    metro_id,
    authority_id,
    route_id,
    short_name,
    long_name,
    route_type,
    mode,
    color,
    text_color,
    st_astext(geom) as geom_wkt
from {{ ref('silver_routes') }}
where geom is not null and not st_isempty(geom)
