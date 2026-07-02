-- (metro_id, h3) is the spine key the loader upserts on (public.hex_tod).
-- Must be unique in gold. Returns duplicates → fail.
select metro_id, h3, count(*) as n
from {{ ref('gold_hex_tod') }}
group by metro_id, h3
having count(*) > 1
