-- (authority_id, route_id) must be unique in silver. Returns duplicates → fail.
select authority_id, route_id, count(*) as n
from {{ ref('silver_routes') }}
group by authority_id, route_id
having count(*) > 1
