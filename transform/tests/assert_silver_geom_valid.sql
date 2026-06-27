-- Data-integrity gate (DEFINITION_OF_DONE): geometries must be ST_IsValid before
-- they can load. Returns offending rows → dbt test fails if any geometry is bad.
select 'stop' as kind, authority_id, stop_id as id
from {{ ref('silver_stops') }}
where geom is null or not st_isvalid(geom)

union all

select 'route' as kind, authority_id, route_id as id
from {{ ref('silver_routes') }}
where geom is not null and not st_isvalid(geom)
