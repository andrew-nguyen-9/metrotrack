-- Data-integrity gate (DEFINITION_OF_DONE): hex polygons must be ST_IsValid before
-- they load to PostGIS / tile. Returns offending cells → dbt test fails if any.
select h3
from {{ ref('gold_hex_metrics') }}
where geom_wkt is null or not st_isvalid(st_geomfromtext(geom_wkt))
