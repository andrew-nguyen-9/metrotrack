-- (metro_id, cbd_id) is the spine key the loader upserts on (public.cbds).
-- Must be unique in gold. Returns duplicates → fail.
select metro_id, cbd_id, count(*) as n
from {{ ref('gold_cbds') }}
group by metro_id, cbd_id
having count(*) > 1
