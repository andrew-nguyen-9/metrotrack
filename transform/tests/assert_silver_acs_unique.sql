-- (metro_id, geo_level, geoid) must be unique in the silver change model.
select metro_id, geo_level, geoid, count(*) as n
from {{ ref('silver_acs_change') }}
group by metro_id, geo_level, geoid
having count(*) > 1
