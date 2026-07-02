-- (metro_id, authority_id, station_id, month) is the ridership-by-stop grain. Must be
-- unique in silver (dedup happened here). Returns duplicates → fail.
select metro_id, authority_id, station_id, month, count(*) as n
from {{ ref('silver_ridership_stop') }}
group by metro_id, authority_id, station_id, month
having count(*) > 1
