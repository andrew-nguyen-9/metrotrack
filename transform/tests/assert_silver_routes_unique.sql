-- (metro_id, authority_id, route_id) must be unique in silver. Returns duplicates → fail.
select metro_id, authority_id, route_id, count(*) as n
from {{ ref('silver_routes') }}
group by metro_id, authority_id, route_id
having count(*) > 1
