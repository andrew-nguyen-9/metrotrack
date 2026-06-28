-- (metro_id, authority_id, stop_id) is the spine key the loader upserts on
-- (public.stops). Must be unique in gold. Returns duplicates → fail.
select metro_id, authority_id, stop_id, count(*) as n
from {{ ref('gold_stops') }}
group by metro_id, authority_id, stop_id
having count(*) > 1
