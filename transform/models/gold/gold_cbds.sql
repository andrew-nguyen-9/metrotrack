-- Gold CBDs: the serving shape for the Supabase spine + TOD export. Point geometry
-- as WKT (SRID 4326), same convention as gold_stops. One row per (metro, cbd). [v3.10]
select
    metro_id,
    cbd_id,
    name,
    lat,
    lon,
    ST_AsText(ST_Point(lon, lat)) as geom_wkt
from {{ ref('silver_cbds') }}
