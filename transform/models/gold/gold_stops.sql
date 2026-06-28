-- Gold stops: serving shape for the Supabase spine (public.stops).
-- Geometry as WKT so the loader inserts via ST_GeomFromText(.., 4326).
select
    metro_id,
    authority_id,
    stop_id,
    name,
    st_astext(geom) as geom_wkt
from {{ ref('silver_stops') }}
