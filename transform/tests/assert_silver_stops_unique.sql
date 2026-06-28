-- (metro_id, authority_id, stop_id) must be unique in silver. Returns duplicates → fail.
select metro_id, authority_id, stop_id, count(*) as n
from {{ ref('silver_stops') }}
group by metro_id, authority_id, stop_id
having count(*) > 1
