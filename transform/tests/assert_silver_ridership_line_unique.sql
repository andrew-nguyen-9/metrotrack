-- (metro_id, authority_id, route, month) is the ridership-by-line grain. Must be
-- unique in silver (dedup happened here). Returns duplicates → fail.
select metro_id, authority_id, route, month, count(*) as n
from {{ ref('silver_ridership_line') }}
group by metro_id, authority_id, route, month
having count(*) > 1
