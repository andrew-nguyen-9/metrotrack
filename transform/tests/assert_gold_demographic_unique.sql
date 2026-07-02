-- (metro_id, geo_level, geoid) is the spine key the loader upserts on. Unique in gold.
select metro_id, geo_level, geoid, count(*) as n
from {{ ref('gold_demographic_change') }}
group by metro_id, geo_level, geoid
having count(*) > 1
