-- (metro_id, authority_id, route_id) is the spine key the loader upserts on
-- (public.routes). Must be unique in gold. Returns duplicates → fail.
select metro_id, authority_id, route_id, count(*) as n
from {{ ref('gold_routes') }}
group by metro_id, authority_id, route_id
having count(*) > 1
